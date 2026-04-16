from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.actions import action_gives_point, action_gives_point_to_opponent
from app.core.database import get_db
from app.core.rotation import rotate_positions
from app.core.volley_rules import is_set_won

from app.models.enums import ActionType, MatchStatus, SetStatus, TeamSide
from app.models.lineup_position import LineupPosition
from app.models.match import Match
from app.models.player import Player
from app.models.rally_action import RallyAction
from app.models.service_spot_snapshot import ServiceSpotSnapshot
from app.models.set import Set
from app.models.team import Team

from app.schemas.action import ActionCreate, ActionRead
from app.schemas.lineup import CourtCell, CourtConstraints, CourtView
from app.schemas.live import MatchLiveRead
from app.schemas.match import MatchCreate, MatchRead
from app.schemas.score import PointCreate
from app.schemas.serve import ServeStart
from app.schemas.set import FinishedSetRead, SetRead
from app.schemas.stats import PlayerStats
from app.schemas.team_stats import TeamStats

router = APIRouter(prefix="/matches", tags=["matches"])


def _get_match_or_404(db: Session, match_id: int) -> Match:
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match introuvable.")
    return match


def _get_current_set_or_400(db: Session, match_id: int) -> Set:
    current_set = (
        db.query(Set)
        .filter(Set.match_id == match_id)
        .order_by(Set.set_number.desc())
        .first()
    )
    if not current_set:
        raise HTTPException(status_code=400, detail="Aucun set en cours. Démarre le match.")
    if current_set.status != SetStatus.running:
        raise HTTPException(status_code=400, detail="Le set courant n'est pas en cours.")
    return current_set


def _get_latest_set_or_400(db: Session, match_id: int) -> Set:
    latest = (
        db.query(Set)
        .filter(Set.match_id == match_id)
        .order_by(Set.set_number.desc())
        .first()
    )
    if not latest:
        raise HTTPException(status_code=400, detail="Aucun set trouvé. Démarre le match.")
    if latest.status == SetStatus.finished:
        raise HTTPException(status_code=400, detail="Le dernier set est terminé.")
    return latest


def _other_team_id(match: Match, team_id: int) -> int:
    if team_id == match.team_a_id:
        return match.team_b_id
    if team_id == match.team_b_id:
        return match.team_a_id
    raise HTTPException(status_code=400, detail="Équipe invalide pour ce match.")


def _max_sets(match: Match) -> int:
    return 2 * match.sets_to_win - 1


def _count_sets_won(db: Session, match: Match) -> tuple[int, int]:
    finished_sets = (
        db.query(Set)
        .filter(Set.match_id == match.id, Set.status == SetStatus.finished)
        .all()
    )
    a_won = 0
    b_won = 0
    for s in finished_sets:
        if s.score_team_a > s.score_team_b:
            a_won += 1
        elif s.score_team_b > s.score_team_a:
            b_won += 1
    return a_won, b_won


def _finished_sets_summary(db: Session, match: Match) -> list[FinishedSetRead]:
    finished_sets = (
        db.query(Set)
        .filter(Set.match_id == match.id, Set.status == SetStatus.finished)
        .order_by(Set.set_number.asc())
        .all()
    )

    result: list[FinishedSetRead] = []
    for s in finished_sets:
        winner_team_id = None
        if s.score_team_a > s.score_team_b:
            winner_team_id = match.team_a_id
        elif s.score_team_b > s.score_team_a:
            winner_team_id = match.team_b_id

        result.append(
            FinishedSetRead(
                set_number=s.set_number,
                score_team_a=s.score_team_a,
                score_team_b=s.score_team_b,
                winner_team_id=winner_team_id,
            )
        )
    return result


def _lineup_ready(db: Session, match_id: int, team_id: int) -> bool:
    lineup = (
        db.query(LineupPosition)
        .filter(
            LineupPosition.match_id == match_id,
            LineupPosition.team_id == team_id,
            LineupPosition.is_on_court.is_(True),
        )
        .all()
    )
    if len(lineup) != 6:
        return False
    positions = {lp.position for lp in lineup}
    return positions == {1, 2, 3, 4, 5, 6}


def _require_lineups_ready(db: Session, match: Match) -> None:
    if not _lineup_ready(db, match.id, match.team_a_id) or not _lineup_ready(db, match.id, match.team_b_id):
        raise HTTPException(
            status_code=400,
            detail="Lineup incomplet : 6 joueurs (positions 1..6) doivent être définis pour chaque équipe avant de démarrer le set.",
        )


def _award_point_and_maybe_finish_set(db: Session, match: Match, current_set: Set, winning_team_id: int) -> None:
    if winning_team_id == match.team_a_id:
        current_set.score_team_a += 1
    else:
        current_set.score_team_b += 1

    if not is_set_won(
        current_set.score_team_a,
        current_set.score_team_b,
        current_set.set_number,
        match.sets_to_win,
    ):
        return

    current_set.status = SetStatus.finished
    db.flush()

    a_sets, b_sets = _count_sets_won(db, match)

    if a_sets >= match.sets_to_win or b_sets >= match.sets_to_win:
        match.status = MatchStatus.finished
        match.finished_at = datetime.now(timezone.utc)
        return

    if current_set.set_number >= _max_sets(match):
        match.status = MatchStatus.finished
        match.finished_at = datetime.now(timezone.utc)
        return

    next_set = Set(
        match_id=match.id,
        set_number=current_set.set_number + 1,
        status=SetStatus.not_started,
        score_team_a=0,
        score_team_b=0,
        serving_team_id=None,
        starting_team_id=None,
    )
    db.add(next_set)


def _rotate_team_if_needed(
    db: Session,
    match: Match,
    current_set: Set,
    winning_team_id: int,
    serving_player_id: int | None = None,
) -> None:
    if serving_player_id is not None:
        if current_set.serving_team_id is None:
            raise HTTPException(status_code=400, detail="Aucune équipe n'est définie au service.")

        pos1 = (
            db.query(LineupPosition)
            .filter(
                LineupPosition.match_id == match.id,
                LineupPosition.team_id == current_set.serving_team_id,
                LineupPosition.position == 1,
                LineupPosition.is_on_court.is_(True),
            )
            .first()
        )

        if not pos1:
            raise HTTPException(status_code=400, detail="Impossible de vérifier le serveur : position 1 non définie.")

        if pos1.player_id != serving_player_id:
            raise HTTPException(status_code=400, detail="Serveur incorrect : seul le joueur en position 1 peut servir.")

    if current_set.serving_team_id is None:
        current_set.serving_team_id = winning_team_id
        return

    if winning_team_id != current_set.serving_team_id:
        lineup = (
            db.query(LineupPosition)
            .filter(
                LineupPosition.match_id == match.id,
                LineupPosition.team_id == winning_team_id,
                LineupPosition.is_on_court.is_(True),
            )
            .order_by(LineupPosition.position.asc())
            .all()
        )

        if len(lineup) != 6:
            raise HTTPException(status_code=400, detail="Rotation impossible : 6 joueurs doivent être définis.")

        pos_map = {lp.position: lp.player_id for lp in lineup}
        if set(pos_map.keys()) != {1, 2, 3, 4, 5, 6}:
            raise HTTPException(status_code=400, detail="Positions incomplètes (1..6 requises).")

        rotated = rotate_positions(pos_map)

        db.query(LineupPosition).filter(
            LineupPosition.match_id == match.id,
            LineupPosition.team_id == winning_team_id,
            LineupPosition.is_on_court.is_(True),
        ).delete(synchronize_session=False)

        for pos in range(1, 7):
            db.add(
                LineupPosition(
                    match_id=match.id,
                    team_id=winning_team_id,
                    position=pos,
                    player_id=rotated[pos],
                    is_on_court=True,
                )
            )

    current_set.serving_team_id = winning_team_id


@router.post("", response_model=MatchRead, status_code=status.HTTP_201_CREATED)
def create_match(payload: MatchCreate, db: Session = Depends(get_db)):
    team_a = db.query(Team).filter(Team.id == payload.team_a_id).first()
    team_b = db.query(Team).filter(Team.id == payload.team_b_id).first()

    if not team_a or not team_b:
        raise HTTPException(status_code=404, detail="Équipe introuvable.")

    if payload.team_a_id == payload.team_b_id:
        raise HTTPException(status_code=400, detail="Les deux équipes doivent être différentes.")

    match = Match(
        team_a_id=payload.team_a_id,
        team_b_id=payload.team_b_id,
        sets_to_win=payload.sets_to_win,
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


@router.get("/{match_id}", response_model=MatchRead)
def get_match(match_id: int, db: Session = Depends(get_db)):
    return _get_match_or_404(db, match_id)


@router.post("/{match_id}/start", response_model=MatchRead)
def start_match(match_id: int, db: Session = Depends(get_db)):
    match = _get_match_or_404(db, match_id)

    if match.status != MatchStatus.draft:
        raise HTTPException(status_code=400, detail="Le match a déjà commencé.")

    match.status = MatchStatus.running
    match.started_at = datetime.now(timezone.utc)

    first_set = Set(
        match_id=match.id,
        set_number=1,
        status=SetStatus.not_started,
        score_team_a=0,
        score_team_b=0,
        serving_team_id=None,
        starting_team_id=None,
    )
    db.add(first_set)

    db.commit()
    db.refresh(match)
    return match


@router.get("/{match_id}/current-set", response_model=SetRead)
def get_current_set(match_id: int, db: Session = Depends(get_db)):
    _get_match_or_404(db, match_id)
    current_set = (
        db.query(Set)
        .filter(Set.match_id == match_id)
        .order_by(Set.set_number.desc())
        .first()
    )
    if not current_set:
        raise HTTPException(status_code=404, detail="Aucun set trouvé pour ce match.")
    return current_set


@router.post("/{match_id}/point")
def add_point(match_id: int, payload: PointCreate, db: Session = Depends(get_db)):
    match = _get_match_or_404(db, match_id)

    if match.status != MatchStatus.running:
        raise HTTPException(status_code=400, detail="Le match n'est pas en cours.")

    current_set = _get_current_set_or_400(db, match_id)
    winning_team_id = match.team_a_id if payload.side == TeamSide.A else match.team_b_id

    _award_point_and_maybe_finish_set(db, match, current_set, winning_team_id)

    db.commit()
    db.refresh(current_set)

    return {
        "match_id": match_id,
        "set_number": current_set.set_number,
        "score_team_a": current_set.score_team_a,
        "score_team_b": current_set.score_team_b,
        "serving_team_id": current_set.serving_team_id,
        "starting_team_id": current_set.starting_team_id,
        "set_status": current_set.status,
    }


@router.post("/{match_id}/actions", response_model=ActionRead, status_code=status.HTTP_201_CREATED)
def add_action(match_id: int, payload: ActionCreate, db: Session = Depends(get_db)):
    match = _get_match_or_404(db, match_id)
    if match.status != MatchStatus.running:
        raise HTTPException(status_code=400, detail="Le match n'est pas en cours.")

    current_set = _get_current_set_or_400(db, match_id)

    player = db.query(Player).filter(Player.id == payload.player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Joueur introuvable.")

    if player.team_id not in (match.team_a_id, match.team_b_id):
        raise HTTPException(status_code=400, detail="Ce joueur ne participe pas à ce match.")

    if action_gives_point(payload.action_type):
        winning_team_id = player.team_id
    elif action_gives_point_to_opponent(payload.action_type):
        winning_team_id = _other_team_id(match, player.team_id)
    else:
        winning_team_id = None

    action = RallyAction(
        match_id=match_id,
        set_id=current_set.id,
        team_id=player.team_id,
        player_id=player.id,
        action_type=payload.action_type,
        point_won=(winning_team_id == player.team_id),
    )
    db.add(action)

    if winning_team_id is not None:
        if payload.action_type in {ActionType.SERVICE_ACE, ActionType.SERVICE_ERROR}:
            _rotate_team_if_needed(
                db=db,
                match=match,
                current_set=current_set,
                winning_team_id=winning_team_id,
                serving_player_id=player.id,
            )
        else:
            _rotate_team_if_needed(
                db=db,
                match=match,
                current_set=current_set,
                winning_team_id=winning_team_id,
            )

        _award_point_and_maybe_finish_set(db, match, current_set, winning_team_id)

    db.commit()
    db.refresh(action)
    return action


@router.post("/{match_id}/serve")
def set_serving_team(match_id: int, payload: ServeStart, db: Session = Depends(get_db)):
    match = _get_match_or_404(db, match_id)

    if match.status != MatchStatus.running:
        raise HTTPException(status_code=400, detail="Le match n'est pas en cours.")

    current_set = _get_latest_set_or_400(db, match_id)

    if payload.team_id not in (match.team_a_id, match.team_b_id):
        raise HTTPException(status_code=400, detail="Cette équipe ne participe pas au match.")

    _require_lineups_ready(db, match)

    current_set.serving_team_id = payload.team_id
    current_set.starting_team_id = payload.team_id
    current_set.status = SetStatus.running

    db.commit()
    db.refresh(current_set)

    return {
        "match_id": match_id,
        "set_id": current_set.id,
        "set_number": current_set.set_number,
        "set_status": current_set.status,
        "serving_team_id": current_set.serving_team_id,
        "starting_team_id": current_set.starting_team_id,
    }


@router.post("/{match_id}/next-set")
def start_next_set(match_id: int, db: Session = Depends(get_db)):
    match = _get_match_or_404(db, match_id)

    if match.status != MatchStatus.running:
        raise HTTPException(status_code=400, detail="Le match n'est pas en cours.")

    current_set = (
        db.query(Set)
        .filter(Set.match_id == match_id)
        .order_by(Set.set_number.desc())
        .first()
    )
    if not current_set:
        raise HTTPException(status_code=404, detail="Aucun set trouvé.")

    if current_set.status != SetStatus.not_started:
        raise HTTPException(status_code=400, detail="Le set suivant n'est pas en attente.")

    previous_set = (
        db.query(Set)
        .filter(
            Set.match_id == match_id,
            Set.set_number == current_set.set_number - 1,
            Set.status == SetStatus.finished,
        )
        .first()
    )

    starter_team_id = None
    if previous_set:
        starter_team_id = previous_set.starting_team_id or previous_set.serving_team_id

    if starter_team_id is None:
        raise HTTPException(
            status_code=400,
            detail="Impossible de déterminer automatiquement l'équipe au service pour le set suivant.",
        )

    _require_lineups_ready(db, match)

    auto_serving_team_id = _other_team_id(match, starter_team_id)

    current_set.serving_team_id = auto_serving_team_id
    current_set.starting_team_id = auto_serving_team_id
    current_set.status = SetStatus.running

    db.commit()
    db.refresh(current_set)

    return {
        "match_id": match_id,
        "set_id": current_set.id,
        "set_number": current_set.set_number,
        "set_status": current_set.status,
        "serving_team_id": current_set.serving_team_id,
        "starting_team_id": current_set.starting_team_id,
    }


@router.get("/{match_id}/players/{player_id}/stats", response_model=PlayerStats)
def get_player_stats(match_id: int, player_id: int, db: Session = Depends(get_db)):
    actions = (
        db.query(RallyAction)
        .filter(RallyAction.match_id == match_id, RallyAction.player_id == player_id)
        .all()
    )

    service_points = sum(1 for a in actions if a.action_type == ActionType.SERVICE_ACE)
    attack_points = sum(1 for a in actions if a.action_type == ActionType.ATTACK_KILL)
    block_points = sum(1 for a in actions if a.action_type == ActionType.BLOCK_POINT)

    service_faults = sum(1 for a in actions if a.action_type == ActionType.SERVICE_ERROR)
    attack_faults = sum(1 for a in actions if a.action_type == ActionType.ATTACK_ERROR)
    block_faults = sum(1 for a in actions if a.action_type == ActionType.BLOCK_ERROR)

    return PlayerStats(
        player_id=player_id,
        service_points=service_points,
        attack_points=attack_points,
        block_points=block_points,
        service_faults=service_faults,
        attack_faults=attack_faults,
        block_faults=block_faults,
        total_points=service_points + attack_points + block_points,
        total_faults=service_faults + attack_faults + block_faults,
    )


@router.get("/{match_id}/teams/{team_id}/stats", response_model=TeamStats)
def get_team_stats(match_id: int, team_id: int, db: Session = Depends(get_db)):
    match = _get_match_or_404(db, match_id)

    if team_id not in (match.team_a_id, match.team_b_id):
        raise HTTPException(status_code=400, detail="Cette équipe ne participe pas au match.")

    actions = (
        db.query(RallyAction)
        .filter(RallyAction.match_id == match_id, RallyAction.team_id == team_id)
        .all()
    )

    service_points = sum(1 for a in actions if a.action_type == ActionType.SERVICE_ACE)
    attack_points = sum(1 for a in actions if a.action_type == ActionType.ATTACK_KILL)
    block_points = sum(1 for a in actions if a.action_type == ActionType.BLOCK_POINT)

    service_faults = sum(1 for a in actions if a.action_type == ActionType.SERVICE_ERROR)
    attack_faults = sum(1 for a in actions if a.action_type == ActionType.ATTACK_ERROR)
    block_faults = sum(1 for a in actions if a.action_type == ActionType.BLOCK_ERROR)

    return TeamStats(
        team_id=team_id,
        service_points=service_points,
        attack_points=attack_points,
        block_points=block_points,
        service_faults=service_faults,
        attack_faults=attack_faults,
        block_faults=block_faults,
        total_points=service_points + attack_points + block_points,
        total_faults=service_faults + attack_faults + block_faults,
    )


@router.get("/{match_id}/teams/{team_id}/lineup")
def get_team_lineup(match_id: int, team_id: int, db: Session = Depends(get_db)):
    lineup = (
        db.query(LineupPosition, Player)
        .join(Player, Player.id == LineupPosition.player_id)
        .filter(
            LineupPosition.match_id == match_id,
            LineupPosition.team_id == team_id,
            LineupPosition.is_on_court.is_(True),
        )
        .order_by(LineupPosition.position.asc())
        .all()
    )

    return [
        {
            "position": lp.position,
            "jersey_number": player.jersey_number,
        }
        for lp, player in lineup
    ]


@router.get("/{match_id}/teams/{team_id}/court-view")
def get_court_view(match_id: int, team_id: int, db: Session = Depends(get_db)):
    match = _get_match_or_404(db, match_id)

    if team_id not in (match.team_a_id, match.team_b_id):
        raise HTTPException(status_code=400, detail="Cette équipe ne participe pas au match.")

    current_set = (
        db.query(Set)
        .filter(Set.match_id == match_id)
        .order_by(Set.set_number.desc())
        .first()
    )
    if not current_set:
        raise HTTPException(status_code=400, detail="Aucun set pour ce match.")

    rows = (
        db.query(LineupPosition, Player)
        .join(Player, Player.id == LineupPosition.player_id)
        .filter(
            LineupPosition.match_id == match_id,
            LineupPosition.team_id == team_id,
            LineupPosition.is_on_court.is_(True),
        )
        .order_by(LineupPosition.position.asc())
        .all()
    )

    if len(rows) != 6:
        raise HTTPException(status_code=400, detail="Lineup incomplet : 6 joueurs sur le terrain requis.")

    positions = [lp.position for (lp, _) in rows]
    if sorted(positions) != [1, 2, 3, 4, 5, 6]:
        raise HTTPException(status_code=400, detail="Lineup invalide : positions 1..6 requises.")

    pos_to_cell = {
        4: {"x": 0, "y": 0, "label": "Avant gauche"},
        3: {"x": 1, "y": 0, "label": "Avant centre"},
        2: {"x": 2, "y": 0, "label": "Avant droit"},
        5: {"x": 0, "y": 1, "label": "Arrière gauche"},
        6: {"x": 1, "y": 1, "label": "Arrière centre"},
        1: {"x": 2, "y": 1, "label": "Arrière droit"},
    }

    pos_to_jersey = {lp.position: player.jersey_number for lp, player in rows}

    cells = []
    for pos in [4, 3, 2, 5, 6, 1]:
        c = pos_to_cell[pos]
        cells.append(
            {
                "x": c["x"],
                "y": c["y"],
                "position": pos,
                "label": c["label"],
                "jersey_number": pos_to_jersey[pos],
            }
        )

    return {
        "team_id": team_id,
        "set_id": current_set.id,
        "cells": cells,
        "constraints": {
            "left_right": [],
            "front_back": [],
        },
    }


@router.get("/{match_id}/live", response_model=MatchLiveRead)
def get_match_live(match_id: int, db: Session = Depends(get_db)):
    match = _get_match_or_404(db, match_id)

    current_set = (
        db.query(Set)
        .filter(Set.match_id == match_id)
        .order_by(Set.set_number.desc())
        .first()
    )
    if not current_set:
        raise HTTPException(status_code=404, detail="Current set not found")

    team_a = db.query(Team).filter(Team.id == match.team_a_id).first()
    team_b = db.query(Team).filter(Team.id == match.team_b_id).first()

    if not team_a or not team_b:
        raise HTTPException(status_code=404, detail="Team not found")

    def build_court_view(team_id: int) -> CourtView:
        rows = (
            db.query(LineupPosition, Player)
            .join(Player, Player.id == LineupPosition.player_id)
            .filter(
                LineupPosition.match_id == match_id,
                LineupPosition.team_id == team_id,
                LineupPosition.is_on_court.is_(True),
            )
            .order_by(LineupPosition.position.asc())
            .all()
        )

        pos_to_xy = {
            4: (0, 0),
            3: (1, 0),
            2: (2, 0),
            5: (0, 1),
            6: (1, 1),
            1: (2, 1),
        }

        cells = []
        for lp, player in rows:
            if lp.position not in pos_to_xy:
                continue
            x, y = pos_to_xy[lp.position]
            cells.append(
                CourtCell(
                    x=x,
                    y=y,
                    position=lp.position,
                    label=f"{player.first_name} {player.last_name}",
                    jersey_number=player.jersey_number,
                )
            )

        return CourtView(
            team_id=team_id,
            set_id=current_set.id,
            cells=cells,
            constraints=CourtConstraints(left_right=[], front_back=[]),
        )

    a_sets, b_sets = _count_sets_won(db, match)

    return MatchLiveRead(
        match=match,
        current_set=current_set,
        team_a=team_a,
        team_b=team_b,
        court_a=build_court_view(match.team_a_id),
        court_b=build_court_view(match.team_b_id),
        team_a_sets_won=a_sets,
        team_b_sets_won=b_sets,
        finished_sets=_finished_sets_summary(db, match),
    )


@router.delete("/reset-all", status_code=status.HTTP_204_NO_CONTENT)
def reset_all(db: Session = Depends(get_db)):
    db.query(RallyAction).delete(synchronize_session=False)
    db.query(LineupPosition).delete(synchronize_session=False)
    db.query(ServiceSpotSnapshot).delete(synchronize_session=False)
    db.query(Set).delete(synchronize_session=False)
    db.query(Match).delete(synchronize_session=False)
    db.query(Player).delete(synchronize_session=False)
    db.query(Team).delete(synchronize_session=False)
    db.commit()


@router.delete("/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_match(match_id: int, db: Session = Depends(get_db)):
    match = _get_match_or_404(db, match_id)
    team_ids = [match.team_a_id, match.team_b_id]

    db.query(RallyAction).filter(RallyAction.match_id == match_id).delete(synchronize_session=False)
    db.query(LineupPosition).filter(LineupPosition.match_id == match_id).delete(synchronize_session=False)
    db.query(ServiceSpotSnapshot).filter(ServiceSpotSnapshot.match_id == match_id).delete(synchronize_session=False)
    db.query(Set).filter(Set.match_id == match_id).delete(synchronize_session=False)

    db.delete(match)

    db.query(Player).filter(Player.team_id.in_(team_ids)).delete(synchronize_session=False)
    db.query(Team).filter(Team.id.in_(team_ids)).delete(synchronize_session=False)

    db.commit()
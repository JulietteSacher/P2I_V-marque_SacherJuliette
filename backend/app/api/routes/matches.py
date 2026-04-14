from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.actions import action_gives_point
from app.core.database import get_db
from app.core.rotation import rotate_positions
from app.core.volley_rules import is_set_won

from app.models.enums import ActionType, MatchStatus, SetStatus, TeamSide
from app.models.lineup_position import LineupPosition
from app.models.match import Match
from app.models.player import Player
from app.models.rally_action import RallyAction
from app.models.set import Set
from app.models.team import Team

from app.schemas.action import ActionCreate, ActionRead
from app.schemas.lineup import CourtCell, CourtConstraints, CourtView
from app.schemas.live import MatchLiveRead
from app.schemas.match import MatchCreate, MatchRead
from app.schemas.score import PointCreate
from app.schemas.serve import ServeStart
from app.schemas.stats import PlayerStats
from app.schemas.team_stats import TeamStats

router = APIRouter(prefix="/matches", tags=["matches"])


# -------------------------
# Helpers
# -------------------------
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
    s = (
        db.query(Set)
        .filter(Set.match_id == match_id)
        .order_by(Set.set_number.desc())
        .first()
    )
    if not s:
        raise HTTPException(status_code=400, detail="Aucun set trouvé. Démarre le match.")
    if s.status == SetStatus.finished:
        raise HTTPException(status_code=400, detail="Le dernier set est terminé.")
    return s


def _other_team_id(match: Match, team_id: int) -> int:
    return match.team_b_id if team_id == match.team_a_id else match.team_a_id


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
    pos = {lp.position for lp in lineup}
    return pos == {1, 2, 3, 4, 5, 6}


def _require_lineups_ready(db: Session, match: Match) -> None:
    if not _lineup_ready(db, match.id, match.team_a_id) or not _lineup_ready(db, match.id, match.team_b_id):
        raise HTTPException(
            status_code=400,
            detail="Lineup incomplet : 6 joueurs (positions 1..6) doivent être définis pour chaque équipe avant de démarrer le set.",
        )


def _clear_lineups_for_new_set(db: Session, match_id: int) -> None:
    db.query(LineupPosition).filter(
        LineupPosition.match_id == match_id,
        LineupPosition.is_on_court.is_(True),
    ).delete(synchronize_session=False)


def _award_point_and_maybe_finish_set(db: Session, match: Match, current_set: Set, winning_team_id: int) -> None:
    if winning_team_id == match.team_a_id:
        current_set.score_team_a += 1
    else:
        current_set.score_team_b += 1

    if is_set_won(current_set.score_team_a, current_set.score_team_b, current_set.set_number):
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
            raise HTTPException(
                status_code=400,
                detail="Aucune équipe n'est définie au service.",
            )

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
            raise HTTPException(
                status_code=400,
                detail="Impossible de vérifier le serveur : position 1 non définie.",
            )

        if pos1.player_id != serving_player_id:
            raise HTTPException(
                status_code=400,
                detail="Serveur incorrect : seul le joueur en position 1 peut servir.",
            )

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
            .order_by(LineupPosition.position)
            .all()
        )

        if len(lineup) != 6:
            raise HTTPException(
                status_code=400,
                detail="Rotation impossible : 6 joueurs doivent être définis.",
            )

        pos_map = {lp.position: lp.player_id for lp in lineup}
        if set(pos_map.keys()) != {1, 2, 3, 4, 5, 6}:
            raise HTTPException(
                status_code=400,
                detail="Positions incomplètes (1..6 requises).",
            )

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


# -------------------------
# Match lifecycle
# -------------------------
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
    )
    db.add(first_set)

    db.commit()
    db.refresh(match)
    return match


@router.get("/{match_id}/current-set")
def get_current_set(match_id: int, db: Session = Depends(get_db)):
    _ = _get_match_or_404(db, match_id)
    current_set = (
        db.query(Set)
        .filter(Set.match_id == match_id)
        .order_by(Set.set_number.desc())
        .first()
    )
    if not current_set:
        raise HTTPException(status_code=404, detail="Aucun set trouvé pour ce match.")
    return current_set


# -------------------------
# Point direct
# -------------------------
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
        "set_status": current_set.status,
        "serving_team_id": current_set.serving_team_id,
    }


# -------------------------
# Actions -> score + rotation
# -------------------------
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

    point_for_actor_team = action_gives_point(payload.action_type)
    error_actions = {ActionType.SERVICE_ERROR, ActionType.ATTACK_ERROR, ActionType.BLOCK_ERROR}

    if point_for_actor_team:
        winning_team_id = player.team_id
    elif payload.action_type in error_actions:
        winning_team_id = _other_team_id(match, player.team_id)
    else:
        winning_team_id = None

    action = RallyAction(
        match_id=match_id,
        set_id=current_set.id,
        team_id=player.team_id,
        player_id=player.id,
        action_type=payload.action_type,
        point_won=point_for_actor_team,
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


# -------------------------
# Début de set : définir l'équipe au service
# -------------------------
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
    current_set.status = SetStatus.running

    db.commit()
    db.refresh(current_set)

    return {
        "match_id": match_id,
        "set_id": current_set.id,
        "set_number": current_set.set_number,
        "set_status": current_set.status,
        "serving_team_id": current_set.serving_team_id,
    }


# -------------------------
# Player stats
# -------------------------
@router.get(
    "/{match_id}/players/{player_id}/stats",
    response_model=PlayerStats,
    summary="Afficher les statistiques d’un joueur pour un match",
)
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

    total_points = service_points + attack_points + block_points
    total_faults = service_faults + attack_faults + block_faults

    return PlayerStats(
        player_id=player_id,
        service_points=service_points,
        attack_points=attack_points,
        block_points=block_points,
        service_faults=service_faults,
        attack_faults=attack_faults,
        block_faults=block_faults,
        total_points=total_points,
        total_faults=total_faults,
    )


@router.get(
    "/{match_id}/players/stats/search",
    response_model=PlayerStats,
    summary="Rechercher les stats d’un joueur par nom ou numéro",
)
def get_player_stats_by_search(
    match_id: int,
    jersey_number: int | None = None,
    last_name: str | None = None,
    db: Session = Depends(get_db),
):
    if jersey_number is None and last_name is None:
        raise HTTPException(status_code=400, detail="Il faut fournir un numéro de maillot ou un nom de famille.")

    query = db.query(Player)

    if jersey_number is not None:
        query = query.filter(Player.jersey_number == jersey_number)

    if last_name is not None:
        query = query.filter(Player.last_name.ilike(f"%{last_name}%"))

    player = query.first()
    if not player:
        raise HTTPException(status_code=404, detail="Joueur introuvable.")

    match = _get_match_or_404(db, match_id)
    if player.team_id not in (match.team_a_id, match.team_b_id):
        raise HTTPException(status_code=400, detail="Ce joueur ne participe pas à ce match.")

    actions = (
        db.query(RallyAction)
        .filter(RallyAction.match_id == match_id, RallyAction.player_id == player.id)
        .all()
    )

    service_points = sum(1 for a in actions if a.action_type == ActionType.SERVICE_ACE)
    attack_points = sum(1 for a in actions if a.action_type == ActionType.ATTACK_KILL)
    block_points = sum(1 for a in actions if a.action_type == ActionType.BLOCK_POINT)

    service_faults = sum(1 for a in actions if a.action_type == ActionType.SERVICE_ERROR)
    attack_faults = sum(1 for a in actions if a.action_type == ActionType.ATTACK_ERROR)
    block_faults = sum(1 for a in actions if a.action_type == ActionType.BLOCK_ERROR)

    total_points = service_points + attack_points + block_points
    total_faults = service_faults + attack_faults + block_faults

    return PlayerStats(
        player_id=player.id,
        service_points=service_points,
        attack_points=attack_points,
        block_points=block_points,
        service_faults=service_faults,
        attack_faults=attack_faults,
        block_faults=block_faults,
        total_points=total_points,
        total_faults=total_faults,
    )


# -------------------------
# Court view
# -------------------------
@router.get("/{match_id}/teams/{team_id}/court-view")
def get_court_view(match_id: int, team_id: int, db: Session = Depends(get_db)):
    match = _get_match_or_404(db, match_id)

    if team_id not in (match.team_a_id, match.team_b_id):
        raise HTTPException(
            status_code=400,
            detail="Cette équipe ne participe pas au match."
        )

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
        raise HTTPException(
            status_code=400,
            detail="Lineup incomplet : 6 joueurs sur le terrain requis."
        )

    positions = [lp.position for (lp, _) in rows]

    if sorted(positions) != [1, 2, 3, 4, 5, 6]:
        raise HTTPException(
            status_code=400,
            detail="Lineup invalide : positions 1..6 requises."
        )

    pos_to_cell = {
        4: {"x": 0, "y": 0, "label": "Avant gauche"},
        3: {"x": 1, "y": 0, "label": "Avant centre"},
        2: {"x": 2, "y": 0, "label": "Avant droit"},
        5: {"x": 0, "y": 1, "label": "Arrière gauche"},
        6: {"x": 1, "y": 1, "label": "Arrière centre"},
        1: {"x": 2, "y": 1, "label": "Arrière droit"},
    }

    pos_to_jersey = {}
    for lp, player in rows:
        pos_to_jersey[lp.position] = player.jersey_number

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

    constraints = {
        "left_right": [
            {"a_pos": 4, "b_pos": 3, "rule": "a_left_of_b"},
            {"a_pos": 3, "b_pos": 2, "rule": "a_left_of_b"},
            {"a_pos": 5, "b_pos": 6, "rule": "a_left_of_b"},
            {"a_pos": 6, "b_pos": 1, "rule": "a_left_of_b"},
        ],
        "front_back": [
            {"front_pos": 4, "back_pos": 5, "rule": "front_in_front_of_back"},
            {"front_pos": 3, "back_pos": 6, "rule": "front_in_front_of_back"},
            {"front_pos": 2, "back_pos": 1, "rule": "front_in_front_of_back"},
        ],
    }

    return {
        "team_id": team_id,
        "set_id": current_set.id,
        "cells": cells,
        "constraints": constraints,
    }


# -------------------------
# Team stats
# -------------------------
@router.get(
    "/{match_id}/teams/{team_id}/stats",
    response_model=TeamStats,
    summary="Afficher les statistiques d’une équipe pour un match",
)
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

    total_points = service_points + attack_points + block_points
    total_faults = service_faults + attack_faults + block_faults

    return TeamStats(
        team_id=team_id,
        service_points=service_points,
        attack_points=attack_points,
        block_points=block_points,
        service_faults=service_faults,
        attack_faults=attack_faults,
        block_faults=block_faults,
        total_points=total_points,
        total_faults=total_faults,
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
        .order_by(LineupPosition.position)
        .all()
    )

    return [
        {
            "position": lp.position,
            "jersey_number": player.jersey_number,
        }
        for lp, player in lineup
    ]


# -------------------------
# Match live (une seule route pour le front)
# -------------------------
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
            constraints=CourtConstraints(
                left_right=[],
                front_back=[],
            ),
        )

    court_a = build_court_view(match.team_a_id)
    court_b = build_court_view(match.team_b_id)

    return MatchLiveRead(
        match=match,
        current_set=current_set,
        team_a=team_a,
        team_b=team_b,
        court_a=court_a,
        court_b=court_b,
    )


    #------------------------------------------
    # Supprimer le match de de la bdd
    #-------------------------------------------

@router.delete("/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_match(match_id: int, db: Session = Depends(get_db)):
    match = _get_match_or_404(db, match_id)

    db.query(RallyAction).filter(RallyAction.match_id == match_id).delete(synchronize_session=False)
    db.query(LineupPosition).filter(LineupPosition.match_id == match_id).delete(synchronize_session=False)
    db.query(Set).filter(Set.match_id == match_id).delete(synchronize_session=False)

    db.delete(match)
    db.commit()

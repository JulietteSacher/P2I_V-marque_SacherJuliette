from __future__ import annotations
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.core.volley_rules import is_set_won
from app.core.actions import action_gives_point
from app.core.rotation import rotate_positions

from app.models.team import Team
from app.models.player import Player
from app.models.match import Match
from app.models.set import Set
from app.models.rally_action import RallyAction
from app.models.lineup_position import LineupPosition
from app.models.enums import MatchStatus, SetStatus, TeamSide, ActionType

from app.schemas.match import MatchCreate, MatchRead
from app.schemas.score import PointCreate
from app.schemas.action import ActionCreate, ActionRead
from app.schemas.stats import PlayerStats
from app.schemas.team_stats import TeamStats
from app.schemas.serve import ServeStart

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


def _other_team_id(match: Match, team_id: int) -> int:
    return match.team_b_id if team_id == match.team_a_id else match.team_a_id

def _max_sets(match: Match) -> int:
    # 2 -> 3 sets max ; 3 -> 5 sets max
    return 2 * match.sets_to_win - 1


def _count_sets_won(match: Match) -> tuple[int, int]:
    a_won = 0
    b_won = 0
    for s in match.sets:
        # Certains modèles n'ont pas winner_id : on infère par score à la fin
        if s.status != SetStatus.finished:
            continue
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
    # ✅ “Remettre le lineup” : on vide le terrain pour les 2 équipes
    db.query(LineupPosition).filter(
        LineupPosition.match_id == match_id,
        LineupPosition.is_on_court.is_(True),
    ).delete(synchronize_session=False)

def _award_point_and_maybe_finish_set(db: Session, match: Match, current_set: Set, winning_team_id: int) -> None:
    # Incrément score
    if winning_team_id == match.team_a_id:
        current_set.score_team_a += 1
    else:
        current_set.score_team_b += 1

    # Fin de set ?
    if is_set_won(current_set.score_team_a, current_set.score_team_b, current_set.set_number):
        current_set.status = SetStatus.finished

        # Créer set suivant si < 5
        if current_set.set_number < 5:
            next_set = Set(
                match_id=match.id,
                set_number=current_set.set_number + 1,
                status=SetStatus.running,
                score_team_a=0,
                score_team_b=0,
                serving_team_id=None,  # à définir au début du set
            )
            db.add(next_set)
        else:
            match.status = MatchStatus.finished
            match.finished_at = datetime.now(timezone.utc)


def _rotate_team_if_needed(
    db: Session,
    match: Match,
    current_set: Set,
    winning_team_id: int,
    serving_player_id: int | None = None,
) -> None:
    """
    Gère :
    - validation du serveur (seul position 1 peut servir)
    - changement de service
    - rotation automatique si récupération du service
    """

    # ===============================
    # 1️⃣ Validation : seul pos 1 sert
    # ===============================
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

    # ===================================
    # 2️⃣ Initialisation premier service
    # ===================================
    if current_set.serving_team_id is None:
        current_set.serving_team_id = winning_team_id
        return

    # ===================================
    # 3️⃣ Si changement de service → rotation
    # ===================================
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

        # mapping position -> player
        pos_map = {lp.position: lp.player_id for lp in lineup}

        if set(pos_map.keys()) != {1, 2, 3, 4, 5, 6}:
            raise HTTPException(
                status_code=400,
                detail="Positions incomplètes (1..6 requises).",
            )

        # Rotation logique
        rotated = rotate_positions(pos_map)

        # FK-safe : on supprime les anciennes lignes
        db.query(LineupPosition).filter(
            LineupPosition.match_id == match.id,
            LineupPosition.team_id == winning_team_id,
            LineupPosition.is_on_court.is_(True),
        ).delete(synchronize_session=False)

        # On recrée les nouvelles positions
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

    # ===================================
    # 4️⃣ Mise à jour équipe au service
    # ===================================
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
        sets_to_win=payload.sets_to_win,  # ✅
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    return match

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
        status=SetStatus.not_started,  # ✅ démarre seulement après /serve
        score_team_a=0,
        score_team_b=0,
        serving_team_id=None,
    )
    db.add(first_set)

    # ✅ On force à définir le lineup pour le set 1 (en le vidant)
    _clear_lineups_for_new_set(db, match.id)

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
# (Optionnel) point direct - tu peux le garder ou le supprimer
# -------------------------
@router.post("/{match_id}/point")
def add_point(match_id: int, payload: PointCreate, db: Session = Depends(get_db)):
    match = _get_match_or_404(db, match_id)

    if match.status != MatchStatus.running:
        raise HTTPException(status_code=400, detail="Le match n'est pas en cours.")

    current_set = _get_current_set_or_400(db, match_id)

    # Incrémenter le score (sans stats/rotation)
    if payload.side == TeamSide.A:
        winning_team_id = match.team_a_id
    else:
        winning_team_id = match.team_b_id

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

    # 1) Vérifier match
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match introuvable.")
    if match.status != MatchStatus.running:
        raise HTTPException(status_code=400, detail="Le match n'est pas en cours.")

    # 2) Récupérer le set courant
    current_set = (
        db.query(Set)
        .filter(Set.match_id == match_id)
        .order_by(Set.set_number.desc())
        .first()
    )
    if not current_set or current_set.status != SetStatus.running:
        raise HTTPException(status_code=400, detail="Aucun set en cours. Démarre le match.")

    # 3) Vérifier joueur
    player = db.query(Player).filter(Player.id == payload.player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Joueur introuvable.")

    # Vérifier que le joueur appartient à une des 2 équipes du match
    if player.team_id not in (match.team_a_id, match.team_b_id):
        raise HTTPException(status_code=400, detail="Ce joueur ne participe pas à ce match.")

    # 4) Logique point : à qui va le point ?
    # "point_won" = point pour l'équipe du joueur (utile pour stats type ace/kill/block)
    point_for_actor_team = action_gives_point(payload.action_type)

    # Déterminer l'équipe qui gagne le point (IMPORTANT pour *_ERROR)
    error_actions = {ActionType.SERVICE_ERROR, ActionType.ATTACK_ERROR, ActionType.BLOCK_ERROR}

    if point_for_actor_team:
        winning_team_id = player.team_id
    elif payload.action_type in error_actions:
        winning_team_id = match.team_b_id if player.team_id == match.team_a_id else match.team_a_id
    else:
        # Si un jour tu ajoutes des actions "neutres" qui ne donnent pas de point
        winning_team_id = None

    # 5) Enregistrer l'action (stats)
    action = RallyAction(
        match_id=match_id,
        set_id=current_set.id,
        team_id=player.team_id,
        player_id=player.id,
        action_type=payload.action_type,
        point_won=point_for_actor_team,
    )
    db.add(action)

    # 6) Si l'action entraîne un point, on met à jour score + rotation/service
    if winning_team_id is not None:

        # 6a) Validation serveur uniquement pour actions de service
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

        # 6b) Incrémenter le score du set pour l'équipe gagnante du point
        if winning_team_id == match.team_a_id:
            current_set.score_team_a += 1
        else:
            current_set.score_team_b += 1

        # 6c) Vérifier fin de set
        if is_set_won(current_set.score_team_a, current_set.score_team_b, current_set.set_number):
            current_set.status = SetStatus.finished

            # créer set suivant automatiquement si < 5
            if current_set.set_number < 5:
                next_set = Set(
                    match_id=match_id,
                    set_number=current_set.set_number + 1,
                    status=SetStatus.running,
                    score_team_a=0,
                    score_team_b=0,
                    serving_team_id=None,  # on redéfinira via /matches/{id}/serve ou au 1er point
                )
                db.add(next_set)
            else:
                match.status = MatchStatus.finished
                match.finished_at = datetime.now(timezone.utc)

    # 7) Commit final
    db.commit()
    db.refresh(action)
    return action


# Route dédiée pour définir l'équipe au service (ex: au début du set ou pour corr
@router.post("/{match_id}/serve")
def set_serving_team(match_id: int, payload: ServeStart, db: Session = Depends(get_db)):
    match = _get_match_or_404(db, match_id)
    current_set = _get_current_set_or_400(db, match_id)

    if payload.team_id not in (match.team_a_id, match.team_b_id):
        raise HTTPException(status_code=400, detail="Cette équipe ne participe pas au match.")

    current_set.serving_team_id = payload.team_id
    db.commit()
    db.refresh(current_set)

    return {
        "match_id": match_id,
        "set_id": current_set.id,
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

    # Reuse stats
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
        raise HTTPException(status_code=400, detail="Cette équipe ne participe pas à ce match.")

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
        db.query(LineupPosition)
        .filter(
            LineupPosition.match_id == match_id,
            LineupPosition.team_id == team_id,
            LineupPosition.is_on_court.is_(True),
        )
        .order_by(LineupPosition.position)
        .all()
    )
    return [{"position": lp.position, "player_id": lp.player_id} for lp in lineup]

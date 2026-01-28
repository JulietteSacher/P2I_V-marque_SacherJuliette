from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from sqlalchemy import or_


from app.core.database import get_db
from app.models.match import Match
from app.models.set import Set
from app.models.team import Team
from app.models.enums import MatchStatus, SetStatus
from app.schemas.match import MatchCreate, MatchRead
from app.schemas.score import PointCreate
from app.models.enums import TeamSide
from app.core.volley_rules import is_set_won
from app.models.player import Player
from app.models.rally_action import RallyAction
from app.schemas.action import ActionCreate, ActionRead
from app.core.actions import action_gives_point
from app.models.rally_action import RallyAction
from app.models.enums import ActionType
from app.schemas.stats import PlayerStats
from app.schemas.team_stats import TeamStats


router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("", response_model=MatchRead, status_code=status.HTTP_201_CREATED)
def create_match(payload: MatchCreate, db: Session = Depends(get_db)):
    team_a = db.query(Team).filter(Team.id == payload.team_a_id).first()
    team_b = db.query(Team).filter(Team.id == payload.team_b_id).first()
    if not team_a or not team_b:
        raise HTTPException(status_code=404, detail="Équipe introuvable.")

    match = Match(team_a_id=payload.team_a_id, team_b_id=payload.team_b_id)
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


@router.post("/{match_id}/start", response_model=MatchRead)
def start_match(match_id: int, db: Session = Depends(get_db)):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match introuvable.")
    if match.status != MatchStatus.draft:
        raise HTTPException(status_code=400, detail="Le match a déjà commencé.")

    match.status = MatchStatus.running
    match.started_at = datetime.now(timezone.utc)

    first_set = Set(
        match_id=match.id,
        set_number=1,
        status=SetStatus.running,
    )
    db.add(first_set)
    db.commit()
    db.refresh(match)
    return match

@router.get("/{match_id}/current-set")
def get_current_set(match_id: int, db: Session = Depends(get_db)):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match introuvable.")

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
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match introuvable.")
    if match.status != MatchStatus.running:
        raise HTTPException(status_code=400, detail="Le match n'est pas en cours.")

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

    # 1) Incrémenter le score
    if payload.side == TeamSide.A:
        current_set.score_team_a += 1
    else:
        current_set.score_team_b += 1

    # 2) Vérifier si le set est gagné
    if is_set_won(current_set.score_team_a, current_set.score_team_b, current_set.set_number):
        current_set.status = SetStatus.finished

        # Option MVP : créer automatiquement le set suivant si < 5
        if current_set.set_number < 5:
            next_set = Set(
                match_id=match_id,
                set_number=current_set.set_number + 1,
                status=SetStatus.running,
                score_team_a=0,
                score_team_b=0,
            )
            db.add(next_set)

        # Option MVP : si c'était le 5e set, on termine le match
        else:
            match.status = MatchStatus.finished
            match.finished_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(current_set)

    return {
        "match_id": match_id,
        "set_number": current_set.set_number,
        "score_team_a": current_set.score_team_a,
        "score_team_b": current_set.score_team_b,
        "set_status": current_set.status,
    }

@router.post("/{match_id}/actions", response_model=ActionRead, status_code=status.HTTP_201_CREATED)
def add_action(match_id: int, payload: ActionCreate, db: Session = Depends(get_db)):
    # 1) Vérifier match
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match introuvable.")
    if match.status != MatchStatus.running:
        raise HTTPException(status_code=400, detail="Le match n'est pas en cours.")

    # 2) Trouver le set courant (le dernier set créé)
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

    # 4) Vérifier que le joueur appartient à une des 2 équipes du match
    if player.team_id not in (match.team_a_id, match.team_b_id):
        raise HTTPException(status_code=400, detail="Ce joueur ne participe pas à ce match.")

    # 5) Déterminer si l'action donne un point
    point_won = action_gives_point(payload.action_type)

    # 6) Enregistrer l'action
    action = RallyAction(
        match_id=match_id,
        set_id=current_set.id,
        team_id=player.team_id,
        player_id=player.id,
        action_type=payload.action_type,
        point_won=point_won,
    )
    db.add(action)

    # 7) Si point, incrémenter le score du set pour l'équipe correspondante
    if point_won:
        if player.team_id == match.team_a_id:
            current_set.score_team_a += 1
        else:
            current_set.score_team_b += 1

        # 8) Vérifier fin de set
        if is_set_won(current_set.score_team_a, current_set.score_team_b, current_set.set_number):
            current_set.status = SetStatus.finished

            # MVP : créer set suivant automatiquement si < 5
            if current_set.set_number < 5:
                next_set = Set(
                    match_id=match_id,
                    set_number=current_set.set_number + 1,
                    status=SetStatus.running,
                    score_team_a=0,
                    score_team_b=0,
                )
                db.add(next_set)
            else:
                match.status = MatchStatus.finished
                match.finished_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(action)
    return action

@router.get(
    "/{match_id}/players/{player_id}/stats",
    response_model=PlayerStats,
    summary="Afficher les statistiques d’un joueur pour un match"
)
def get_player_stats(match_id: int, player_id: int, db: Session = Depends(get_db)):
    actions = (
        db.query(RallyAction)
        .filter(
            RallyAction.match_id == match_id,
            RallyAction.player_id == player_id,
        )
        .all()
    )

    if not actions:
        return PlayerStats(
            player_id=player_id,
            service_points=0,
            attack_points=0,
            block_points=0,
            service_faults=0,
            attack_faults=0,
            block_faults=0,
            total_points=0,
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
    summary="Rechercher les stats d’un joueur par nom ou numéro"
)
def get_player_stats_by_search(
    match_id: int,
    jersey_number: int | None = None,
    last_name: str | None = None,
    db: Session = Depends(get_db),
):
    if jersey_number is None and last_name is None:
        raise HTTPException(
            status_code=400,
            detail="Il faut fournir un numéro de maillot ou un nom de famille."
        )

    # 1) Trouver le joueur
    query = db.query(Player)

    if jersey_number is not None:
        query = query.filter(Player.jersey_number == jersey_number)

    if last_name is not None:
        query = query.filter(Player.last_name.ilike(f"%{last_name}%"))

    player = query.first()

    if not player:
        raise HTTPException(status_code=404, detail="Joueur introuvable.")

    # 2) Vérifier qu’il participe au match
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match introuvable.")

    if player.team_id not in (match.team_a_id, match.team_b_id):
        raise HTTPException(
            status_code=400,
            detail="Ce joueur ne participe pas à ce match."
        )

    # 3) Récupérer les actions du joueur
    actions = (
        db.query(RallyAction)
        .filter(
            RallyAction.match_id == match_id,
            RallyAction.player_id == player.id,
        )
        .all()
    )

    # 4) Calcul des stats (même logique que précédemment)
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

# Stats d'une équipe pour un match
@router.get(
    "/{match_id}/teams/{team_id}/stats",
    response_model=TeamStats,
    summary="Afficher les statistiques d’une équipe pour un match"
)
def get_team_stats(match_id: int, team_id: int, db: Session = Depends(get_db)):
    # 1) Vérifier match
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match introuvable.")

    # 2) Vérifier que l’équipe participe au match
    if team_id not in (match.team_a_id, match.team_b_id):
        raise HTTPException(
            status_code=400,
            detail="Cette équipe ne participe pas à ce match."
        )

    # 3) Récupérer toutes les actions de l’équipe
    actions = (
        db.query(RallyAction)
        .filter(
            RallyAction.match_id == match_id,
            RallyAction.team_id == team_id,
        )
        .all()
    )

    # 4) Calcul des stats
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

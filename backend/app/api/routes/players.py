from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.models.team import Team
from app.models.player import Player
from app.schemas.player import PlayerCreate, PlayerRead

router = APIRouter(prefix="/teams/{team_id}/players", tags=["players"])


@router.post("", response_model=PlayerRead, status_code=status.HTTP_201_CREATED)
def create_player(team_id: int, payload: PlayerCreate, db: Session = Depends(get_db)):
    # Vérifie que l'équipe existe
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Équipe introuvable.")

    player = Player(
        team_id=team_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        jersey_number=payload.jersey_number,
        role=payload.role,
        license_number=payload.license_number,
    )

    db.add(player)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # ici ça attrape notamment l'unicité (team_id, jersey_number)
        raise HTTPException(
            status_code=400,
            detail="Numéro de maillot déjà utilisé dans cette équipe."
        )

    db.refresh(player)
    return player


@router.get("", response_model=list[PlayerRead])
def list_players(team_id: int, db: Session = Depends(get_db)):
    # Vérifie que l'équipe existe (pour renvoyer 404 si team_id invalide)
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Équipe introuvable.")

    return (
        db.query(Player)
        .filter(Player.team_id == team_id)
        .order_by(Player.jersey_number.asc())
        .all()
    )


@router.get("/{player_id}", response_model=PlayerRead)
def get_player(team_id: int, player_id: int, db: Session = Depends(get_db)):
    player = (
        db.query(Player)
        .filter(Player.team_id == team_id, Player.id == player_id)
        .first()
    )
    if not player:
        raise HTTPException(status_code=404, detail="Joueur introuvable.")
    return player

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.team import Team
from app.schemas.team import TeamCreate, TeamRead

router = APIRouter(prefix="/teams", tags=["teams"])


@router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
def create_team(payload: TeamCreate, db: Session = Depends(get_db)):
    # Vérifie unicité du nom (car unique=True en DB, mais on veut un message propre)
    existing = db.query(Team).filter(Team.name == payload.name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Une équipe avec ce nom existe déjà."
        )

    team = Team(name=payload.name)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.get("", response_model=list[TeamRead])
def list_teams(db: Session = Depends(get_db)):
    return db.query(Team).order_by(Team.id.asc()).all()


@router.get("/{team_id}", response_model=TeamRead)
def get_team(team_id: int, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Équipe introuvable.")
    return team

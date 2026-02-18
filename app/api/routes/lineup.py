from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.lineup_position import LineupPosition
from app.models.player import Player
from app.schemas.lineup import LineupCreate

router = APIRouter(prefix="/lineup", tags=["Lineup"])


@router.post("/matches/{match_id}/teams/{team_id}")
def set_initial_lineup(
    match_id: int,
    team_id: int,
    lineup: LineupCreate,
    db: Session = Depends(get_db),
):
    positions = {
        1: lineup.p1,
        2: lineup.p2,
        3: lineup.p3,
        4: lineup.p4,
        5: lineup.p5,
        6: lineup.p6,
    }

    # Vérification appartenance joueurs
    players = (
        db.query(Player)
        .filter(Player.id.in_(positions.values()), Player.team_id == team_id)
        .all()
    )

    if len(players) != 6:
        raise HTTPException(status_code=400, detail="Joueurs invalides pour l’équipe.")

    # Nettoyage ancien lineup
    db.query(LineupPosition).filter(
        LineupPosition.match_id == match_id,
        LineupPosition.team_id == team_id,
    ).delete()

    # Création lineup
    for pos, player_id in positions.items():
        db.add(LineupPosition(
            match_id=match_id,
            team_id=team_id,
            position=pos,
            player_id=player_id,
            is_on_court=True,
        ))

    db.commit()
    return {"status": "rotation initiale enregistrée"}

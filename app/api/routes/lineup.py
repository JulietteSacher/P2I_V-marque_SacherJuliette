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
    # positions -> jersey_number
    positions = {
        1: lineup.p1,
        2: lineup.p2,
        3: lineup.p3,
        4: lineup.p4,
        5: lineup.p5,
        6: lineup.p6,
    }
    jersey_numbers = list(positions.values())

    # Vérifier doublons de maillots
    if len(set(jersey_numbers)) != 6:
        raise HTTPException(status_code=400, detail="Numéros de maillot dupliqués dans le lineup.")

    # Récupérer les joueurs par (team_id + jersey_number)
    players = (
        db.query(Player)
        .filter(
            Player.team_id == team_id,
            Player.jersey_number.in_(jersey_numbers),
        )
        .all()
    )

    if len(players) != 6:
        found = sorted([p.jersey_number for p in players])
        requested = sorted(jersey_numbers)
        missing = sorted(list(set(requested) - set(found)))
        raise HTTPException(
            status_code=400,
            detail=f"Lineup invalide : team_id={team_id}, demandés={requested}, trouvés={found}, manquants={missing}",
        )

    # mapping jersey_number -> player_id
    jersey_to_player_id = {p.jersey_number: p.id for p in players}

    # Nettoyage ancien lineup (uniquement joueurs sur le terrain)
    db.query(LineupPosition).filter(
        LineupPosition.match_id == match_id,
        LineupPosition.team_id == team_id,
        LineupPosition.is_on_court.is_(True),
    ).delete(synchronize_session=False)

    # Création lineup : on stocke player_id en DB
    for pos, jersey in positions.items():
        db.add(
            LineupPosition(
                match_id=match_id,
                team_id=team_id,
                position=pos,
                player_id=jersey_to_player_id[jersey],
                is_on_court=True,
            )
        )

    db.commit()
    return {"status": "lineup enregistré", "match_id": match_id, "team_id": team_id}

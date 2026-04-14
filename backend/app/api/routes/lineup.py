from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.lineup_position import LineupPosition
from app.models.player import Player
from app.schemas.lineup import LineupCreate, SwapPlayerRequest

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
    jersey_numbers = list(positions.values())

    if len(set(jersey_numbers)) != 6:
        raise HTTPException(status_code=400, detail="Numéros de maillot dupliqués dans le lineup.")

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

    jersey_to_player_id = {p.jersey_number: p.id for p in players}

    db.query(LineupPosition).filter(
        LineupPosition.match_id == match_id,
        LineupPosition.team_id == team_id,
    ).delete(synchronize_session=False)

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


@router.post("/matches/{match_id}/teams/{team_id}/swap")
def swap_players(
    match_id: int,
    team_id: int,
    payload: SwapPlayerRequest,
    db: Session = Depends(get_db),
):
    player_out = (
        db.query(Player)
        .filter(Player.id == payload.player_out_id, Player.team_id == team_id)
        .first()
    )
    player_in = (
        db.query(Player)
        .filter(Player.id == payload.player_in_id, Player.team_id == team_id)
        .first()
    )

    if not player_out or not player_in:
        raise HTTPException(status_code=404, detail="Joueur introuvable dans cette équipe.")

    lineup_out = (
        db.query(LineupPosition)
        .filter(
            LineupPosition.match_id == match_id,
            LineupPosition.team_id == team_id,
            LineupPosition.player_id == payload.player_out_id,
            LineupPosition.is_on_court.is_(True),
        )
        .first()
    )

    if not lineup_out:
        raise HTTPException(status_code=400, detail="Le joueur sortant n'est pas sur le terrain.")

    lineup_in = (
        db.query(LineupPosition)
        .filter(
            LineupPosition.match_id == match_id,
            LineupPosition.team_id == team_id,
            LineupPosition.player_id == payload.player_in_id,
        )
        .first()
    )

    if lineup_in and lineup_in.is_on_court:
        raise HTTPException(status_code=400, detail="Le joueur entrant est déjà sur le terrain.")

    position_out = lineup_out.position

    lineup_out.is_on_court = False
    lineup_out.position = 0

    if lineup_in:
        lineup_in.is_on_court = True
        lineup_in.position = position_out
    else:
        db.add(
            LineupPosition(
                match_id=match_id,
                team_id=team_id,
                position=position_out,
                player_id=payload.player_in_id,
                is_on_court=True,
            )
        )

    db.commit()

    return {
        "status": "swap effectué",
        "match_id": match_id,
        "team_id": team_id,
        "player_out_id": payload.player_out_id,
        "player_in_id": payload.player_in_id,
        "position": position_out,
    }
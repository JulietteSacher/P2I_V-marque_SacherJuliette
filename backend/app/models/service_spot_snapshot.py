from datetime import datetime, timezone


from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship


from app.core.database import Base




class ServiceSpotSnapshot(Base):
    __tablename__ = "service_spot_snapshots"


    id = Column(Integer, primary_key=True, index=True)


    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    set_id = Column(Integer, ForeignKey("sets.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)


    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


    # serveur (joueur qui sert)
    server_player_id = Column(Integer, ForeignKey("players.id"), nullable=False)


    # qui est physiquement dans chaque spot 1..6 au moment du service
    spot1_player_id = Column(Integer, ForeignKey("players.id"), nullable=False)  # arrière droit
    spot2_player_id = Column(Integer, ForeignKey("players.id"), nullable=False)  # avant droit
    spot3_player_id = Column(Integer, ForeignKey("players.id"), nullable=False)  # avant centre
    spot4_player_id = Column(Integer, ForeignKey("players.id"), nullable=False)  # avant gauche
    spot5_player_id = Column(Integer, ForeignKey("players.id"), nullable=False)  # arrière gauche
    spot6_player_id = Column(Integer, ForeignKey("players.id"), nullable=False)  # arrière centre
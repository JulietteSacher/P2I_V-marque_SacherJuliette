from sqlalchemy import Column, Integer, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class LineupPosition(Base):
    __tablename__ = "lineup_positions"

    id = Column(Integer, primary_key=True, index=True)

    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)

    position = Column(Integer, nullable=False)  # 1..6
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)

    is_on_court = Column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("match_id", "team_id", "position", name="uq_lineup_position"),
        UniqueConstraint("match_id", "team_id", "player_id", name="uq_lineup_player"),
    )

    player = relationship("Player")

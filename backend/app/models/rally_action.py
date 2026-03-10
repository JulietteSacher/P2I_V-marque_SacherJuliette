from datetime import datetime, timezone

from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import ActionType


class RallyAction(Base):
    __tablename__ = "rally_actions"

    id = Column(Integer, primary_key=True, index=True)

    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    set_id = Column(Integer, ForeignKey("sets.id"), nullable=False)

    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)

    action_type = Column(Enum(ActionType), nullable=False)
    point_won = Column(Boolean, nullable=False)

    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # (relations optionnelles, utiles plus tard)
    player = relationship("Player")
    team = relationship("Team")

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import MatchStatus


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(Enum(MatchStatus), default=MatchStatus.draft, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    team_a_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    team_b_id = Column(Integer, ForeignKey("teams.id"), nullable=False)

    # ✅ 2 = best of 3 (2 sets gagnants), 3 = best of 5 (3 sets gagnants)
    sets_to_win = Column(Integer, default=2, nullable=False)

    sets = relationship("Set", back_populates="match", cascade="all, delete-orphan")

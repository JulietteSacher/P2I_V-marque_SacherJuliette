from sqlalchemy import Column, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import SetStatus


class Set(Base):
    __tablename__ = "sets"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    set_number = Column(Integer, nullable=False)

    score_team_a = Column(Integer, default=0)
    score_team_b = Column(Integer, default=0)
    status = Column(Enum(SetStatus), default=SetStatus.not_started)

    serving_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    starting_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    match = relationship("Match", back_populates="sets")
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.player import PlayerRole



class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)

    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)

    jersey_number = Column(Integer, nullable=False)
    role = Column(Enum(PlayerRole), nullable=False)
    license_number = Column(String, nullable=True)

    team = relationship("Team", back_populates="players")

    __table_args__ = (
        UniqueConstraint("team_id", "jersey_number", name="uq_team_jersey"),
    )
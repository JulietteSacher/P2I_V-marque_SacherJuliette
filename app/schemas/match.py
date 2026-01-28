from pydantic import BaseModel, ConfigDict
from app.models.enums import MatchStatus


class MatchCreate(BaseModel):
    team_a_id: int
    team_b_id: int


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: MatchStatus
    team_a_id: int
    team_b_id: int

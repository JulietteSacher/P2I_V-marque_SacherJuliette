from pydantic import BaseModel, ConfigDict
from app.models.enums import SetStatus


class SetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    set_number: int
    score_team_a: int
    score_team_b: int
    status: SetStatus
    serving_team_id: int | None = None
    starting_team_id: int | None = None


class FinishedSetRead(BaseModel):
    set_number: int
    score_team_a: int
    score_team_b: int
    winner_team_id: int | None = None
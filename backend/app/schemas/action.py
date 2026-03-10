from pydantic import BaseModel, ConfigDict
from app.models.enums import ActionType


class ActionCreate(BaseModel):
    player_id: int
    action_type: ActionType


class ActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_id: int
    set_id: int
    team_id: int
    player_id: int
    action_type: ActionType
    point_won: bool

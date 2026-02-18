from pydantic import BaseModel, ConfigDict, field_validator
from app.models.enums import MatchStatus


class MatchCreate(BaseModel):
    team_a_id: int
    team_b_id: int
    sets_to_win: int = 2  # ✅ 2 ou 3

    @field_validator("sets_to_win")
    @classmethod
    def validate_sets_to_win(cls, v: int) -> int:
        if v not in (2, 3):
            raise ValueError("sets_to_win doit être 2 (best-of-3) ou 3 (best-of-5).")
        return v


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: MatchStatus
    team_a_id: int
    team_b_id: int
    sets_to_win: int

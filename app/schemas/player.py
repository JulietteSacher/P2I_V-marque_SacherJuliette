from pydantic import BaseModel, ConfigDict
from app.models.enums import PlayerRole


class PlayerCreate(BaseModel):
    first_name: str
    last_name: str
    jersey_number: int
    role: PlayerRole
    license_number: str | None = None


class PlayerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    first_name: str
    last_name: str
    jersey_number: int
    role: PlayerRole
    license_number: str | None = None

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TeamCreate(BaseModel):
    name: str


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True) #from_attributes=True permet de convertir un objet SQLAlchemy en réponse JSON.

    id: int
    name: str
    created_at: datetime

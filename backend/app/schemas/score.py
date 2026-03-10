from pydantic import BaseModel
from app.models.enums import TeamSide

class PointCreate(BaseModel):
    side: TeamSide  # "A" ou "B"

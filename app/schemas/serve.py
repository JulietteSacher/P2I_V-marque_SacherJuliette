from pydantic import BaseModel

class ServeStart(BaseModel):
    team_id: int

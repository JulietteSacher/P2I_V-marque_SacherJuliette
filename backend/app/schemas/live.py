from pydantic import BaseModel, ConfigDict

from app.schemas.lineup import CourtView
from app.schemas.match import MatchRead
from app.schemas.set import SetRead, FinishedSetRead
from app.schemas.team import TeamRead


class MatchLiveRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    match: MatchRead
    current_set: SetRead
    team_a: TeamRead
    team_b: TeamRead
    court_a: CourtView
    court_b: CourtView

    team_a_sets_won: int = 0
    team_b_sets_won: int = 0
    finished_sets: list[FinishedSetRead] = []
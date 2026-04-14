from pydantic import BaseModel


class LineupCreate(BaseModel):
    p1: int
    p2: int
    p3: int
    p4: int
    p5: int
    p6: int


class SwapPlayerRequest(BaseModel):
    player_out_id: int
    player_in_id: int


class CourtCell(BaseModel):
    x: int
    y: int
    position: int
    label: str
    jersey_number: int


class LeftRightConstraint(BaseModel):
    a_pos: int
    b_pos: int
    rule: str


class FrontBackConstraint(BaseModel):
    front_pos: int
    back_pos: int
    rule: str


class CourtConstraints(BaseModel):
    left_right: list[LeftRightConstraint]
    front_back: list[FrontBackConstraint]


class CourtView(BaseModel):
    team_id: int
    set_id: int
    cells: list[CourtCell]
    constraints: CourtConstraints
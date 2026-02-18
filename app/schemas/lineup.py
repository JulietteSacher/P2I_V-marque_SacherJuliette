from pydantic import BaseModel

class LineupCreate(BaseModel):
    p1: int
    p2: int
    p3: int 
    p4: int
    p5: int
    p6: int
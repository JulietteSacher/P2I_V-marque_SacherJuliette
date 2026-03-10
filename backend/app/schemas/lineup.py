from pydantic import BaseModel, field_validator


class LineupCreate(BaseModel):
    # ✅ maintenant ce sont des NUMÉROS DE MAILLOT
    p1: int
    p2: int
    p3: int
    p4: int
    p5: int
    p6: int

    @field_validator("p1", "p2", "p3", "p4", "p5", "p6")
    @classmethod
    def validate_jersey_number(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Le numéro de maillot doit être un entier positif.")
        return v

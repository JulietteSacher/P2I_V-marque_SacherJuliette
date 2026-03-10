from pydantic import BaseModel, field_validator




class ServiceSpotsCreate(BaseModel):
    team_id: int


    # serveur en numéro de maillot (pas id)
    server_jersey_number: int


    # spots 1..6 en numéro de maillot
    spot1: int
    spot2: int
    spot3: int
    spot4: int
    spot5: int
    spot6: int


    @field_validator("server_jersey_number", "spot1", "spot2", "spot3", "spot4", "spot5", "spot6")
    @classmethod
    def validate_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Les numéros de maillot doivent être des entiers positifs.")
        return v

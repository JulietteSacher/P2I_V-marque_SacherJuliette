from pydantic import BaseModel


class PlayerStats(BaseModel):
    player_id: int
    service_points: int
    attack_points: int
    block_points: int

    service_faults: int
    attack_faults: int
    block_faults: int

    total_points: int
    total_faults: int
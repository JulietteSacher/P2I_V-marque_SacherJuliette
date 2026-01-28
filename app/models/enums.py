import enum
from enum import Enum

class PlayerRole(enum.Enum):
    PASSEUR = "PASSEUR"
    POINTU = "POINTU"
    R4 = "R4"
    CENTRAL = "CENTRAL"
    LIBERO = "LIBERO"

class MatchStatus(str, Enum):
    draft = "draft"
    running = "running"
    finished = "finished"


class SetStatus(str, Enum):
    not_started = "not_started"
    running = "running"
    finished = "finished"

class TeamSide(str, Enum):
    A = "A"
    B = "B"

class ActionType(str, Enum):
    SERVICE_ACE = "SERVICE_ACE"
    SERVICE_ERROR = "SERVICE_ERROR"
    ATTACK_KILL = "ATTACK_KILL"
    ATTACK_ERROR = "ATTACK_ERROR"
    BLOCK_POINT = "BLOCK_POINT"
    BLOCK_ERROR = "BLOCK_ERROR"

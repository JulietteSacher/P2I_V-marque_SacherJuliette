from app.models.enums import ActionType

POINT_ACTIONS = {
    ActionType.SERVICE_ACE,
    ActionType.ATTACK_KILL,
    ActionType.BLOCK_POINT,
    # ActionType.BLOCK_ERROR,
    # ActionType.ATTACK_ERROR,
    # ActionType.SERVICE_ERROR,

}

def action_gives_point(action_type: ActionType) -> bool:
    return action_type in POINT_ACTIONS

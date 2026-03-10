from app.models.enums import ActionType

# Actions qui donnent le point À L'ÉQUIPE QUI FAIT L'ACTION
POINT_ACTIONS = {
    ActionType.SERVICE_ACE,
    ActionType.ATTACK_KILL,
    ActionType.BLOCK_POINT,
}

# Actions qui donnent le point À L'ÉQUIPE ADVERSE (erreurs)
ERROR_ACTIONS = {
    ActionType.SERVICE_ERROR,
    ActionType.ATTACK_ERROR,
    ActionType.BLOCK_ERROR,
}


def action_gives_point(action_type: ActionType) -> bool:
    """
    Retourne True si l'action donne le point à l'équipe qui réalise l'action.
    Ex: ACE/KILL/BLOCK_POINT -> True
    Ex: *_ERROR -> False (car point à l'adversaire)
    """
    return action_type in POINT_ACTIONS


def action_gives_point_to_opponent(action_type: ActionType) -> bool:
    """
    Retourne True si l'action est une erreur et donne le point à l'adversaire.
    """
    return action_type in ERROR_ACTIONS

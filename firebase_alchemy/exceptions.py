class SQLError(Exception):
    """Raise when sql operations fail
    """
    pass


class ValidationError(Exception):
    """Raise when validator find err
    """
    pass


class UniqueError(Exception):
    """Raise when a unique constraintions exists, and not slience
    """
    pass

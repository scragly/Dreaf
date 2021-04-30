import typing as t


class LimitInstances:
    """Ensures only a single instance exists per identifier, returning old ones if existing."""

    __instances__: t.Dict[t.Any, object] = dict()

    def __new__(cls, identifier: t.Any, *args, **kwds):
        """Set the class to a single instance per identifier."""
        instance = cls.__instances__.get(identifier)
        if instance is None:
            cls.__instances__[identifier] = instance = object.__new__(cls)
        return instance

    def __init_subclass__(cls, **kwargs):
        cls.__instances__ = dict()

"""Reusable filter choice builders grouped by model.

Each module inside this package should correspond to a model domain and expose
callables with the signature: fn(user, query="") -> list[(value, label)].
"""

__all__ = []


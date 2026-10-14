"""Legacy state store module aliasing SQLStateStore for backward compatibility."""

from app.memory.sql_store import SQLStateStore, state_store

# Alias for legacy imports
FirestoreStateStore = SQLStateStore

__all__ = ["FirestoreStateStore", "SQLStateStore", "state_store"]

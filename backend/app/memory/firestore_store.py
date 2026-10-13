"""Firestore-backed agent state & session memory store with local fallback."""

from datetime import UTC, datetime
import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class FirestoreStateStore:
    """Persists LangGraph thread checkpoints and agent memory in GCP Firestore.

    Automatically falls back to an in-memory dictionary when running locally
    without GCP credentials configured, enabling zero-friction local learning.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._local_cache: dict[str, dict[str, Any]] = {}
        self._client: Any | None = None

    def _get_client(self) -> Any | None:
        if self._client is not None:
            return self._client
        if not self.settings.gcp_project_id:
            return None
        try:
            from google.cloud import firestore  # type: ignore[import-untyped]

            self._client = firestore.AsyncClient(project=self.settings.gcp_project_id)
            return self._client
        except Exception as exc:
            logger.warning("Firestore unavailable (%s); using local memory fallback.", exc)
            return None

    @property
    def backend_mode(self) -> str:
        """Return active state backend mode ('firestore' or 'in-memory-fallback')."""
        return "firestore" if self.settings.gcp_project_id else "in-memory-fallback"

    async def save_checkpoint(self, thread_id: str, state_payload: dict[str, Any]) -> None:
        """Persist thread state snapshot to Firestore or local memory."""
        record = {
            "thread_id": thread_id,
            "state": state_payload,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        client = self._get_client()
        if client is not None:
            try:
                doc_ref = client.collection(self.settings.firestore_collection).document(thread_id)
                await doc_ref.set(record, merge=True)
                return
            except Exception as exc:
                logger.warning("Firestore write failed (%s); caching in memory.", exc)

        self._local_cache[thread_id] = record

    async def load_checkpoint(self, thread_id: str) -> dict[str, Any] | None:
        """Load the latest thread state snapshot from Firestore or local memory."""
        client = self._get_client()
        if client is not None:
            try:
                doc_ref = client.collection(self.settings.firestore_collection).document(thread_id)
                snapshot = await doc_ref.get()
                if snapshot.exists:
                    return snapshot.to_dict()
            except Exception as exc:
                logger.warning("Firestore read failed (%s); reading from local memory.", exc)

        return self._local_cache.get(thread_id)


state_store = FirestoreStateStore()

"""In-memory, session-isolated document store.

Every uploaded document lives under a per-browser-session UUID that is
generated server-side and never guessable from the outside. All read/write
access to a document requires both the session_id and doc_id to match —
a client can never enumerate or fetch another session's documents, which
is the concrete mechanism behind "avoid exposing uploaded documents to
other users." Sessions expire after SESSION_TTL_SECONDS of inactivity and
are swept on each request, so nothing is retained indefinitely.

For a real production deployment behind persistent storage, swap this
module for a Redis/Postgres-backed store keyed the same way (session_id,
doc_id) with the same access check — the rest of the app is unaffected.
"""
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional
from .models import Clause
from .retrieval import ClauseIndex, build_index

SESSION_TTL_SECONDS = 60 * 60  # 1 hour of inactivity


@dataclass
class StoredDocument:
    doc_id: str
    name: str
    text: str
    clauses: list
    index: ClauseIndex
    summary: Optional[dict] = None
    risks: Optional[list] = None
    lawyer_prep: Optional[dict] = None


@dataclass
class Session:
    session_id: str
    last_seen: float
    documents: Dict[str, StoredDocument] = field(default_factory=dict)


class Store:
    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def _sweep(self):
        now = time.time()
        expired = [
            sid
            for sid, s in self._sessions.items()
            if now - s.last_seen > SESSION_TTL_SECONDS
        ]
        for sid in expired:
            del self._sessions[sid]

    def new_session(self) -> str:
        self._sweep()
        sid = str(uuid.uuid4())
        self._sessions[sid] = Session(session_id=sid, last_seen=time.time())
        return sid

    def _get_session(self, session_id: str) -> Optional[Session]:
        self._sweep()
        s = self._sessions.get(session_id)
        if s:
            s.last_seen = time.time()
        return s

    def add_document(self, session_id: str, name: str, text: str, clauses: list):
        session = self._get_session(session_id)
        if session is None:
            # session_id supplied by client didn't match a live session —
            # create a fresh one rather than silently attaching to nothing.
            session_id = self.new_session()
            session = self._sessions[session_id]
        doc_id = str(uuid.uuid4())
        session.documents[doc_id] = StoredDocument(
            doc_id=doc_id,
            name=name,
            text=text,
            clauses=clauses,
            index=build_index(clauses),
        )
        return session_id, doc_id

    def get_document(self, session_id: str, doc_id: str) -> Optional[StoredDocument]:
        session = self._get_session(session_id)
        if session is None:
            return None
        return session.documents.get(doc_id)


store = Store()

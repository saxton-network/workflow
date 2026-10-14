"""Auditable SQLite persistence. One verified transaction per state transition."""
from __future__ import annotations

import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from .contracts import Rejected, canonical, decode, digest, validate, validate_state


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise Rejected("unsupported store version")
            if version == 0:
                if db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone():
                    raise Rejected("unversioned nonempty store")
                db.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE workflows (id TEXT PRIMARY KEY, state TEXT NOT NULL);
                    CREATE TABLE events (workflow TEXT NOT NULL, sequence INTEGER NOT NULL,
                        body TEXT NOT NULL, hash TEXT NOT NULL, PRIMARY KEY(workflow, sequence),
                        FOREIGN KEY(workflow) REFERENCES workflows(id));
                    CREATE TRIGGER events_no_update BEFORE UPDATE ON events
                        BEGIN SELECT RAISE(ABORT, 'append-only events'); END;
                    CREATE TRIGGER events_no_delete BEFORE DELETE ON events
                        BEGIN SELECT RAISE(ABORT, 'append-only events'); END;
                    PRAGMA user_version=1;
                    COMMIT;
                """)

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        return db

    @contextmanager
    def transaction(self):
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise Rejected("unsupported store version")
            yield db
            db.execute("COMMIT")
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    def _verified(self, db, workflow_id):
        row = db.execute("SELECT state FROM workflows WHERE id=?", (workflow_id,)).fetchone()
        if row is None:
            raise Rejected("unknown workflow")
        state = decode(row[0])
        validate_state(state)
        records = db.execute("SELECT sequence, body, hash FROM events WHERE workflow=? ORDER BY sequence",
                             (workflow_id,)).fetchall()
        if not records:
            raise Rejected("missing event history")
        previous = "0" * 64
        last_at = -1
        events = []
        for index, (sequence, raw, checksum) in enumerate(records, 1):
            event = decode(raw)
            validate("event", event)
            validate_state(event["state"])
            if (sequence != index or event["sequence"] != index or
                    event["workflow_id"] != workflow_id or
                    event["state"]["plan"]["workflow_id"] != workflow_id or
                    event["previous_hash"] != previous or digest(event) != checksum or
                    event["at"] < last_at):
                raise Rejected("corrupted journal chain")
            previous, last_at = checksum, event["at"]
            events.append(dict(event, event_hash=checksum))
        if state != events[-1]["state"]:
            raise Rejected("projection/checkpoint mismatch")
        return state, events

    def all_states(self, db):
        return {row[0]: self._verified(db, row[0])[0]
                for row in db.execute("SELECT id FROM workflows ORDER BY id").fetchall()}

    def read(self, workflow_id: str) -> dict:
        with self.transaction() as db:
            return self._verified(db, workflow_id)[0]

    def events(self, workflow_id: str) -> list[dict]:
        with self.transaction() as db:
            return self._verified(db, workflow_id)[1]

    def transition(self, workflow_id: str, operation: str, actor: str, at: int, change,
                   *, create: bool = False) -> dict:
        with self.transaction() as db:
            states = self.all_states(db)
            if create:
                if workflow_id in states:
                    raise Rejected("workflow already exists")
                state, events = None, []
            else:
                state, events = self._verified(db, workflow_id)
            if events and at < events[-1]["at"]:
                raise Rejected("clock regression")
            next_state = change(state, states)
            if next_state == state:
                return state
            validate_state(next_state)
            event = {"schema_version": 1, "workflow_id": workflow_id, "sequence": len(events)+1,
                     "operation": operation, "actor": actor, "at": at,
                     "previous_hash": events[-1]["event_hash"] if events else "0"*64,
                     "state": next_state}
            validate("event", event)
            db.execute("INSERT INTO workflows VALUES (?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state",
                       (workflow_id, canonical(next_state)))
            db.execute("INSERT INTO events VALUES (?,?,?,?)",
                       (workflow_id, event["sequence"], canonical(event), digest(event)))
            return next_state

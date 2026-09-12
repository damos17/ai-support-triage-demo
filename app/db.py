import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .models import Case, Incident, TicketDraft


class SQLiteStore:
    """Tiny persistence layer for demo state.

    Production systems would normally use migrations and a dedicated database
    abstraction. For this public demo, stdlib sqlite3 keeps startup friction low.
    """

    def __init__(self, path: str = "data/demo.db"):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tickets (
                    case_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );
                """
            )

    def save_case(self, case: Case) -> None:
        self._upsert("cases", "case_id", case.case_id, case.model_dump(mode="json"))

    def save_ticket(self, ticket: TicketDraft) -> None:
        self._upsert("tickets", "case_id", ticket.case_id, ticket.model_dump(mode="json"))

    def save_incident(self, incident: Incident) -> None:
        self._upsert("incidents", "incident_id", incident.incident_id, incident.model_dump(mode="json"))

    def load_cases(self) -> list[Case]:
        return [Case.model_validate(x) for x in self._all("cases")]

    def load_tickets(self) -> dict[str, TicketDraft]:
        tickets = [TicketDraft.model_validate(x) for x in self._all("tickets")]
        return {ticket.case_id: ticket for ticket in tickets}

    def load_incidents(self) -> list[Incident]:
        return [Incident.model_validate(x) for x in self._all("incidents")]

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM cases")
            conn.execute("DELETE FROM tickets")
            conn.execute("DELETE FROM incidents")

    def _upsert(self, table: str, key_name: str, key: str, payload: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                f"INSERT INTO {table} ({key_name}, payload) VALUES (?, ?) "
                f"ON CONFLICT({key_name}) DO UPDATE SET payload=excluded.payload",
                (key, json.dumps(payload)),
            )

    def _all(self, table: str) -> Iterable[dict]:
        with self._connect() as conn:
            rows = conn.execute(f"SELECT payload FROM {table}").fetchall()
        return [json.loads(row["payload"]) for row in rows]

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("PORTAL_DB_PATH", ROOT / "data" / "portal.db"))
SOP_DIR = Path(os.getenv("PORTAL_SOP_DIR", ROOT / "data" / "uploads" / "sops"))


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=20)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    statements = [
        """CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
            username TEXT NOT NULL, role TEXT NOT NULL, business_unit TEXT NOT NULL,
            action TEXT NOT NULL, details TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
            business_unit TEXT NOT NULL, username TEXT NOT NULL, shift TEXT NOT NULL,
            unit_name TEXT NOT NULL, status TEXT NOT NULL, deviation_count INTEGER NOT NULL,
            payload TEXT NOT NULL, comments TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
            business_unit TEXT NOT NULL, username TEXT NOT NULL, event_date TEXT NOT NULL,
            title TEXT NOT NULL, category TEXT NOT NULL, severity TEXT NOT NULL,
            status TEXT NOT NULL, description TEXT NOT NULL, actions TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS sops (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
            business_unit TEXT NOT NULL, username TEXT NOT NULL, title TEXT NOT NULL,
            category TEXT NOT NULL, unit_name TEXT NOT NULL, version TEXT NOT NULL,
            filename TEXT NOT NULL, file_path TEXT NOT NULL)""",
    ]
    with _connect() as connection:
        for statement in statements:
            connection.execute(statement)
        connection.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log_action(username: str, role: str, business_unit: str, action: str, details: Any = "") -> None:
    text = details if isinstance(details, str) else json.dumps(details, default=str)
    with _connect() as connection:
        connection.execute(
            "INSERT INTO audit_log(timestamp,username,role,business_unit,action,details) VALUES (?,?,?,?,?,?)",
            (_now(), username, role, business_unit, action, text),
        )
        connection.commit()


def audit_frame(business_unit: str | None = None) -> pd.DataFrame:
    query = "SELECT timestamp,username,role,business_unit,action,details FROM audit_log"
    params: tuple[Any, ...] = ()
    if business_unit:
        query += " WHERE business_unit=?"
        params = (business_unit,)
    query += " ORDER BY id DESC"
    with _connect() as connection:
        return pd.read_sql_query(query, connection, params=params)


def save_round(business_unit: str, username: str, shift: str, unit_name: str, status: str,
               deviation_count: int, payload: dict[str, Any], comments: str) -> None:
    with _connect() as connection:
        connection.execute(
            """INSERT INTO rounds(timestamp,business_unit,username,shift,unit_name,status,
               deviation_count,payload,comments) VALUES (?,?,?,?,?,?,?,?,?)""",
            (_now(), business_unit, username, shift, unit_name, status, deviation_count,
             json.dumps(payload, default=str), comments),
        )
        connection.commit()


def rounds_frame(business_unit: str) -> pd.DataFrame:
    with _connect() as connection:
        return pd.read_sql_query(
            """SELECT timestamp,username,shift,unit_name,status,deviation_count,comments
               FROM rounds WHERE business_unit=? ORDER BY id DESC""",
            connection, params=(business_unit,),
        )


def save_event(business_unit: str, username: str, event_date: str, title: str, category: str,
               severity: str, status: str, description: str, actions: str) -> None:
    with _connect() as connection:
        connection.execute(
            """INSERT INTO events(timestamp,business_unit,username,event_date,title,category,
               severity,status,description,actions) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (_now(), business_unit, username, event_date, title, category, severity,
             status, description, actions),
        )
        connection.commit()


def events_frame(business_unit: str) -> pd.DataFrame:
    with _connect() as connection:
        return pd.read_sql_query(
            """SELECT event_date,title,category,severity,status,description,actions,username,timestamp
               FROM events WHERE business_unit=? ORDER BY event_date DESC,id DESC""",
            connection, params=(business_unit,),
        )


def save_sop(business_unit: str, username: str, title: str, category: str, unit_name: str,
             version: str, filename: str, payload: bytes) -> Path:
    safe_name = Path(filename).name
    folder = SOP_DIR / business_unit
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    destination = folder / f"{stamp}_{safe_name}"
    destination.write_bytes(payload)
    with _connect() as connection:
        connection.execute(
            """INSERT INTO sops(timestamp,business_unit,username,title,category,unit_name,
               version,filename,file_path) VALUES (?,?,?,?,?,?,?,?,?)""",
            (_now(), business_unit, username, title, category, unit_name, version,
             safe_name, str(destination)),
        )
        connection.commit()
    return destination


def sops_frame(business_unit: str) -> pd.DataFrame:
    with _connect() as connection:
        return pd.read_sql_query(
            """SELECT id,timestamp,title,category,unit_name,version,filename,file_path,username
               FROM sops WHERE business_unit=? ORDER BY id DESC""",
            connection, params=(business_unit,),
        )

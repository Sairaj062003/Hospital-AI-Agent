"""Postgres access for doctors and appointment slots.

This is the only module in the project that talks to the database directly.
The MCP server (server.py) is the only caller of these functions.
"""

import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Supabase project uses a non-default schema with a hyphen in its name, which
# Postgres only accepts as a quoted identifier - so every table reference
# below is fully schema-qualified rather than relying on search_path, which
# cannot be trusted to persist across PgBouncer's transaction-pooled port.
SCHEMA = '"hospital-scheduling-asst"'


def get_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def fetch_available_doctor_slots() -> list[dict]:
    """Return every unbooked slot, joined with its doctor's name and specialization."""
    query = f"""
        SELECT s.slot_id, d.name AS doctor_name, d.specialization, s.slot_time
        FROM {SCHEMA}.appointment_slots s
        JOIN {SCHEMA}.doctors d ON d.doctor_id = s.doctor_id
        WHERE s.is_booked = FALSE
        ORDER BY s.slot_time;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    return [
        {
            "slot_id": row[0],
            "doctor_name": row[1],
            "specialization": row[2],
            "slot_time": row[3].isoformat(),
        }
        for row in rows
    ]


def mark_slot_booked(slot_id: int) -> bool:
    """Book the given slot if it exists and is currently unbooked.

    Returns True if the slot was booked by this call, False if it was
    already booked or does not exist.
    """
    query = f"""
        UPDATE {SCHEMA}.appointment_slots
        SET is_booked = TRUE
        WHERE slot_id = %s AND is_booked = FALSE
        RETURNING slot_id;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (slot_id,))
            updated = cur.fetchone()
        conn.commit()

    return updated is not None


def fetch_booked_slots() -> list[dict]:
    """Return every booked slot, joined with its doctor's name and specialization.

    There is no patient/login system yet, so this is every booking in the
    database, not scoped to any particular user.
    """
    query = f"""
        SELECT s.slot_id, d.name AS doctor_name, d.specialization, s.slot_time
        FROM {SCHEMA}.appointment_slots s
        JOIN {SCHEMA}.doctors d ON d.doctor_id = s.doctor_id
        WHERE s.is_booked = TRUE
        ORDER BY s.slot_time;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    return [
        {
            "slot_id": row[0],
            "doctor_name": row[1],
            "specialization": row[2],
            "slot_time": row[3].isoformat(),
        }
        for row in rows
    ]


def mark_slot_unbooked(slot_id: int) -> bool:
    """Cancel a booking, freeing the slot back up.

    Returns True if a booked slot was freed, False if it was already
    unbooked or does not exist.
    """
    query = f"""
        UPDATE {SCHEMA}.appointment_slots
        SET is_booked = FALSE
        WHERE slot_id = %s AND is_booked = TRUE
        RETURNING slot_id;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (slot_id,))
            updated = cur.fetchone()
        conn.commit()

    return updated is not None

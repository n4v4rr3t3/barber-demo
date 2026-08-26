"""Database and reusable business configuration.

Production uses PostgreSQL when DATABASE_URL is present (Railway). Local
development falls back to SQLite so the project remains easy to run.
"""
import os
import sqlite3
import secrets
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timedelta

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRES = DATABASE_URL.startswith(("postgres://", "postgresql://"))
DB_PATH = Path(__file__).resolve().parent.parent / "black_barber.db"

SERVICES = [
    {"id": "corte", "nombre": "Corte Clásico", "duracion_min": 30, "precio": 18500},
    {"id": "corte_barba", "nombre": "Corte + Barba", "duracion_min": 50, "precio": 23500},
    {"id": "barba", "nombre": "Perfilado de Barba", "duracion_min": 20, "precio": 16000},
    {"id": "fade", "nombre": "Fade / Degradé", "duracion_min": 40, "precio": 20500},
    {"id": "color", "nombre": "Color / Platinado", "duracion_min": 60, "precio": 18000},
    {"id": "premium", "nombre": "Experiencia Premium", "duracion_min": 75, "precio": 24000},
]

BUSINESS = {
    "nombre": "BLACK BARBER",
    "direccion": "Nicaragua 4550, Palermo, CABA",
    "whatsapp": "5491100000000",
    "instagram": "blackbarber.palermo",
    "horario": "Lun a Sáb 10:00–20:00",
    "lat": -34.5875,
    "lng": -58.4309,
}

OPEN_HOUR = 10
CLOSE_HOUR = 20
SLOT_MINUTES = 30
VALID_STATES = {"pendiente", "confirmado", "cancelado", "completado"}


def _q(sql):
    return sql.replace("?", "%s") if USE_POSTGRES else sql


@contextmanager
def get_conn():
    if USE_POSTGRES:
        import psycopg
        from psycopg.rows import dict_row
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    else:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    id_sql = "BIGSERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"
    with get_conn() as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS turnos (
                id {id_sql},
                public_token TEXT NOT NULL UNIQUE,
                servicio_id TEXT NOT NULL,
                servicio_nombre TEXT NOT NULL,
                duracion_min INTEGER NOT NULL,
                precio INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                hora TEXT NOT NULL,
                cliente_nombre TEXT NOT NULL,
                cliente_telefono TEXT NOT NULL,
                notas TEXT,
                estado TEXT NOT NULL DEFAULT 'pendiente',
                creado_en TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_turnos_fecha_hora ON turnos (fecha, hora)")


def _parse(fecha, hora):
    return datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")


def hay_solapamiento(conn, fecha, hora, duracion_min):
    nuevo_inicio = _parse(fecha, hora)
    nuevo_fin = nuevo_inicio + timedelta(minutes=duracion_min)
    rows = conn.execute(_q(
        "SELECT hora, duracion_min FROM turnos WHERE fecha = ? AND estado != 'cancelado'"
    ), (fecha,)).fetchall()
    for row in rows:
        existente_inicio = _parse(fecha, row["hora"])
        existente_fin = existente_inicio + timedelta(minutes=row["duracion_min"])
        if nuevo_inicio < existente_fin and existente_inicio < nuevo_fin:
            return True
    return False


def crear_turno(servicio_id, servicio_nombre, duracion_min, precio, fecha, hora, nombre, telefono, notas=""):
    token = secrets.token_urlsafe(24)
    with get_conn() as conn:
        # PostgreSQL serializes booking attempts for the same date. This makes
        # the overlap check + insert atomic across concurrent requests.
        if USE_POSTGRES:
            conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (fecha,))
        else:
            conn.execute("BEGIN IMMEDIATE")
        if hay_solapamiento(conn, fecha, hora, duracion_min):
            raise ValueError("HORARIO_OCUPADO")
        cur = conn.execute(_q(
            """INSERT INTO turnos
               (public_token, servicio_id, servicio_nombre, duracion_min, precio, fecha, hora,
                cliente_nombre, cliente_telefono, notas, estado, creado_en)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?)"""
        ), (token, servicio_id, servicio_nombre, duracion_min, precio, fecha, hora,
            nombre, telefono, notas, datetime.now().isoformat(timespec="seconds")))
        if USE_POSTGRES:
            row = conn.execute("SELECT currval(pg_get_serial_sequence('turnos','id')) AS id").fetchone()
            return row["id"], token
        return cur.lastrowid, token


def turno_por_token(token):
    with get_conn() as conn:
        row = conn.execute(_q("SELECT * FROM turnos WHERE public_token = ?"), (token,)).fetchone()
        return dict(row) if row else None


def turnos_del_dia(fecha):
    with get_conn() as conn:
        rows = conn.execute(_q(
            "SELECT hora, duracion_min FROM turnos WHERE fecha = ? AND estado != 'cancelado'"
        ), (fecha,)).fetchall()
        return [dict(r) for r in rows]


def listar_turnos(fecha=None):
    with get_conn() as conn:
        if fecha:
            rows = conn.execute(_q("SELECT * FROM turnos WHERE fecha = ? ORDER BY hora"), (fecha,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM turnos ORDER BY fecha DESC, hora DESC LIMIT 200").fetchall()
        return [dict(r) for r in rows]


def actualizar_estado(turno_id, estado):
    if estado not in VALID_STATES:
        raise ValueError("ESTADO_INVALIDO")
    with get_conn() as conn:
        conn.execute(_q("UPDATE turnos SET estado = ? WHERE id = ?"), (estado, turno_id))

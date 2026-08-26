"""
Capa de base de datos — BLACK BARBER
SQLite puro (sin ORM) para mantener el proyecto liviano y fácil de portar
a otro negocio. Toda la lógica de negocio específica de "barbería" vive
en SERVICES (abajo) y en las tablas, no en el código de rutas.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent.parent / "black_barber.db"

# ---------------------------------------------------------------------------
# CATÁLOGO DE SERVICIOS — esto es lo primero que hay que editar para
# reutilizar la demo en otro negocio (otra barbería, peluquería, estética).
# ---------------------------------------------------------------------------
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

# horarios de atención por franja de 30' usados para generar turnos disponibles
OPEN_HOUR = 10
CLOSE_HOUR = 20
SLOT_MINUTES = 30


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS turnos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                servicio_id TEXT NOT NULL,
                servicio_nombre TEXT NOT NULL,
                precio INTEGER NOT NULL,
                fecha TEXT NOT NULL,          -- YYYY-MM-DD
                hora TEXT NOT NULL,           -- HH:MM
                cliente_nombre TEXT NOT NULL,
                cliente_telefono TEXT NOT NULL,
                notas TEXT,
                estado TEXT NOT NULL DEFAULT 'pendiente',  -- pendiente | confirmado | cancelado | completado
                creado_en TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_turnos_fecha_hora
            ON turnos (fecha, hora)
        """)


def crear_turno(servicio_id, servicio_nombre, precio, fecha, hora, nombre, telefono, notas=""):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO turnos
               (servicio_id, servicio_nombre, precio, fecha, hora,
                cliente_nombre, cliente_telefono, notas, estado, creado_en)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?)""",
            (servicio_id, servicio_nombre, precio, fecha, hora,
             nombre, telefono, notas, datetime.now().isoformat(timespec="seconds")),
        )
        return cur.lastrowid


def turno_por_id(turno_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM turnos WHERE id = ?", (turno_id,)).fetchone()
        return dict(row) if row else None


def horarios_ocupados(fecha):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT hora FROM turnos WHERE fecha = ? AND estado != 'cancelado'",
            (fecha,),
        ).fetchall()
        return {r["hora"] for r in rows}


def listar_turnos(fecha=None):
    with get_conn() as conn:
        if fecha:
            rows = conn.execute(
                "SELECT * FROM turnos WHERE fecha = ? ORDER BY hora", (fecha,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM turnos ORDER BY fecha DESC, hora DESC LIMIT 200"
            ).fetchall()
        return [dict(r) for r in rows]


def actualizar_estado(turno_id, estado):
    with get_conn() as conn:
        conn.execute("UPDATE turnos SET estado = ? WHERE id = ?", (estado, turno_id))

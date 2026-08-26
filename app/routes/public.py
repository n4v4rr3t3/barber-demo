from datetime import date, datetime, timedelta
from pathlib import Path
import re

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database import (
    SERVICES, BUSINESS, OPEN_HOUR, CLOSE_HOUR, SLOT_MINUTES,
    turnos_del_dia, crear_turno, turno_por_token,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")
router = APIRouter()


def _service(servicio_id: str):
    return next((s for s in SERVICES if s["id"] == servicio_id), None)


def _slots_del_dia():
    slots = []
    t = datetime.combine(date.today(), datetime.min.time()).replace(hour=OPEN_HOUR, minute=0)
    end = t.replace(hour=CLOSE_HOUR, minute=0)
    while t < end:
        slots.append(t.strftime("%H:%M"))
        t += timedelta(minutes=SLOT_MINUTES)
    return slots


def _fecha_valida(fecha):
    try:
        d = date.fromisoformat(fecha)
    except ValueError:
        return False
    return date.today() <= d <= date.today() + timedelta(days=13)


def _slot_disponible(fecha, hora, duracion):
    if hora not in _slots_del_dia():
        return False
    inicio = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
    cierre = inicio.replace(hour=CLOSE_HOUR, minute=0)
    if inicio + timedelta(minutes=duracion) > cierre:
        return False
    for turno in turnos_del_dia(fecha):
        ocupado_inicio = datetime.strptime(f"{fecha} {turno['hora']}", "%Y-%m-%d %H:%M")
        ocupado_fin = ocupado_inicio + timedelta(minutes=turno["duracion_min"])
        if inicio < ocupado_fin and ocupado_inicio < inicio + timedelta(minutes=duracion):
            return False
    return True


@router.get("/")
def landing(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "business": BUSINESS, "services": SERVICES})


@router.get("/reservar")
def reservar(request: Request):
    hoy = date.today()
    dias = [hoy + timedelta(days=i) for i in range(14)]
    return templates.TemplateResponse("reservar.html", {"request": request, "business": BUSINESS, "services": SERVICES, "dias": dias})


@router.get("/api/horarios")
def api_horarios(fecha: str, servicio_id: str = None):
    if not _fecha_valida(fecha):
        raise HTTPException(400, "Fecha inválida")
    servicio = _service(servicio_id) if servicio_id else None
    duracion = servicio["duracion_min"] if servicio else SLOT_MINUTES
    disponibles = [h for h in _slots_del_dia() if _slot_disponible(fecha, h, duracion)]
    return {"fecha": fecha, "disponibles": disponibles}


@router.post("/api/turnos")
def api_crear_turno(
    servicio_id: str = Form(...), fecha: str = Form(...), hora: str = Form(...),
    nombre: str = Form(...), telefono: str = Form(...), notas: str = Form(""),
):
    servicio = _service(servicio_id)
    nombre = nombre.strip()
    telefono = telefono.strip()
    notas = notas.strip()
    if not servicio:
        raise HTTPException(400, "Servicio inválido")
    if not _fecha_valida(fecha):
        raise HTTPException(400, "Fecha inválida")
    if not 2 <= len(nombre) <= 80:
        raise HTTPException(400, "Nombre inválido")
    if not re.fullmatch(r"[+0-9 ()-]{7,25}", telefono):
        raise HTTPException(400, "Teléfono inválido")
    if len(notas) > 500:
        raise HTTPException(400, "Notas demasiado largas")
    if not _slot_disponible(fecha, hora, servicio["duracion_min"]):
        raise HTTPException(409, "Ese horario ya no está disponible")
    try:
        _, token = crear_turno(
            servicio_id=servicio["id"], servicio_nombre=servicio["nombre"],
            duracion_min=servicio["duracion_min"], precio=servicio["precio"],
            fecha=fecha, hora=hora, nombre=nombre, telefono=telefono, notas=notas,
        )
    except ValueError as exc:
        if str(exc) == "HORARIO_OCUPADO":
            raise HTTPException(409, "Ese horario acaba de ser reservado, elegí otro")
        raise
    return RedirectResponse(url=f"/confirmacion/{token}", status_code=303)


@router.get("/confirmacion/{token}")
def confirmacion(request: Request, token: str):
    turno = turno_por_token(token)
    if not turno:
        raise HTTPException(404, "Turno no encontrado")
    return templates.TemplateResponse("confirmacion.html", {"request": request, "business": BUSINESS, "turno": turno})

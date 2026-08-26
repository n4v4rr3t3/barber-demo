from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database import (
    SERVICES, BUSINESS, OPEN_HOUR, CLOSE_HOUR, SLOT_MINUTES,
    horarios_ocupados, crear_turno, turno_por_id,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

router = APIRouter()


def _service(servicio_id: str):
    return next((s for s in SERVICES if s["id"] == servicio_id), None)


def _slots_del_dia():
    """Genera todos los horarios posibles del día (HH:MM) según la franja de atención."""
    slots = []
    t = datetime.combine(date.today(), datetime.min.time()).replace(hour=OPEN_HOUR, minute=0)
    end = t.replace(hour=CLOSE_HOUR, minute=0)
    while t < end:
        slots.append(t.strftime("%H:%M"))
        t += timedelta(minutes=SLOT_MINUTES)
    return slots


@router.get("/")
def landing(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "business": BUSINESS,
        "services": SERVICES,
    })


@router.get("/reservar")
def reservar(request: Request):
    # próximos 14 días para elegir fecha
    hoy = date.today()
    dias = [(hoy + timedelta(days=i)) for i in range(14)]
    return templates.TemplateResponse("reservar.html", {
        "request": request,
        "business": BUSINESS,
        "services": SERVICES,
        "dias": dias,
    })


@router.get("/api/horarios")
def api_horarios(fecha: str):
    ocupados = horarios_ocupados(fecha)
    disponibles = [h for h in _slots_del_dia() if h not in ocupados]
    return {"fecha": fecha, "disponibles": disponibles}


@router.post("/api/turnos")
def api_crear_turno(
    servicio_id: str = Form(...),
    fecha: str = Form(...),
    hora: str = Form(...),
    nombre: str = Form(...),
    telefono: str = Form(...),
    notas: str = Form(""),
):
    servicio = _service(servicio_id)
    if not servicio:
        raise HTTPException(400, "Servicio inválido")
    if hora in horarios_ocupados(fecha):
        raise HTTPException(409, "Ese horario ya fue reservado, elegí otro")

    turno_id = crear_turno(
        servicio_id=servicio["id"],
        servicio_nombre=servicio["nombre"],
        precio=servicio["precio"],
        fecha=fecha,
        hora=hora,
        nombre=nombre,
        telefono=telefono,
        notas=notas,
    )
    return RedirectResponse(url=f"/confirmacion/{turno_id}", status_code=303)


@router.get("/confirmacion/{turno_id}")
def confirmacion(request: Request, turno_id: int):
    turno = turno_por_id(turno_id)
    if not turno:
        raise HTTPException(404, "Turno no encontrado")
    return templates.TemplateResponse("confirmacion.html", {
        "request": request,
        "business": BUSINESS,
        "turno": turno,
    })

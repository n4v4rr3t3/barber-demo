import os
import secrets
from pathlib import Path
from datetime import date

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from app.database import BUSINESS, listar_turnos, actualizar_estado

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

router = APIRouter(prefix="/admin")
security = HTTPBasic()

# En la demo el usuario/clave se fijan por variable de entorno.
# En producción para cada cliente, cambiar ADMIN_USER / ADMIN_PASS.
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "blackbarber2026")


def verificar_credenciales(credentials: HTTPBasicCredentials = Depends(security)):
    usuario_ok = secrets.compare_digest(credentials.username, ADMIN_USER)
    pass_ok = secrets.compare_digest(credentials.password, ADMIN_PASS)
    if not (usuario_ok and pass_ok):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@router.get("")
def dashboard(request: Request, fecha: str = None, user: str = Depends(verificar_credenciales)):
    fecha = fecha or date.today().isoformat()
    turnos = listar_turnos(fecha=fecha)
    todos = listar_turnos()
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "business": BUSINESS,
        "turnos": turnos,
        "fecha": fecha,
        "hoy": date.today().isoformat(),
        "total_turnos": len(todos),
    })


@router.post("/turnos/{turno_id}/estado")
def cambiar_estado(turno_id: int, estado: str = Form(...), fecha: str = Form(...),
                    user: str = Depends(verificar_credenciales)):
    actualizar_estado(turno_id, estado)
    return RedirectResponse(url=f"/admin?fecha={fecha}", status_code=303)

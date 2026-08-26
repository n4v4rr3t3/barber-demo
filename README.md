# BLACK BARBER — Demo reutilizable (Web + Turnos + WhatsApp)

Demo comercial para vender la **OFERTA 2 (Turnos + WhatsApp)**. Pensada para
mostrarse tal cual a un prospecto y, con el catálogo de servicios y datos del
negocio cambiados, reutilizarse para cualquier barbería/peluquería/estética real.

## 1. Correr en local

```bash
cd black-barber
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Abrí:
- Landing: http://localhost:8000
- Reservar turno: http://localhost:8000/reservar
- Panel admin: http://localhost:8000/admin (user: `admin`, pass: `blackbarber2026`,
  configurables por variable de entorno `ADMIN_USER` / `ADMIN_PASS`)

La base SQLite (`black_barber.db`) se crea sola al primer arranque.

## 2. Probarlo end-to-end

1. Entrá a `/reservar`, elegí un servicio, un día y un horario libre.
2. Cargá nombre y teléfono, confirmá.
3. Te lleva a `/confirmacion/<id>` con el "ticket" del turno.
4. Entrá a `/admin`, filtrá por esa fecha y vas a ver el turno cargado.
5. Marcalo como "Confirmado" y verificá que el horario ya no aparezca
   disponible en `/reservar` para ese día (evita doble reserva).

## 3. Reutilizar la demo para OTRO negocio (esto es lo que la hace vendible)

Solo hay que tocar **un archivo**: `app/database.py`

- `BUSINESS` → nombre, dirección, WhatsApp, Instagram, horario, lat/lng.
- `SERVICES` → catálogo de servicios, duración y precio.
- `OPEN_HOUR` / `CLOSE_HOUR` / `SLOT_MINUTES` → franja horaria de turnos.

Nada más cambia. La lógica de reservas, el panel admin y el flujo de
WhatsApp son genéricos. Para copiar a un cliente nuevo:

```bash
cp -r black-barber cliente-nuevo
rm cliente-nuevo/black_barber.db     # empieza con base vacía
# editar cliente-nuevo/app/database.py
```

Si el cliente además quiere otra paleta de colores/tipografía, se toca
solo `static/css/style.css` (todo el color sale de las variables `:root`
al principio del archivo).

## 4. Desplegar en un VPS (Linux + Nginx + HTTPS)

```bash
# En el servidor:
sudo apt update && sudo apt install -y python3-venv nginx certbot python3-certbot-nginx
cd /var/www/black-barber
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Correrlo como servicio con systemd (crear /etc/systemd/system/blackbarber.service):
# [Unit]
# Description=Black Barber
# After=network.target
#
# [Service]
# User=www-data
# WorkingDirectory=/var/www/black-barber
# Environment="ADMIN_USER=admin" "ADMIN_PASS=cambiar-esto"
# ExecStart=/var/www/black-barber/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
# Restart=always
#
# [Install]
# WantedBy=multi-user.target

sudo systemctl enable --now blackbarber

# Nginx como reverse proxy (server block apuntando a 127.0.0.1:8000)
# y certbot para HTTPS:
sudo certbot --nginx -d dominio-del-cliente.com
```

## 5. Qué falta para un cliente real (no incluido en la demo, a propósito)

- Envío real de WhatsApp automático (hoy es un link `wa.me` — para
  confirmaciones/recordatorios automáticos se necesita WhatsApp Business
  API o un proveedor como Twilio/360dialog, eso ya es upsell de la
  OFERTA 3).
- Autenticación admin más robusta que Basic Auth si el cliente maneja
  datos sensibles.
- Carga de fotos reales en la galería (hoy son placeholders).

No se agregó porque no aporta a cerrar el primer cliente — se construye
recién después del anticipo, para el negocio real que lo pida.

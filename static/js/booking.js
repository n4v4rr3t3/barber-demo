// Flujo de reserva BLACK BARBER — vanilla JS, sin dependencias.
(function () {
  const state = { paso: 1, servicio: null, fecha: null, hora: null };
  const form = document.getElementById("booking-form");
  const panels = { 1: document.getElementById("panel-1"), 2: document.getElementById("panel-2"), 3: document.getElementById("panel-3") };
  const stepLabels = { 1: document.getElementById("step-label-1"), 2: document.getElementById("step-label-2"), 3: document.getElementById("step-label-3") };
  const btnNext = document.getElementById("btn-next");
  const btnBack = document.getElementById("btn-back");
  const summaryText = document.getElementById("summary-text");
  const slotGrid = document.getElementById("slot-grid");
  const params = new URLSearchParams(window.location.search);
  const preseleccion = params.get("servicio");

  document.querySelectorAll(".svc-option").forEach((el) => {
    if (preseleccion && el.dataset.id === preseleccion) selectServicio(el);
    el.addEventListener("click", () => selectServicio(el));
  });

  function selectServicio(el) {
    document.querySelectorAll(".svc-option").forEach((o) => o.classList.remove("selected"));
    el.classList.add("selected");
    state.servicio = { id: el.dataset.id, nombre: el.dataset.nombre, precio: el.dataset.precio };
    document.getElementById("input-servicio").value = state.servicio.id;
    state.hora = null;
    document.getElementById("input-hora").value = "";
    if (state.fecha) cargarHorarios(state.fecha);
    updateSummary();
    btnNext.disabled = false;
  }

  document.querySelectorAll(".day-chip").forEach((el) => el.addEventListener("click", () => selectDia(el)));

  function selectDia(el) {
    document.querySelectorAll(".day-chip").forEach((o) => o.classList.remove("selected"));
    el.classList.add("selected");
    state.fecha = el.dataset.fecha;
    state.hora = null;
    document.getElementById("input-fecha").value = state.fecha;
    document.getElementById("input-hora").value = "";
    cargarHorarios(state.fecha);
    updateSummary();
    btnNext.disabled = true;
  }

  async function cargarHorarios(fecha) {
    slotGrid.innerHTML = '<div class="empty-state" style="grid-column:1/-1;">Cargando horarios...</div>';
    try {
      const servicio = state.servicio ? `&servicio_id=${encodeURIComponent(state.servicio.id)}` : "";
      const res = await fetch(`/api/horarios?fecha=${encodeURIComponent(fecha)}${servicio}`);
      if (!res.ok) throw new Error("availability");
      const data = await res.json();
      if (!data.disponibles.length) {
        slotGrid.innerHTML = '<div class="empty-state" style="grid-column:1/-1;">No hay horarios disponibles ese día</div>';
        return;
      }
      slotGrid.innerHTML = "";
      data.disponibles.forEach((hora) => {
        const div = document.createElement("div");
        div.className = "slot";
        div.textContent = hora;
        div.addEventListener("click", () => selectHora(div, hora));
        slotGrid.appendChild(div);
      });
    } catch (e) {
      slotGrid.innerHTML = '<div class="empty-state" style="grid-column:1/-1;">Error cargando horarios, intentá de nuevo</div>';
    }
  }

  function selectHora(el, hora) {
    document.querySelectorAll(".slot").forEach((o) => o.classList.remove("selected"));
    el.classList.add("selected");
    state.hora = hora;
    document.getElementById("input-hora").value = hora;
    updateSummary();
    btnNext.disabled = false;
  }

  function updateSummary() {
    if (state.paso === 1) summaryText.innerHTML = state.servicio ? `<b>${state.servicio.nombre}</b> — $${Number(state.servicio.precio).toLocaleString("es-AR")}` : "Elegí un servicio para continuar";
    else if (state.paso === 2) summaryText.innerHTML = state.hora ? `<b>${state.servicio.nombre}</b> · ${state.fecha} a las <b>${state.hora}</b>` : "Elegí día y horario";
    else summaryText.innerHTML = `<b>${state.servicio.nombre}</b> · ${state.fecha} ${state.hora}hs`;
  }

  function irAPaso(n) {
    state.paso = n;
    [1, 2, 3].forEach((i) => {
      panels[i].style.display = i === n ? "block" : "none";
      stepLabels[i].classList.toggle("active", i === n);
    });
    btnBack.style.display = n === 1 ? "none" : "inline-block";
    btnNext.textContent = n === 3 ? "Confirmar turno →" : "Continuar →";
    btnNext.disabled = n === 1 ? !state.servicio : n === 2 ? !state.hora : false;
    updateSummary();
  }

  btnNext.addEventListener("click", () => {
    if (state.paso < 3) return irAPaso(state.paso + 1);
    const nombre = document.getElementById("nombre").value.trim();
    const telefono = document.getElementById("telefono").value.trim();
    if (!nombre || !telefono) return alert("Completá tu nombre y teléfono para confirmar el turno");
    form.submit();
  });
  btnBack.addEventListener("click", () => { if (state.paso > 1) irAPaso(state.paso - 1); });
  irAPaso(1);
})();

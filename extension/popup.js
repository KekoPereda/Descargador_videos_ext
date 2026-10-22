const SERVIDOR = "http://127.0.0.1:8765";
const HOSTS_YOUTUBE = ["youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"];

const $ = (id) => document.getElementById(id);
const campoUrl = $("url");
const botonDescargar = $("descargar");
const bloqueCalidad = $("bloque-calidad");
const estado = $("estado");
const progreso = $("progreso");
const mensaje = $("mensaje");
const indicador = $("servidor");
const botonEncendido = $("encendido");
const textoEncendido = $("texto-encendido");
const ANFITRION = "com.descargador.youtube";
const botonMostrar = $("mostrar");

let intervalo = null;

function esUrlYoutube(texto) {
  try {
    const url = new URL(texto);
    return ["http:", "https:"].includes(url.protocol) && HOSTS_YOUTUBE.includes(url.hostname);
  } catch {
    return false;
  }
}

function tipoSeleccionado() {
  return document.querySelector('input[name="tipo"]:checked').value;
}

function mostrarEstado(texto, porcentaje = null, clase = "") {
  estado.classList.remove("oculto");
  mensaje.textContent = texto;
  progreso.className = "progreso " + clase;
  if (porcentaje !== null) progreso.style.width = porcentaje + "%";
}

async function comprobarServidor() {
  try {
    const r = await fetch(SERVIDOR + "/salud");
    const datos = await r.json();
    indicador.className = "servidor ok";
    textoEncendido.textContent = "Apagar";
    botonEncendido.title = "Servidor activo" + (datos.ffmpeg ? "" : " (sin ffmpeg: calidad limitada)") + ". Clic para apagar.";
    return true;
  } catch {
    indicador.className = "servidor error";
    textoEncendido.textContent = "Encender";
    botonEncendido.title = "Servidor apagado. Clic para encender.";
    return false;
  }
}

const esperar = (ms) => new Promise((r) => setTimeout(r, ms));

async function encenderServidor() {
  try {
    const respuesta = await chrome.runtime.sendNativeMessage(ANFITRION, { accion: "encender" });
    if (!respuesta || !respuesta.ok) throw new Error((respuesta && respuesta.mensaje) || "Sin respuesta");
  } catch (e) {
    const noInstalado = /not found|no encontrado/i.test(e.message);
    mostrarEstado(
      noInstalado
        ? "No se pudo encender: falta registrar el anfitrión. Ejecuta servidor/instalar.command una vez y recarga la extensión."
        : "No se pudo encender el servidor: " + e.message,
      null, "fallo"
    );
    return false;
  }
  // El servidor tarda un momento en abrir el puerto.
  for (let i = 0; i < 20; i++) {
    if (await comprobarServidor()) return true;
    await esperar(250);
  }
  mostrarEstado("El servidor no respondió. Revisa ~/Library/Logs/DescargadorYouTube.log", null, "fallo");
  return false;
}

async function apagarServidor() {
  try {
    await fetch(SERVIDOR + "/apagar", { method: "POST" });
  } catch {
    // Si ya estaba apagado no hay nada que hacer.
  }
  await esperar(300);
  return !(await comprobarServidor());
}

async function alternarServidor() {
  botonEncendido.disabled = true;
  const activo = await comprobarServidor();
  if (activo) {
    textoEncendido.textContent = "Apagando...";
    if (await apagarServidor()) {
      clearInterval(intervalo);
      chrome.storage.local.remove("trabajo");
      botonDescargar.disabled = false;
      mostrarEstado("Servidor apagado.", 0);
    }
  } else {
    textoEncendido.textContent = "Encendiendo...";
    if (await encenderServidor()) mostrarEstado("Servidor encendido.", 0);
  }
  await comprobarServidor();
  botonEncendido.disabled = false;
}

async function seguirTrabajo(id) {
  clearInterval(intervalo);
  const consultar = async () => {
    try {
      const r = await fetch(`${SERVIDOR}/estado/${encodeURIComponent(id)}`);
      if (!r.ok) throw new Error("Trabajo no encontrado");
      const t = await r.json();

      if (t.estado === "completado") {
        clearInterval(intervalo);
        mostrarEstado(`✅ Listo: ${t.archivo || "descarga completada"}\nGuardado en ${t.carpeta}`, 100, "listo");
        botonMostrar.classList.remove("oculto");
        botonDescargar.disabled = false;
        chrome.storage.local.remove("trabajo");
        chrome.storage.local.set({ ultimo: { id: t.id, archivo: t.archivo, carpeta: t.carpeta } });
      } else if (t.estado === "error") {
        clearInterval(intervalo);
        mostrarEstado("❌ " + t.mensaje, null, "fallo");
        botonDescargar.disabled = false;
        chrome.storage.local.remove("trabajo");
      } else {
        const pct = t.progreso || 0;
        mostrarEstado(`${t.mensaje} ${pct ? pct.toFixed(1) + "%" : ""}`, pct);
        botonDescargar.disabled = true;
      }
    } catch (e) {
      clearInterval(intervalo);
      mostrarEstado("❌ Se perdió la conexión con el servidor local.", null, "fallo");
      botonDescargar.disabled = false;
      chrome.storage.local.remove("trabajo");
    }
  };
  await consultar();
  intervalo = setInterval(consultar, 1000);
}

async function descargar() {
  const url = campoUrl.value.trim();
  if (!esUrlYoutube(url)) {
    mostrarEstado("Introduce una dirección válida de YouTube.", 0, "fallo");
    campoUrl.focus();
    return;
  }
  botonDescargar.disabled = true;
  botonMostrar.classList.add("oculto");
  if (!(await comprobarServidor())) {
    // Si está apagado, se enciende automáticamente.
    mostrarEstado("Encendiendo el servidor...", 0);
    if (!(await encenderServidor())) {
      botonDescargar.disabled = false;
      return;
    }
  }

  mostrarEstado("Enviando petición...", 0);

  try {
    const r = await fetch(SERVIDOR + "/descargar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, tipo: tipoSeleccionado(), calidad: $("calidad").value }),
    });
    const datos = await r.json();
    if (!r.ok) throw new Error(datos.error || "Error desconocido");
    await chrome.storage.local.set({ trabajo: datos.id });
    seguirTrabajo(datos.id);
  } catch (e) {
    mostrarEstado("❌ " + e.message, null, "fallo");
    botonDescargar.disabled = false;
  }
}

async function mostrarEnFinder() {
  botonMostrar.disabled = true;
  try {
    if (!(await comprobarServidor()) && !(await encenderServidor())) return;
    const { ultimo } = await chrome.storage.local.get("ultimo");
    const r = await fetch(SERVIDOR + "/mostrar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: ultimo ? ultimo.id : null }),
    });
    if (!r.ok) throw new Error((await r.json()).error || "Error desconocido");
  } catch (e) {
    mostrarEstado("❌ No se pudo abrir Finder: " + e.message, null, "fallo");
  } finally {
    botonMostrar.disabled = false;
  }
}

async function iniciar() {
  // Preferencias guardadas
  const { tipo, calidad, trabajo, ultimo } = await chrome.storage.local.get(["tipo", "calidad", "trabajo", "ultimo"]);
  if (tipo) document.querySelector(`input[name="tipo"][value="${tipo}"]`).checked = true;
  if (calidad) $("calidad").value = calidad;
  bloqueCalidad.classList.toggle("oculto", tipoSeleccionado() !== "video");

  // Rellenar con la pestaña actual si es YouTube
  const [pestana] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (pestana && pestana.url && esUrlYoutube(pestana.url)) campoUrl.value = pestana.url;

  const activo = await comprobarServidor();
  if (activo && trabajo) {
    seguirTrabajo(trabajo);
  } else if (ultimo) {
    // Recordar la última descarga para poder abrirla en Finder al volver a abrir el popup.
    mostrarEstado(`Última descarga: ${ultimo.archivo || "(sin nombre)"}`, 100, "listo");
    botonMostrar.classList.remove("oculto");
  }
}

document.querySelectorAll('input[name="tipo"]').forEach((radio) =>
  radio.addEventListener("change", () => {
    bloqueCalidad.classList.toggle("oculto", tipoSeleccionado() !== "video");
    chrome.storage.local.set({ tipo: tipoSeleccionado() });
  })
);
$("calidad").addEventListener("change", (e) => chrome.storage.local.set({ calidad: e.target.value }));

$("pegar").addEventListener("click", async () => {
  try {
    campoUrl.value = (await navigator.clipboard.readText()).trim();
  } catch {
    campoUrl.focus();
  }
});

campoUrl.addEventListener("keydown", (e) => { if (e.key === "Enter") descargar(); });
botonDescargar.addEventListener("click", descargar);
botonEncendido.addEventListener("click", alternarServidor);
botonMostrar.addEventListener("click", mostrarEnFinder);

iniciar();

#!/usr/bin/env python3
"""Servidor local para la extensión "Descargador YouTube".

Escucha solo en 127.0.0.1 y usa yt-dlp para descargar audio (MP3) o video (MP4).
No necesita librerías externas además de yt-dlp (y, recomendado, ffmpeg).

Uso:  python3 servidor.py [--puerto 8765] [--carpeta ~/Downloads/YouTube]
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HOSTS_YOUTUBE = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
CALIDADES = {"mejor": None, "1080": 1080, "720": 720, "480": 480}
RE_PROGRESO = re.compile(r"\[download\]\s+([\d.]+)%")
RE_DESTINO = re.compile(r'(?:Destination: |Merging formats into ")(.+?)"?$'
                        r'|^\[download\] (.+) has already been downloaded')

trabajos = {}
bloqueo = threading.Lock()
CARPETA = os.path.expanduser("~/Downloads/YouTube")

WINDOWS = sys.platform == "win32"
if WINDOWS:
    INSTALAR_YTDLP, INSTALAR_FFMPEG = "winget install yt-dlp.yt-dlp", "winget install Gyan.FFmpeg"
else:
    INSTALAR_YTDLP, INSTALAR_FFMPEG = "brew install yt-dlp", "brew install ffmpeg"


def comando_ytdlp():
    ruta = shutil.which("yt-dlp")
    if ruta:
        return [ruta]
    try:
        import yt_dlp  # noqa: F401
        return [sys.executable, "-m", "yt_dlp"]
    except ImportError:
        return None


def hay_ffmpeg():
    return shutil.which("ffmpeg") is not None


def es_url_youtube(url):
    try:
        p = urlparse(url)
    except ValueError:
        return False
    return p.scheme in ("http", "https") and p.hostname in HOSTS_YOUTUBE


def construir_argumentos(url, tipo, calidad):
    args = comando_ytdlp() + [
        "--newline",
        "--no-playlist",
        "--restrict-filenames",
        "-P", CARPETA,
        "-o", "%(title)s [%(id)s].%(ext)s",
    ]
    ffmpeg = hay_ffmpeg()

    if tipo == "audio":
        if ffmpeg:
            args += ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
        else:
            # Sin ffmpeg no se puede convertir: se baja el mejor audio en m4a.
            args += ["-f", "bestaudio[ext=m4a]/bestaudio"]
    else:
        altura = CALIDADES.get(calidad)
        filtro = "[height<=%d]" % altura if altura else ""
        if ffmpeg:
            # Se prefiere H.264 (avc1): QuickTime/Vista Previa no reproducen AV1 ni VP9.
            args += [
                "-f", "bv*%s[vcodec^=avc1]+ba[ext=m4a]/bv*%s[ext=mp4]+ba[ext=m4a]/bv*%s+ba/b%s"
                % (filtro, filtro, filtro, filtro),
                "--merge-output-format", "mp4",
            ]
        else:
            # Sin ffmpeg solo sirven formatos que ya traen audio y video juntos.
            args += ["-f", "b%s[ext=mp4]/b%s" % (filtro, filtro)]

    return args + ["--", url]


def abrir_en_carpeta(ruta, seleccionar):
    """Abre Finder o el Explorador de Windows; con seleccionar=True marca el archivo."""
    if WINDOWS:
        if seleccionar:
            subprocess.run(["explorer", "/select,", os.path.normpath(ruta)], check=False)
        else:
            os.startfile(ruta)
    else:
        subprocess.run(["/usr/bin/open"] + (["-R"] if seleccionar else []) + [ruta], check=False)


def ejecutar(id_trabajo, url, tipo, calidad):
    def actualizar(**campos):
        with bloqueo:
            trabajos[id_trabajo].update(campos)

    try:
        os.makedirs(CARPETA, exist_ok=True)
        proceso = subprocess.Popen(
            construir_argumentos(url, tipo, calidad),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            # En Windows la codificación por defecto no es UTF-8: un título raro no debe romper la lectura.
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if WINDOWS else 0,
        )
        ultimas = []
        for linea in proceso.stdout:
            linea = linea.strip()
            if not linea:
                continue
            ultimas = (ultimas + [linea])[-15:]
            m = RE_PROGRESO.search(linea)
            if m:
                actualizar(progreso=float(m.group(1)), mensaje="Descargando...")
            d = RE_DESTINO.search(linea)
            if d:
                ruta = d.group(1) or d.group(2)
                actualizar(archivo=os.path.basename(ruta), ruta=os.path.join(CARPETA, ruta))
            if linea.startswith("[ExtractAudio]"):
                actualizar(mensaje="Convirtiendo a MP3...")
            elif linea.startswith("[Merger]"):
                actualizar(mensaje="Uniendo audio y video...")
        proceso.wait()

        if proceso.returncode == 0:
            actualizar(estado="completado", progreso=100.0, mensaje="Completado")
        else:
            errores = [l for l in ultimas if "ERROR" in l]
            actualizar(estado="error", mensaje=(errores[-1] if errores else "yt-dlp terminó con error"))
    except Exception as e:  # noqa: BLE001
        actualizar(estado="error", mensaje=str(e))


class Manejador(BaseHTTPRequestHandler):
    def origen_permitido(self):
        origen = self.headers.get("Origin")
        # Sin Origin (p. ej. curl local) o desde una extensión de Chrome: permitido.
        # Cualquier página web queda bloqueada para que no pueda lanzar descargas.
        return origen is None or origen.startswith("chrome-extension://")

    def responder(self, codigo, datos):
        cuerpo = json.dumps(datos).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        origen = self.headers.get("Origin")
        if origen and origen.startswith("chrome-extension://"):
            self.send_header("Access-Control-Allow-Origin", origen)
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_OPTIONS(self):
        if not self.origen_permitido():
            return self.responder(403, {"error": "Origen no permitido"})
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", ""))
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if not self.origen_permitido():
            return self.responder(403, {"error": "Origen no permitido"})
        if self.path == "/salud":
            return self.responder(200, {"ok": True, "ytdlp": comando_ytdlp() is not None,
                                        "ffmpeg": hay_ffmpeg(), "carpeta": CARPETA,
                                        "instalar": {"ytdlp": INSTALAR_YTDLP, "ffmpeg": INSTALAR_FFMPEG}})
        if self.path.startswith("/estado/"):
            id_trabajo = self.path[len("/estado/"):]
            with bloqueo:
                t = trabajos.get(id_trabajo)
                t = dict(t) if t else None
            if not t:
                return self.responder(404, {"error": "Trabajo no encontrado"})
            return self.responder(200, t)
        self.responder(404, {"error": "Ruta no encontrada"})

    def do_POST(self):
        if not self.origen_permitido():
            return self.responder(403, {"error": "Origen no permitido"})
        if self.path == "/apagar":
            self.responder(200, {"ok": True})
            # shutdown() espera a que termine serve_forever(): hay que llamarlo desde otro hilo.
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        if self.path not in ("/descargar", "/mostrar"):
            return self.responder(404, {"error": "Ruta no encontrada"})
        try:
            largo = int(self.headers.get("Content-Length", 0))
            datos = json.loads(self.rfile.read(min(largo, 10000)) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self.responder(400, {"error": "JSON inválido"})

        if self.path == "/mostrar":
            return self.mostrar_en_carpeta(datos.get("id"))

        url = str(datos.get("url", "")).strip()
        tipo = datos.get("tipo")
        calidad = datos.get("calidad", "mejor")

        if not es_url_youtube(url):
            return self.responder(400, {"error": "La dirección no es de YouTube"})
        if tipo not in ("audio", "video"):
            return self.responder(400, {"error": "Tipo debe ser 'audio' o 'video'"})
        if calidad not in CALIDADES:
            calidad = "mejor"
        if comando_ytdlp() is None:
            return self.responder(500, {"error": "yt-dlp no está instalado (%s)" % INSTALAR_YTDLP})

        id_trabajo = uuid.uuid4().hex
        with bloqueo:
            trabajos[id_trabajo] = {"id": id_trabajo, "estado": "en_curso", "progreso": 0.0,
                                    "mensaje": "Preparando...", "archivo": None, "ruta": None,
                                    "carpeta": CARPETA,
                                    "tipo": tipo}
        threading.Thread(target=ejecutar, args=(id_trabajo, url, tipo, calidad), daemon=True).start()
        self.responder(202, {"id": id_trabajo})

    def mostrar_en_carpeta(self, id_trabajo):
        # Solo se abren rutas que el propio servidor descargó, nunca una ruta enviada por el cliente.
        with bloqueo:
            t = trabajos.get(id_trabajo) if isinstance(id_trabajo, str) else None
            ruta = t.get("ruta") if t else None
        os.makedirs(CARPETA, exist_ok=True)
        if ruta and os.path.exists(ruta):
            abrir_en_carpeta(ruta, seleccionar=True)
            return self.responder(200, {"ok": True, "ruta": ruta})
        # Si el archivo ya no existe (o el servidor se reinició), se abre la carpeta de descargas.
        abrir_en_carpeta(CARPETA, seleccionar=False)
        self.responder(200, {"ok": True, "ruta": CARPETA})

    def log_message(self, formato, *args):
        sys.stderr.write("[servidor] %s\n" % (formato % args))


def main():
    global CARPETA
    parser = argparse.ArgumentParser(description="Servidor local del Descargador YouTube")
    parser.add_argument("--puerto", type=int, default=8765)
    parser.add_argument("--carpeta", default=CARPETA)
    opciones = parser.parse_args()
    CARPETA = os.path.expanduser(opciones.carpeta)

    if comando_ytdlp() is None:
        print("⚠️  yt-dlp no encontrado. Instálalo con:  " + INSTALAR_YTDLP)
    if not hay_ffmpeg():
        print("⚠️  ffmpeg no encontrado: no habrá MP3 ni video en alta calidad. Instálalo con:  " + INSTALAR_FFMPEG)

    servidor = ThreadingHTTPServer(("127.0.0.1", opciones.puerto), Manejador)
    print("✅ Servidor escuchando en http://127.0.0.1:%d" % opciones.puerto)
    print("📁 Las descargas se guardan en %s" % CARPETA)
    print("   (Ctrl+C para detener)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    servidor.server_close()
    print("\nServidor detenido.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Anfitrión de Native Messaging: permite que la extensión encienda el servidor local.

Chrome lo ejecuta cuando la extensión llama a chrome.runtime.sendNativeMessage().
Protocolo: cada mensaje es un entero de 4 bytes (longitud) seguido de JSON en UTF-8.
"""

import json
import os
import socket
import struct
import subprocess
import sys

DIRECTORIO = os.path.dirname(os.path.abspath(__file__))
SERVIDOR = os.path.join(DIRECTORIO, "servidor.py")
WINDOWS = sys.platform == "win32"
if WINDOWS:
    REGISTRO = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                            "DescargadorYouTube", "DescargadorYouTube.log")
else:
    REGISTRO = os.path.expanduser("~/Library/Logs/DescargadorYouTube.log")
PUERTO = 8765


def leer_mensaje():
    cabecera = sys.stdin.buffer.read(4)
    if len(cabecera) < 4:
        return None
    largo = struct.unpack("<I", cabecera)[0]
    return json.loads(sys.stdin.buffer.read(largo).decode("utf-8"))


def enviar_mensaje(datos):
    cuerpo = json.dumps(datos).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(cuerpo)) + cuerpo)
    sys.stdout.buffer.flush()


def servidor_activo():
    try:
        with socket.create_connection(("127.0.0.1", PUERTO), timeout=0.5):
            return True
    except OSError:
        return False


def encender():
    if servidor_activo():
        return {"ok": True, "mensaje": "El servidor ya estaba encendido"}

    entorno = dict(os.environ)
    # El registro se escribe en UTF-8 aunque Windows use otra codificación por defecto.
    entorno["PYTHONIOENCODING"] = "utf-8"
    if WINDOWS:
        # winget deja aquí los accesos a yt-dlp y ffmpeg; así se encuentran aunque
        # se hayan instalado después de abrir Chrome.
        extra = [os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links")]
    else:
        # Chrome lanza este proceso con un PATH mínimo: se añaden las rutas de Homebrew
        # para que el servidor encuentre yt-dlp y ffmpeg.
        extra = ["/opt/homebrew/bin", "/usr/local/bin"]
    entorno["PATH"] = os.pathsep.join(extra + [entorno.get("PATH", os.defpath)])

    os.makedirs(os.path.dirname(REGISTRO), exist_ok=True)
    with open(REGISTRO, "a") as registro:
        def lanzar(**opciones):
            subprocess.Popen(
                [sys.executable, SERVIDOR, "--puerto", str(PUERTO)],
                cwd=DIRECTORIO,
                env=entorno,
                stdin=subprocess.DEVNULL,
                stdout=registro,
                stderr=registro,
                **opciones,
            )

        if not WINDOWS:
            # Sesión nueva para que el servidor siga vivo cuando Chrome cierre este anfitrión.
            lanzar(start_new_session=True)
        else:
            # Chrome mete al anfitrión en un "job" que cierra a sus hijos al terminar:
            # el servidor sale de ese job, sin ventana de consola.
            flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            try:
                lanzar(creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB)
            except OSError:
                lanzar(creationflags=flags)
    return {"ok": True, "mensaje": "Servidor iniciado"}


def main():
    mensaje = leer_mensaje() or {}
    accion = mensaje.get("accion")
    try:
        if accion == "encender":
            respuesta = encender()
        elif accion == "estado":
            respuesta = {"ok": True, "activo": servidor_activo()}
        else:
            respuesta = {"ok": False, "mensaje": "Acción desconocida: %s" % accion}
    except Exception as e:  # noqa: BLE001
        respuesta = {"ok": False, "mensaje": str(e)}
    enviar_mensaje(respuesta)


if __name__ == "__main__":
    main()

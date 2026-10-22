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

    # Chrome lanza este proceso con un PATH mínimo: se añaden las rutas de Homebrew
    # para que el servidor encuentre yt-dlp y ffmpeg.
    entorno = dict(os.environ)
    entorno["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + entorno.get("PATH", "/usr/bin:/bin")

    os.makedirs(os.path.dirname(REGISTRO), exist_ok=True)
    with open(REGISTRO, "a") as registro:
        # Sesión nueva para que el servidor siga vivo cuando Chrome cierre este anfitrión.
        subprocess.Popen(
            [sys.executable, SERVIDOR, "--puerto", str(PUERTO)],
            cwd=DIRECTORIO,
            env=entorno,
            stdin=subprocess.DEVNULL,
            stdout=registro,
            stderr=registro,
            start_new_session=True,
        )
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

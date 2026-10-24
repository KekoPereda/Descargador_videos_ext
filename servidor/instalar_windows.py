"""Instalación en Windows (lo ejecuta instalar.bat).

1. Comprueba que estén yt-dlp y ffmpeg y, si faltan, ofrece instalarlos con winget.
2. Registra el anfitrión de Native Messaging para que la extensión pueda encender el servidor.
   Volver a ejecutarlo si mueves la carpeta del proyecto.
"""

import json
import os
import shutil
import subprocess
import sys
import winreg

NOMBRE = "com.descargador.youtube"
ID_EXTENSION = "pihjhbdhoalklaflineebolmiocfhdll"
DIRECTORIO = os.path.dirname(os.path.abspath(__file__))
NAVEGADORES = {
    "Google Chrome": r"Software\Google\Chrome",
    "Chromium": r"Software\Chromium",
    "Brave": r"Software\BraveSoftware\Brave-Browser",
    "Microsoft Edge": r"Software\Microsoft\Edge",
}
REQUISITOS = [
    # (programa, paquete de winget, para qué sirve, obligatorio)
    ("yt-dlp", "yt-dlp.yt-dlp", "es el que descarga los videos", True),
    ("ffmpeg", "Gyan.FFmpeg", "convierte a MP3 y une audio y video en alta calidad", False),
]


def encontrar(programa):
    # winget deja los programas aquí, aunque esta ventana aún no tenga el PATH actualizado.
    enlaces = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links")
    return shutil.which(programa) or shutil.which(programa, path=enlaces)


def comprobar_requisitos():
    print("Comprobando programas necesarios...\n")
    print("  ✅ Python %d.%d" % sys.version_info[:2])
    faltan = []
    for programa, paquete, uso, obligatorio in REQUISITOS:
        if encontrar(programa):
            print("  ✅ %s" % programa)
        else:
            nivel = "FALTA (obligatorio)" if obligatorio else "FALTA (recomendado)"
            print("  ❌ %s: %s. %s" % (programa, nivel, uso[0].upper() + uso[1:]))
            faltan.append((programa, paquete))
    if not faltan:
        print()
        return

    comando = "winget install " + " ".join(paquete for _, paquete in faltan)
    print("\nPara instalar lo que falta, abre PowerShell y ejecuta:\n\n    %s\n" % comando)
    if not shutil.which("winget"):
        print("(winget no está disponible: instala \"App Installer\" desde Microsoft Store,")
        print(" o descarga yt-dlp de https://github.com/yt-dlp/yt-dlp/releases y ffmpeg de https://www.gyan.dev/ffmpeg/builds/)\n")
        return
    if input("¿Quieres instalarlo ahora? (s/n): ").strip().lower() in ("s", "si", "sí"):
        for programa, paquete in faltan:
            print("\nInstalando %s..." % programa)
            subprocess.run(["winget", "install", "-e", "--id", paquete,
                            "--accept-source-agreements", "--accept-package-agreements"], check=False)
            print("  %s %s" % ("✅" if encontrar(programa) else "⚠️  No se pudo comprobar", programa))
        print()


def registrar_anfitrion():
    # Chrome en Windows no ejecuta un .py directamente: se usa un .bat con la ruta de este Python.
    lanzador = os.path.join(DIRECTORIO, "anfitrion.bat")
    with open(lanzador, "w", encoding="oem", newline="\r\n") as f:
        f.write('@echo off\n"%s" "%%~dp0anfitrion.py" %%*\n' % sys.executable)

    manifiesto = os.path.join(DIRECTORIO, NOMBRE + ".json")
    with open(manifiesto, "w", encoding="utf-8") as f:
        json.dump({
            "name": NOMBRE,
            "description": "Enciende el servidor local del Descargador YouTube",
            "path": lanzador,
            "type": "stdio",
            "allowed_origins": ["chrome-extension://%s/" % ID_EXTENSION],
        }, f, indent=2)

    for navegador, clave in NAVEGADORES.items():
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, clave + r"\NativeMessagingHosts" + "\\" + NOMBRE) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, manifiesto)
        print("✅ Registrado en %s" % navegador)


def main():
    comprobar_requisitos()
    registrar_anfitrion()
    print("\nListo. Recarga la extensión en chrome://extensions.")


if __name__ == "__main__":
    main()

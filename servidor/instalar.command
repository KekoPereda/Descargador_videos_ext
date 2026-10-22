#!/bin/bash
# Registra el anfitrión de Native Messaging para que la extensión pueda encender el servidor.
# Ejecutar una sola vez (doble clic en Finder). Volver a ejecutarlo si mueves la carpeta del proyecto.
set -e
cd "$(dirname "$0")"

NOMBRE="com.descargador.youtube"
ID_EXTENSION="pihjhbdhoalklaflineebolmiocfhdll"
ANFITRION="$(pwd)/anfitrion.py"

chmod +x "$ANFITRION" servidor.py

MANIFIESTO=$(cat <<EOF
{
  "name": "$NOMBRE",
  "description": "Enciende el servidor local del Descargador YouTube",
  "path": "$ANFITRION",
  "type": "stdio",
  "allowed_origins": ["chrome-extension://$ID_EXTENSION/"]
}
EOF
)

SOPORTE="$HOME/Library/Application Support"
instalado=0
for NAVEGADOR in "Google/Chrome" "Google/Chrome Beta" "Chromium" "BraveSoftware/Brave-Browser" "Microsoft Edge"; do
  if [ -d "$SOPORTE/$NAVEGADOR" ]; then
    mkdir -p "$SOPORTE/$NAVEGADOR/NativeMessagingHosts"
    echo "$MANIFIESTO" > "$SOPORTE/$NAVEGADOR/NativeMessagingHosts/$NOMBRE.json"
    echo "✅ Registrado en $NAVEGADOR"
    instalado=1
  fi
done

if [ "$instalado" = 0 ]; then
  echo "⚠️  No se encontró ningún navegador compatible."
  exit 1
fi
echo "Listo. Recarga la extensión en chrome://extensions."

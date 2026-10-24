# Descargador YouTube (extensión de Chrome)

Extensión de Chrome para descargar **audio (MP3)** o **video (MP4)** de YouTube.
Funciona en **macOS** y **Windows** (también en Edge y Brave).
Pegas la dirección (o se rellena sola si estás viendo un video), eliges audio o video y pulsas **Descargar**.

## Cómo funciona

Chrome no permite que una extensión descargue directamente de YouTube, así que hay dos piezas:

```
[Extensión (popup)] --HTTP--> [Servidor local 127.0.0.1:8765] --> yt-dlp (+ ffmpeg) --> Descargas/YouTube
```

- `extension/` — la extensión de Chrome (Manifest V3).
- `servidor/servidor.py` — servidor local en Python (solo librería estándar) que lanza `yt-dlp`.

## Instalación en Windows

1. **Python 3**: si no lo tienes, instálalo desde <https://www.python.org/downloads/>
   (marca *Add python.exe to PATH*) o en PowerShell: `winget install Python.Python.3.12`.
2. Doble clic en `servidor\instalar.bat`. Comprueba si faltan **yt-dlp** o **ffmpeg**,
   te muestra el comando para instalarlos (`winget install yt-dlp.yt-dlp Gyan.FFmpeg`)
   y te ofrece instalarlos en ese momento. Después registra el botón de encendido.
   Si mueves la carpeta del proyecto, vuelve a ejecutarlo.
3. Carga la extensión en Chrome (paso 3 de abajo).

El registro del servidor se guarda en `%LOCALAPPDATA%\DescargadorYouTube\DescargadorYouTube.log`
y se puede arrancar a mano con doble clic en `servidor\iniciar.bat`.

## Instalación en macOS

### 1. Instalar yt-dlp y ffmpeg

```bash
brew install yt-dlp ffmpeg
```

`ffmpeg` es necesario para convertir a MP3 y para unir audio y video en alta calidad.
Sin él, el audio se baja en M4A y el video se limita a los formatos que YouTube ofrece ya combinados (normalmente 360p).

### 2. Registrar el botón de encendido (una sola vez)

Doble clic en `servidor/instalar.command`. Así la extensión podrá encender el servidor
por sí misma mediante *Native Messaging* (`servidor/anfitrion.py`).
Si mueves la carpeta del proyecto, vuelve a ejecutarlo.

A partir de ahí no hace falta abrir nada a mano:

- El botón **Encender / Apagar** del popup arranca o detiene el servidor.
- Si pulsas **Descargar** con el servidor apagado, se enciende automáticamente.
- El registro del servidor se guarda en `~/Library/Logs/DescargadorYouTube.log`.

También se puede arrancar a mano (doble clic en `servidor/iniciar.command` o desde la terminal):

```bash
python3 servidor/servidor.py
# opciones: --puerto 8765  --carpeta ~/Downloads/YouTube
```

Si cambias el puerto, cámbialo también en `extension/popup.js` (`SERVIDOR`),
`extension/manifest.json` (`host_permissions`) y `servidor/anfitrion.py` (`PUERTO`).

### 3. Cargar la extensión en Chrome

1. Abre `chrome://extensions`.
2. Activa **Modo de desarrollador** (arriba a la derecha).
3. Pulsa **Cargar descomprimida** y selecciona la carpeta `extension/`.
4. Fija el icono en la barra de herramientas.

## Uso

1. Abre un video de YouTube (o copia su dirección).
2. Haz clic en el icono de la extensión.
3. Comprueba/pega la dirección y elige **Audio** o **Video** (y la calidad, si es video).
4. Pulsa **Descargar**. Verás el progreso; el archivo se guarda en `Descargas/YouTube` de tu usuario.
5. Al terminar, pulsa **📁 Mostrar en Finder** (en Windows, **Mostrar en el Explorador**) para ver el archivo.
   El botón recuerda la última descarga aunque cierres y vuelvas a abrir el popup.

Si al equipo le falta yt-dlp o ffmpeg, el popup muestra un aviso amarillo con el comando
para instalarlo (botón **Copiar**).

El botón de la esquina superior indica el estado del servidor (verde = activo, rojo = apagado)
y al pulsarlo lo enciende o lo apaga.

> La extensión tiene un ID fijo (`pihjhbdhoalklaflineebolmiocfhdll`, definido por `key` en el
> manifiesto) para que el registro del anfitrión siga funcionando aunque recargues la extensión.

## Seguridad

- El servidor solo escucha en `127.0.0.1` (no es accesible desde la red).
- Rechaza peticiones de páginas web (descargar o apagar); solo acepta las de extensiones de Chrome.
- El anfitrión de Native Messaging solo puede usarlo esta extensión (`allowed_origins`) y solo sabe encender el servidor.
- Solo acepta direcciones de YouTube y nunca usa la shell para lanzar `yt-dlp`.

## Problemas frecuentes

| Síntoma | Solución |
|---|---|
| "Falta instalar la parte local" | Ejecuta `servidor/instalar.command` (Mac) o `servidor\instalar.bat` (Windows) y recarga la extensión. |
| El servidor no responde al encender | Revisa el registro: `~/Library/Logs/DescargadorYouTube.log` (Mac) o `%LOCALAPPDATA%\DescargadorYouTube\DescargadorYouTube.log` (Windows). |
| Error de yt-dlp al descargar | YouTube cambia a menudo: `brew upgrade yt-dlp` (Mac) o `winget upgrade yt-dlp.yt-dlp` (Windows). |
| El audio sale en .m4a | Instala ffmpeg: `brew install ffmpeg` (Mac) o `winget install Gyan.FFmpeg` (Windows). |
| Windows: "No se encontró Python" | Instala Python 3 (ver arriba) y vuelve a ejecutar `instalar.bat`. |

## Aviso legal

Usa esta herramienta solo con contenido que tengas derecho a descargar (tuyo, de dominio público,
con licencia Creative Commons o con permiso del autor). Las condiciones de YouTube restringen la
descarga de contenido sin autorización.

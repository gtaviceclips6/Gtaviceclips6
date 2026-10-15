# GTA VICE CLIPS 6 - montaje profesional del short vertical
#  - Pantalla partida (camara del streamer arriba, juego abajo) si detecta una facecam
#  - Si no hay facecam separada: video centrado sobre fondo difuminado
#  - Subtitulos tipo karaoke (palabra a palabra, la que suena en amarillo)
#  - Zoom rapido en los momentos de mas volumen
#  - Gancho grande los primeros segundos, titulo, @gtaviceclips6 y barra de progreso
import os, re, json, subprocess, textwrap, pathlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
HANDLE = "@gtaviceclips6"
FUENTES = ["fonts/Anton-Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
FUENTE = next((f for f in FUENTES if os.path.exists(f)), FUENTES[-1])
FAMILIA = "Anton" if "Anton" in FUENTE else "DejaVu Sans"
ROSA, CIAN, AMARILLO, BLANCO = (255, 46, 136), (0, 229, 255), (255, 230, 0), (255, 255, 255)
CAM_ALTO = 700          # alto del panel de la camara en pantalla partida
GANCHO_SEG = 2.6        # segundos que se ve el gancho


def ejecutar(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip().splitlines()[-1][:300])
    return p.stdout


def duracion(video):
    try:
        return float(ejecutar(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)]))
    except Exception:
        return 0.0


def audio_16k(video):
    crudo = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(video), "-ac", "1", "-ar", "16000",
                            "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(crudo, np.float32)


# ---------------------------------------------------------------- transcripcion
def transcribir(video):
    """Lista de (palabra, inicio, fin). Vacia si no hay voz o falla."""
    try:
        from faster_whisper import WhisperModel
        audio = audio_16k(video)
        if not len(audio):
            return []
        modelo = WhisperModel(os.environ.get("WHISPER", "small"), device="cpu", compute_type="int8")
        segs, _ = modelo.transcribe(audio, language="es", word_timestamps=True, vad_filter=True)
        return [(w.word.strip(), w.start, w.end) for s in segs for w in (s.words or []) if w.word.strip()]
    except Exception as e:
        print("Subtitulos:", e)
        return []


def tiempo_ass(s):
    h, s = divmod(max(0, s), 3600)
    m, s = divmod(s, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def ass_karaoke(palabras, ruta, margen_v):
    """Subtitulos de 3 en 3 palabras; la palabra que suena sale en amarillo y un poco mas grande."""
    limpia = lambda w: w.upper().replace("{", "").replace("}", "")
    ev = []
    for i in range(0, len(palabras), 3):
        g = palabras[i:i + 3]
        for k, (w, ini, fin) in enumerate(g):
            fin_k = g[k + 1][1] if k + 1 < len(g) else fin + 0.08
            partes = []
            for j, (w2, _, _) in enumerate(g):
                if j == k:
                    partes.append(r"{\c&H0000E6FF&\fscx112\fscy112}" + limpia(w2) + r"{\c&H00FFFFFF&\fscx100\fscy100}")
                else:
                    partes.append(limpia(w2))
            ev.append(f"Dialogue: 0,{tiempo_ass(ini)},{tiempo_ass(fin_k)},Sub,,0,0,0,,{' '.join(partes)}")
    cab = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{FAMILIA},92,&H00FFFFFF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,1,0,1,8,4,2,60,60,{margen_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    pathlib.Path(ruta).write_text(cab + "\n".join(ev) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- analisis del video
def detectar_cam(video):
    """Busca una facecam pequena y fija (esquina del directo). Devuelve (x, y, w, h) a recortar o None."""
    try:
        import cv2
    except ImportError:
        return None
    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    fw, fh = cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    if not fw or fh > fw:
        return None
    cas = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    caras, muestras = [], 10
    for k in range(muestras):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * (k + 0.5) / muestras))
        ok, fr = cap.read()
        if not ok:
            continue
        gris = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        for (x, y, w, h) in cas.detectMultiScale(gris, 1.1, 6, minSize=(int(fh * 0.05), int(fh * 0.05))):
            caras.append((x + w / 2, y + h / 2, w, h))
    cap.release()
    if not caras:
        return None
    # agrupa caras en la misma posicion: la facecam es la que se repite en casi todos los fotogramas
    mejor, votos = None, 0
    for c in caras:
        cerca = [d for d in caras if abs(d[0] - c[0]) < fw * 0.04 and abs(d[1] - c[1]) < fh * 0.04]
        if len(cerca) > votos:
            mejor, votos = cerca, len(cerca)
    if votos < muestras * 0.5:
        return None
    cx, cy = np.mean([c[0] for c in mejor]), np.mean([c[1] for c in mejor])
    tam = np.mean([c[2] for c in mejor])
    # Solo es facecam si la cara es pequena y esta pegada a un lado (esquina del directo).
    # Si la cara es grande o esta en el centro, el streamer sale a camara completa: sin partir.
    if tam > fh * 0.2 or fw * 0.3 < cx < fw * 0.7:
        return None
    w = min(fw, tam * 3.6)
    h = w * CAM_ALTO / W
    x = min(max(0, cx - w / 2), fw - w)
    y = min(max(0, cy - h * 0.45), fh - h)
    return int(x) // 2 * 2, int(y) // 2 * 2, int(w) // 2 * 2, int(h) // 2 * 2


def picos_volumen(video, maximo=3):
    """Momentos de mas volumen (gritos, risas) para hacer zoom."""
    a = audio_16k(video)
    if len(a) < 16000 * 3:
        return []
    paso = 1600  # 0,1 s
    rms = np.sqrt(np.convolve(a ** 2, np.ones(paso) / paso, "valid")[::paso])
    umbral = rms.mean() + 2.2 * rms.std()
    picos = []
    for i in np.argsort(rms)[::-1]:
        t = i * 0.1
        if rms[i] < umbral or len(picos) >= maximo:
            break
        if t > 0.8 and all(abs(t - p) > 4 for p in picos):
            picos.append(t)
    return sorted(picos)


# ---------------------------------------------------------------- textos (imagenes)
def _fuente(tam):
    return ImageFont.truetype(FUENTE, tam)


def _texto(d, y, txt, f, color, borde, col_borde=(0, 0, 0)):
    w = d.textlength(txt, font=f)
    d.text(((W - w) / 2, y), txt, font=f, fill=color, stroke_width=borde, stroke_fill=col_borde)


def _limpiar(t):
    t = " ".join("".join(c for c in t if ord(c) < 0x2000).split())        # sin emojis (salen como cuadrados)
    return re.sub(r"\b(GTA|Xbox|PS) (?=\S)", "\\1\u00a0", t, flags=re.I)   # "GTA 6" no se parte


def png_titulo(titulo, y0, png, tam=84, ancho=20, lineas_max=3):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = _fuente(tam)
    y = y0
    for l in textwrap.wrap(_limpiar(titulo).upper(), ancho)[:lineas_max] or ["GTA 6"]:
        _texto(d, y, l, f, BLANCO, 8, ROSA)
        y += int(tam * 1.18)
    im.save(png)


def png_gancho(gancho, y0, png):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = _fuente(118)
    lineas = textwrap.wrap(_limpiar(gancho).upper(), 15)[:2] or ["MIRA ESTO"]
    alto = len(lineas) * 140 + 50
    d.rounded_rectangle([40, y0 - 25, W - 40, y0 - 25 + alto], 30, fill=(10, 0, 30, 200), outline=AMARILLO + (255,), width=6)
    y = y0
    for l in lineas:
        _texto(d, y, l, f, AMARILLO, 9, (0, 0, 0))
        y += 140
    im.save(png)


def png_marca(png, y=70):
    """@gtaviceclips6 arriba a la derecha, en una pastilla oscura (no choca con subtitulos del juego)."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = _fuente(40)
    w = d.textlength(HANDLE, font=f)
    x = W - w - 60
    d.rounded_rectangle([x - 22, y - 10, x + w + 22, y + 58], 30, fill=(10, 0, 30, 170))
    d.text((x, y), HANDLE, font=f, fill=BLANCO)
    im.save(png)


# ---------------------------------------------------------------- montaje
def montar(src, salida, dur, titulo, gancho="", palabras=None, tmp="tmp"):
    """Hace el short final. Devuelve el modo usado ('partida' o 'centrado')."""
    tmp = pathlib.Path(tmp); tmp.mkdir(exist_ok=True)
    base = tmp / pathlib.Path(salida).stem
    cam = detectar_cam(src)
    modo = "partida" if cam else "centrado"
    p_tit, p_gan, p_mar, ass = (f"{base}_tit.png", f"{base}_gan.png", f"{base}_mar.png", f"{base}.ass")
    if modo == "partida":
        x, y, w, h = cam
        juego_alto = H - CAM_ALTO
        video = (f"[0:v]crop={w}:{h}:{x}:{y},scale={W}:{CAM_ALTO}[cam];"
                 f"[0:v]scale=-2:{juego_alto},crop={W}:{juego_alto}[juego];"
                 f"[cam][juego]vstack[base]")
        png_titulo(titulo, CAM_ALTO - 115, p_tit, tam=70, ancho=24, lineas_max=2)
        png_gancho(gancho or titulo, CAM_ALTO - 120, p_gan)
        margen_subs = juego_alto - 330          # subtitulos en la parte alta del juego
    else:
        video = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                 f"boxblur=25:2,eq=brightness=-0.2[bg];[0:v]scale={W}:-2[fg];"
                 f"[bg][fg]overlay=(W-w)/2:(H-h)/2[base]")
        png_titulo(titulo, 260, p_tit)
        png_gancho(gancho or titulo, 330, p_gan)
        margen_subs = 470
    png_marca(p_mar)

    # zoom rapido en los picos de volumen
    zonas = "+".join(f"between(t,{max(0, p - 0.15):.2f},{p + 0.6:.2f})" for p in picos_volumen(src))
    zoom = (f";[base]scale=w='{W}*(1+0.09*({zonas}))':h=-2:eval=frame,crop={W}:{H}[z]" if zonas
            else ";[base]null[z]")
    f = video + zoom
    f += f";[z][1:v]overlay=0:0:enable='gte(t,{GANCHO_SEG})'[v1]"
    f += f";[v1][2:v]overlay=0:0:enable='lt(t,{GANCHO_SEG})'[v2]"
    f += ";[v2][3:v]overlay=0:0[v3]"
    if palabras:
        ass_karaoke(palabras, ass, margen_subs)
        f += f";[v3]subtitles={ass}:fontsdir=fonts[v4]"
    else:
        f += ";[v3]null[v4]"
    f += f";[v4]drawbox=x=0:y={H - 14}:w='iw*t/{max(dur, 1):.2f}':h=14:color=0xFF2E88@1:t=fill[v]"
    ejecutar(["ffmpeg", "-y", "-i", str(src), "-i", p_tit, "-i", p_gan, "-i", p_mar, "-filter_complex", f,
              "-map", "[v]", "-map", "0:a?", "-t", f"{dur:.2f}", "-r", "30",
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-maxrate", "6M", "-bufsize", "12M",
              "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(salida)])
    return modo

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
from config import MARCA, JUEGO
HANDLE = MARCA["handle"]
FUENTES = ["fonts/Anton-Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
FUENTE = next((f for f in FUENTES if os.path.exists(f)), FUENTES[-1])
FAMILIA = "Anton" if "Anton" in FUENTE else "DejaVu Sans"
ROSA, CIAN, AMARILLO = tuple(MARCA["color_principal"]), tuple(MARCA["color_secundario"]), tuple(MARCA["color_resaltado"])
BLANCO = (255, 255, 255)
CAM_ALTO = 700          # alto del panel de la camara en pantalla partida
JUEGO_Y = 760           # donde empieza el directo entero, debajo de la camara
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


def fotogramas(video, n=4, ancho=480):
    """n fotogramas repartidos por el clip, en JPEG base64 (para que la IA 'vea' el clip)."""
    import base64
    dur = duracion(video) or 10
    out = []
    for k in range(n):
        t = dur * (k + 0.5) / n
        jpg = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                              "-vf", f"scale={ancho}:-2", "-f", "image2", "-c:v", "mjpeg", "-q:v", "6", "-"],
                             capture_output=True).stdout
        if jpg:
            out.append(base64.b64encode(jpg).decode())
    return out


# ---------------------------------------------------------------- transcripcion
VOCABULARIO = JUEGO["vocabulario"]


def transcribir(video):
    """Lista de (palabra, inicio, fin). Vacia si no hay voz o falla."""
    try:
        from faster_whisper import WhisperModel
        audio = audio_16k(video)
        if not len(audio):
            return []
        modelo = WhisperModel(os.environ.get("WHISPER", "medium"), device="cpu", compute_type="int8")
        segs, _ = modelo.transcribe(audio, language="es", word_timestamps=True, vad_filter=True,
                                    initial_prompt=VOCABULARIO, condition_on_previous_text=False)
        return [(w.word.strip(), w.start, w.end) for s in segs for w in (s.words or []) if w.word.strip()]
    except Exception as e:
        print("Subtitulos:", e)
        return []


def tiempo_ass(s):
    h, s = divmod(max(0, s), 3600)
    m, s = divmod(s, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def agrupar(palabras, max_pal=3, max_letras=18, pausa=0.45):
    """Junta palabras en frases cortas cortando en pausas y signos, como hacen los editores de shorts."""
    grupos, g = [], []
    for i, (w, ini, fin) in enumerate(palabras):
        if g and (len(g) >= max_pal or len(" ".join(x[0] for x in g + [(w, 0, 0)])) > max_letras
                  or ini - g[-1][2] > pausa):
            grupos.append(g); g = []
        g.append((w, ini, fin))
        if re.search(r"[.!?…,;:]$", w):
            grupos.append(g); g = []
    if g:
        grupos.append(g)
    return grupos


def ass_karaoke(palabras, ruta, margen_v, tam=92, ancho_max=900):
    """Subtitulos de 1-3 palabras; la que suena en amarillo y mas grande. Siempre caben en pantalla."""
    from PIL import ImageFont
    f = ImageFont.truetype(FUENTE, tam)
    limpia = lambda w: re.sub(r"[{}\\.,;:…\"«»]", "", w).upper()
    grupos = agrupar(palabras)
    ev = []
    for gi, g in enumerate(grupos):
        fin_g = g[-1][2] + 0.25
        if gi + 1 < len(grupos):                          # sin parpadeos: aguanta hasta la siguiente frase si esta cerca
            sig = grupos[gi + 1][0][1]
            fin_g = sig if sig - g[-1][2] < 0.7 else fin_g
        texto = " ".join(limpia(w) for w, _, _ in g)
        ancho = f.getlength(texto) * 1.1
        fs = tam if ancho <= ancho_max else max(48, int(tam * ancho_max / ancho))
        for k, (w, ini, fin) in enumerate(g):
            fin_k = g[k + 1][1] if k + 1 < len(g) else fin_g
            partes = []
            for j, (w2, _, _) in enumerate(g):
                partes.append(r"{\c&H0000E6FF&\fscx115\fscy115}" + limpia(w2) + r"{\c&H00FFFFFF&\fscx100\fscy100}"
                              if j == k else limpia(w2))
            pop = r"{\fs%d\fad(70,0)}" % fs if k == 0 else r"{\fs%d}" % fs
            ev.append(f"Dialogue: 0,{tiempo_ass(ini)},{tiempo_ass(max(fin_k, ini + 0.12))},Sub,,0,0,0,,{pop}{' '.join(partes)}")
    cab = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{FAMILIA},{tam},&H00FFFFFF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,1,0,1,8,4,2,90,90,{margen_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    pathlib.Path(ruta).write_text(cab + "\n".join(ev) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- analisis del video
YUNET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yunet.onnx")


def _caras(cv2, fr):
    """Caras de un fotograma como (cx, cy, lado). YuNet (ve caras con cascos y de 3/4); si falta, Haar."""
    fh, fw = fr.shape[:2]
    if os.path.exists(YUNET):
        det = cv2.FaceDetectorYN.create(YUNET, "", (fw, fh), 0.7, 0.3, 50)
        _, res = det.detect(fr)
        return [(x + w / 2, y + h / 2, max(w, h)) for x, y, w, h in (r[:4] for r in (res if res is not None else []))
                if max(w, h) >= fh * 0.04]
    cas = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    gris = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
    return [(x + w / 2, y + h / 2, w) for (x, y, w, h) in cas.detectMultiScale(gris, 1.1, 6, minSize=(int(fh * 0.05),) * 2)]


def detectar_cam(video):
    """Busca la facecam del directo (cara pequena, fija, hacia un borde). Devuelve (x, y, w, h) a recortar o None."""
    try:
        import cv2
    except ImportError:
        return None
    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    fw, fh = cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    if not fw or fh > fw:
        return None
    caras, muestras, leidas = [], 16, 0
    for k in range(muestras):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * (k + 0.5) / muestras))
        ok, fr = cap.read()
        if not ok:
            continue
        leidas += 1
        caras += [(cx, cy, t, k) for cx, cy, t in _caras(cv2, fr)]
    cap.release()
    if not caras or not leidas:
        return None
    # Agrupa las caras que se repiten en el mismo sitio: la facecam esta en casi todos los fotogramas.
    grupos = []
    for c in caras:
        cerca = [d for d in caras if abs(d[0] - c[0]) < fw * 0.04 and abs(d[1] - c[1]) < fh * 0.05]
        fot = len({d[3] for d in cerca})
        if fot >= leidas * 0.5:
            grupos.append((cerca, fot))
    candidatos = []
    for cerca, fot in grupos:
        cx, cy = np.mean([c[0] for c in cerca]), np.mean([c[1] for c in cerca])
        tam = np.mean([c[2] for c in cerca])
        if tam > fh * 0.25:
            continue                      # cara enorme: el streamer sale a camara completa, sin partir
        bx, by = abs(cx / fw - 0.5), abs(cy / fh - 0.5)
        if bx < 0.2 and by < 0.2:
            continue                      # cara en el centro: es el video que esta viendo, no su camara
        # mas al borde, mas estable y mas grande, mejor (las caras del juego se mueven y suelen ser pequenas)
        candidatos.append((max(bx, by) + fot / leidas * 0.2 + tam / fh * 2, cx, cy, tam))
    if not candidatos:
        return None
    _, cx, cy, tam = max(candidatos)
    w = min(fw, tam * 3.6)
    h = min(fh, w * CAM_ALTO / W)
    w = h * W / CAM_ALTO
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


def recortar(src, ini, fin, salida):
    ejecutar(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{ini:.2f}", "-i", str(src), "-t", f"{fin - ini:.2f}",
              "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-c:a", "aac", "-b:a", "160k", str(salida)])
    return salida


def mejor_tramo(palabras, picos, dur, max_seg=45, ventana=40):
    """Quita silencios del principio/final y, si es largo, elige los 'ventana' segundos con mas chicha."""
    ini, fin = 0.0, dur
    if palabras:
        if palabras[0][1] > 1.2:
            ini = max(0.0, palabras[0][1] - 0.5)
        if dur - palabras[-1][2] > 2.5:
            fin = min(dur, palabras[-1][2] + 1.2)
    if fin - ini > max_seg:
        mejor, puntos = ini, -1
        t = ini
        while t + ventana <= fin + 0.01:
            p = sum(1 for _, a, _ in palabras if t <= a < t + ventana) + 6 * sum(1 for x in picos if t + 2 <= x < t + ventana - 2)
            if p > puntos:
                mejor, puntos = t, p
            t += 1.0
        ini, fin = mejor, mejor + ventana
    return ini, fin


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
def montar(src, salida, dur, titulo, gancho="", palabras=None, tmp="tmp", partir=False):
    """Hace el short final. Por defecto, el video ENTERO y tal cual (sin recortar ni mover la camara del streamer). Devuelve el modo usado ('partida' o 'centrado')."""
    tmp = pathlib.Path(tmp); tmp.mkdir(exist_ok=True)
    base = tmp / pathlib.Path(salida).stem
    cam = detectar_cam(src) if partir else None
    modo = "partida" if cam else "centrado"
    p_tit, p_gan, p_mar, ass = (f"{base}_tit.png", f"{base}_gan.png", f"{base}_mar.png", f"{base}.ass")
    if modo == "partida":
        x, y, w, h = cam
        juego_alto = H - CAM_ALTO
        # Abajo, el directo ENTERO (sin recortar) sobre un fondo difuminado del propio video.
        video = (f"[0:v]crop={w}:{h}:{x}:{y},scale={W}:{CAM_ALTO}[cam];"
                 f"[0:v]split[a][b];[a]scale={W}:{juego_alto}:force_original_aspect_ratio=increase,crop={W}:{juego_alto},"
                 f"boxblur=25:2,eq=brightness=-0.25[fondo];[b]scale={W}:-2[entero];"
                 f"[fondo][entero]overlay=0:{JUEGO_Y - CAM_ALTO}[juego];"
                 f"[cam][juego]vstack[base]")
        png_titulo(titulo, CAM_ALTO - 115, p_tit, tam=70, ancho=24, lineas_max=2)
        png_gancho(gancho or titulo, CAM_ALTO - 120, p_gan)
        margen_subs = 420                       # debajo del directo, encima de los botones de TikTok/Instagram
    else:
        video = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                 f"boxblur=25:2,eq=brightness=-0.2[bg];[0:v]scale={W}:-2[fg];"   # video entero: no se corta a nadie
                 f"[bg][fg]overlay=(W-w)/2:(H-h)/2[base]")
        png_titulo(titulo, 200, p_tit)
        png_gancho(gancho or titulo, 260, p_gan)
        margen_subs = 640          # encima de la zona de botones/descripcion de TikTok e Instagram
    png_marca(p_mar)

    # zoom rapido en los picos de volumen
    # (solo en pantalla partida: en el video entero el zoom cortaria los bordes)
    zonas = "+".join(f"between(t,{max(0, p - 0.15):.2f},{p + 0.6:.2f})" for p in picos_volumen(src)) if modo == "partida" else ""
    zoom = (f";[base]scale=w='{W}*(1+0.05*({zonas}))':h=-2:eval=frame,crop={W}:{H}[z]" if zonas
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

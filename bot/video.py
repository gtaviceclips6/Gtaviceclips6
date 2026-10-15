# Vice GTA6 Clips - montaje del video (vertical, titulo, credito, subtitulos)
import os, subprocess, textwrap
from PIL import Image, ImageDraw, ImageFont

HANDLE = "@gtaviceclips6"
FUENTES = ["fonts/Anton-Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
FUENTE = next((f for f in FUENTES if os.path.exists(f)), FUENTES[-1])
FAMILIA = "Anton" if "Anton" in FUENTE else "DejaVu Sans"


def ejecutar(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip().splitlines()[-1][:300])
    return p.stdout

def tiempo_ass(s):
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"

def subtitulos(video, ass):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return False
    try:
        modelo = WhisperModel("small", device="cpu", compute_type="int8")
        # el audio lo saca ffmpeg (asi no dependemos de PyAV, que daba error con 'metadata_errors')
        import numpy as np
        crudo = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(video), "-ac", "1", "-ar", "16000",
                                "-f", "f32le", "-"], capture_output=True).stdout
        audio = np.frombuffer(crudo, np.float32)
        if not len(audio):
            return False
        segs, _ = modelo.transcribe(audio, language="es", word_timestamps=True, vad_filter=True)
        palabras = [w for s in segs for w in (s.words or [])]
    except Exception as e:   # si falla la transcripcion, el short sale igual pero sin subtitulos
        print("Subtitulos:", e)
        return False
    if not palabras:
        return False
    lineas = []
    for i in range(0, len(palabras), 3):
        g = palabras[i:i + 3]
        txt = " ".join(w.word.strip() for w in g).upper().replace("{", "").replace("}", "")
        lineas.append(f"Dialogue: 0,{tiempo_ass(g[0].start)},{tiempo_ass(g[-1].end + 0.05)},Sub,,0,0,0,,{txt}")
    cab = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{FAMILIA},84,&H0000F0FF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,1,0,1,7,3,2,70,70,500,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ass.write_text(cab + "\n".join(lineas) + "\n", encoding="utf-8")
    return True

def capa(titulo, streamer, png):
    im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f_tit = ImageFont.truetype(FUENTE, 92)
    f_peq = ImageFont.truetype(FUENTE, 46)
    limpio = " ".join("".join(c for c in titulo if ord(c) < 0x2000).split())   # sin emojis (salen como cuadrados)
    lineas = textwrap.wrap(limpio.upper(), 18)[:3] or ["GTA 6"]
    y = 230
    for l in lineas:
        w = d.textlength(l, font=f_tit)
        d.text(((1080 - w) / 2, y), l, font=f_tit, fill=(255, 255, 255),
               stroke_width=8, stroke_fill=(255, 46, 136))
        y += 110
    cred = f"CLIP: {streamer.upper()}" if streamer else ""
    for txt, yy, col in ((cred, 1470, (0, 229, 255)), (HANDLE, 1535, (255, 255, 255))):
        if txt:
            w = d.textlength(txt, font=f_peq)
            d.text(((1080 - w) / 2, yy), txt, font=f_peq, fill=col, stroke_width=4, stroke_fill=(0, 0, 0))
    im.save(png)

def montar(src, png, ass, salida, dur):
    filtro = ("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
              "boxblur=25:2,eq=brightness=-0.18[bg];[0:v]scale=1080:-2[fg];"
              "[bg][fg]overlay=(W-w)/2:(H-h)/2+20[v1];[v1][1:v]overlay=0:0[v2]")
    if ass:
        filtro += f";[v2]subtitles={ass}:fontsdir=fonts[v]"
    else:
        filtro += ";[v2]null[v]"
    ejecutar(["ffmpeg", "-y", "-i", str(src), "-i", str(png), "-filter_complex", filtro,
              "-map", "[v]", "-map", "0:a?", "-t", f"{dur:.2f}", "-r", "30",
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-maxrate", "6M", "-bufsize", "12M",
              "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(salida)])

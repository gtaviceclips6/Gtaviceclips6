# GTA VICE CLIPS 6 - noticias de GTA 6 al momento
# Cada 2 horas mira Google Noticias (en español). La IA elige SOLO noticias oficiales e importantes
# (tráiler, fecha, anuncio de Rockstar/Take-Two...), nunca rumores ni filtraciones, y monta un video
# vertical "ÚLTIMA HORA" que te llega a Telegram con los botones ✅/❌.
import os, re, json, wave, hashlib, pathlib, datetime, subprocess, textwrap
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import tg, pipeline, ia
from video import ejecutar, FUENTE, W, H, ROSA, CIAN, AMARILLO, BLANCO, HANDLE

VISTAS = pathlib.Path("noticias_vistas.txt")
TMP = pathlib.Path("tmp_noticias"); TMP.mkdir(exist_ok=True)
HORAS = int(os.environ.get("HORAS_NOTICIA", "12") or 12)
from config import JUEGO, HASHTAGS as TAGS, CFG
from urllib.parse import quote
_I = CFG["idioma"]
RSS = (f"https://news.google.com/rss/search?q={quote(JUEGO['busqueda_noticias'] + ' when:1d')}"
       f"&hl={_I['codigo']}&gl={_I['pais']}&ceid={_I['pais']}:{_I['codigo']}")

INSTR = """Eres el editor de @gtaviceclips6 (cuenta de fans de GTA 6 para España). Te paso titulares recientes.
Elige COMO MUCHO UNO que sea una noticia OFICIAL e IMPORTANTE de GTA 6: anuncio o confirmacion de Rockstar Games
o Take-Two (trailer nuevo, fecha, retraso, precio, ediciones, plataformas, gameplay oficial, record oficial).
NO elijas: rumores, filtraciones, "segun un insider", opiniones, guias, ofertas, listas, ni noticias viejas o repetidas.
Si ninguno cumple, responde {"indice": null}. No inventes datos: usa solo lo que dice el titular.
Responde SOLO con JSON:
{"indice": numero o null, "titular": "titular corto en español (max 60 caracteres)",
 "resumen": "1-2 frases en español con lo que se sabe (solo lo del titular)",
 "comentario": "1 frase con emoción para el post", "hashtags": ["4-6 hashtags concretos"]}"""


MODO = os.environ.get("MODO_NOTICIAS", "gta")      # "gta" (noticias oficiales de GTA 6) o "virales" (tendencias de España)
TRENDS = f"https://trends.google.com/trending/rss?geo={_I['pais']}"
INSTR_VIRAL = """Eres el editor de @gtaviceclips6, cuenta de humor y gaming para jovenes de España. Te paso lo que mas se
esta buscando AHORA en España (tendencia, busquedas y titulares). Elige COMO MUCHO UNO que sea viral y divertido de contar
en un video corto: deporte (un golazo, un fichaje, un resultado historico), videojuegos, streamers, cine, series, musica,
tecnologia, internet, algo curioso o sorprendente.
PROHIBIDO elegir: muertes, accidentes, sucesos, crimenes, guerras, catastrofes, enfermedades, politica, elecciones,
religion, temas de odio, rumores sin confirmar o cosas de menores. Si ninguno cumple, responde {"indice": null}.
No inventes datos: usa solo lo que dicen los titulares.
Responde SOLO con JSON:
{"indice": numero o null, "titular": "titular corto y llamativo en español (max 60 caracteres)",
 "resumen": "1-2 frases con lo que ha pasado (solo lo de los titulares)",
 "comentario": "1 frase de colega con gracia para el post", "hashtags": ["4-6 hashtags concretos"]}"""


def leer_tendencias():
    """Lo que mas se busca ahora en España (Google Trends), con sus titulares."""
    ns = {"ht": "https://trends.google.com/trending/rss"}
    r = requests.get(TRENDS, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    out = []
    for it in ET.fromstring(r.content).iter("item"):
        tema = (it.findtext("title") or "").strip()
        trafico = it.findtext("ht:approx_traffic", namespaces=ns) or ""
        news = it.findall("ht:news_item", ns)
        if not news:
            continue
        n0 = news[0]
        titulares = " / ".join((n.findtext("ht:news_item_title", namespaces=ns) or "").strip() for n in news[:3])
        out.append(dict(titulo=f"{tema} ({trafico} búsquedas): {titulares}", tema=tema,
                        fuente=(n0.findtext("ht:news_item_source", namespaces=ns) or "").strip(),
                        link=(n0.findtext("ht:news_item_url", namespaces=ns) or "").strip(), fecha=""))
    return out


def norm(t):
    return re.sub(r"\W+", " ", (t or "").lower()).strip()


def leer_rss():
    r = requests.get(RSS, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    out = []
    ahora = datetime.datetime.now(datetime.timezone.utc)
    for it in ET.fromstring(r.content).iter("item"):
        titulo = (it.findtext("title") or "").strip()
        fuente = (it.findtext("source") or "").strip()
        try:
            fecha = parsedate_to_datetime(it.findtext("pubDate"))
        except Exception:
            continue
        if ahora - fecha > datetime.timedelta(hours=HORAS):
            continue
        titulo = re.sub(r"\s+-\s+" + re.escape(fuente) + r"$", "", titulo) if fuente else titulo
        out.append(dict(titulo=titulo, fuente=fuente, link=it.findtext("link") or "", fecha=fecha.isoformat()))
    return out


def elegir(noticias, instr=None):
    if not ia.GEMINI:
        print("Sin GEMINI_API_KEY: no elijo noticias (para no publicar rumores)."); return None
    lista = "\n".join(f"{i}. {n['titulo']} ({n['fuente']})" for i, n in enumerate(noticias))
    for modelo in ia.MODELOS_GEMINI:
        r = ia.gemini_post(modelo, {
                              "systemInstruction": {"parts": [{"text": instr or INSTR}]},
                              "contents": [{"role": "user", "parts": [{"text": lista}]}],
                              "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3}})
        if r.status_code in (400, 404) or r.status_code >= 500:   # Google saturado: siguiente modelo
            continue
        if r.status_code == 429:
            print("Gemini: cupo agotado"); return None
        r.raise_for_status()
        txt = "".join(p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"])
        d = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
        i = d.get("indice")
        if isinstance(i, int) and 0 <= i < len(noticias):
            d["noticia"] = noticias[i]
            return d
        return None
    return None


def fondo():
    px = np.zeros((H, W, 3), np.uint8)
    for y in range(H):
        t = y / H
        px[y, :] = (int(12 + 60 * t), int(0 + 6 * t), int(30 + 70 * t))
    im = Image.fromarray(px).convert("RGBA")
    d = ImageDraw.Draw(im)
    for k in range(-12, 13):
        d.line([(W // 2 + k * 40, 1300), (W // 2 + k * 380, H)], fill=ROSA + (120,), width=3)
    for i in range(1, 10):
        y = 1300 + (H - 1300) * (i / 9) ** 2
        d.line([(0, y), (W, y)], fill=CIAN + (110,), width=3)
    return im


def cartel(d, ruta, cinta="ÚLTIMA HORA"):
    f = lambda t: ImageFont.truetype(FUENTE, t)
    im = fondo()
    dr = ImageDraw.Draw(im)
    # cinta roja ULTIMA HORA
    dr.rounded_rectangle([90, 230, W - 90, 380], 40, fill=(230, 20, 40, 255))
    txt = cinta
    w = dr.textlength(txt, font=f(110)); dr.text(((W - w) / 2, 248), txt, font=f(110), fill=BLANCO)
    y = 470
    lineas = [l.upper() for l in textwrap.wrap(d.get("titular") or d["noticia"]["titulo"], 16)[:4]]
    tam = 104
    while tam > 50 and max(dr.textlength(l, font=f(tam)) for l in lineas) > W - 90:   # que quepa siempre
        tam -= 4
    for l in lineas:
        w = dr.textlength(l, font=f(tam))
        dr.text(((W - w) / 2, y), l, font=f(tam), fill=AMARILLO, stroke_width=8, stroke_fill=(0, 0, 0))
        y += int(tam * 1.18)
    y += 40
    for l in textwrap.wrap(d.get("resumen") or "", 30)[:5]:
        w = dr.textlength(l, font=f(56))
        dr.text(((W - w) / 2, y), l, font=f(56), fill=BLANCO, stroke_width=4, stroke_fill=(0, 0, 0))
        y += 72
    fuente = f"Fuente: {d['noticia']['fuente']}" if d["noticia"].get("fuente") else ""
    for t, yy, tam in ((fuente, 1660, 44), (HANDLE, 1760, 52)):
        if t:
            w = dr.textlength(t, font=f(tam)); dr.text(((W - w) / 2, yy), t, font=f(tam), fill=BLANCO, stroke_width=4, stroke_fill=(0, 0, 0))
    im.convert("RGB").save(ruta)


def musica(ruta, seg=9):
    sr = 44100
    t = np.arange(int(sr * seg)) / sr
    y = np.zeros_like(t)
    for b in np.arange(0, seg, 0.5):               # bombo
        m = (t >= b) & (t < b + 0.25); tb = t[m] - b
        y[m] += np.sin(2 * np.pi * (50 + 80 * np.exp(-tb * 30)) * tb) * np.exp(-tb * 10) * 0.6
    for k, f0 in enumerate([220, 261.6, 196, 246.9]):  # acordes de tension
        m = (t >= k * seg / 4) & (t < (k + 1) * seg / 4); tt = t[m] - k * seg / 4
        y[m] += (np.sin(2 * np.pi * f0 * tt) + 0.5 * np.sin(2 * np.pi * f0 * 1.5 * tt)) * 0.12 * np.minimum(1, tt * 8)
    y *= np.minimum(1, t / 0.2) * np.minimum(1, (seg - t) / 0.6)
    y = (y / np.abs(y).max() * 0.8 * 32767).astype(np.int16)
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(y.tobytes())


def main():
    import ajustes
    if ajustes.en_pausa():
        print("Bot en pausa (desde el menú de Telegram)"); return
    vistas = set(VISTAS.read_text(encoding="utf-8").splitlines()) if VISTAS.exists() else set()
    viral = MODO == "virales"
    if not ajustes.leer()["tendencias" if viral else "noticias_gta"] and os.environ.get("GITHUB_EVENT_NAME") == "schedule":
        print("Desactivado en ajustes"); return
    fuente = leer_tendencias() if viral else leer_rss()
    hoy = datetime.date.today().isoformat()
    clave = (lambda n: f"t:{hoy}:" + norm(n["tema"])) if viral else (lambda n: norm(n["titulo"]))
    nuevas = [n for n in fuente if clave(n) not in vistas][:30]
    print("Titulares nuevos:", len(nuevas))
    if not nuevas:
        return
    d = elegir(nuevas, INSTR_VIRAL if viral else None)
    with open(VISTAS, "a", encoding="utf-8") as f:
        f.write("\n".join(clave(n) for n in nuevas) + "\n")
    if not d:
        print("Ninguna noticia oficial importante."); return
    n = d["noticia"]
    cid = "n" + hashlib.md5(n["titulo"].encode()).hexdigest()[:9]
    png, wav, mp4 = TMP / f"{cid}.png", TMP / f"{cid}.wav", TMP / f"{cid}.mp4"
    cartel(d, png, "VIRAL HOY" if viral else "ÚLTIMA HORA"); musica(wav)
    ejecutar(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(png), "-i", str(wav),
              "-vf", f"scale=8000:-1,zoompan=z='min(zoom+0.0006,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=270:s={W}x{H}:fps=30,format=yuv420p",
              "-t", "9", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-c:a", "aac", "-shortest",
              "-movflags", "+faststart", str(mp4)])
    tags = []
    base = "#viral #ultimahora #noticias #españa #parati #fyp #humor" if viral else TAGS["noticias"]
    for x in base.split() + [
            "#" + re.sub(r"\W", "", str(x).lstrip("#")).lower() for x in (d.get("hashtags") or []) if x]:
        if len(x) > 1 and x.lower() not in [t.lower() for t in tags]:
            tags.append(x)
    texto = (f"{'🔥 VIRAL' if viral else '🚨 ÚLTIMA HORA'}: {d.get('titular') or n['titulo']}\n\n{d.get('resumen', '')}\n\n{d.get('comentario', '')}\n\n"
             f"¿Qué os parece? 👇\nSíguenos para más 👉 {HANDLE}\n\n" + " ".join(tags[:14])).strip()
    info = f"\n\n— Noticia: {n['titulo']} ({n['fuente']})\n{n['link']}"
    tg.enviar_video(mp4, (texto + info)[:1024], cid)
    pipeline.guardar(dict(url=n["link"] or cid, streamer="Noticias", vistas=0), mp4, cid,
                     d.get("titular") or n["titulo"], texto, "IA · noticia")


if __name__ == "__main__":
    try:
        main()
    except BaseException as e:
        import traceback
        pathlib.Path("errores_noticias.txt").write_text(tg.sin_claves(traceback.format_exc()), encoding="utf-8")
        raise

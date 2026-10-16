# GTA VICE CLIPS 6 - reels de escenas sacadas de un video (trailer, gameplay oficial...)
# 1) Descarga el video (enlace de YouTube u otro).
# 2) Detecta los cambios de plano y junta planos seguidos en trozos de 8-15 s.
# 3) La IA mira cada trozo y se queda con las escenas mas espectaculares.
# 4) Monta cada escena en vertical (sin pantalla partida, con el sonido original) y la manda a Telegram con ✅/❌.
import os, re, json, hashlib, pathlib, datetime, subprocess
import tg, pipeline, ia, video
from video import ejecutar

URL = os.environ.get("URL_VIDEO", "").strip()
MAX_REELS = int(os.environ.get("MAX_REELS", "5") or 5)
NOTA = float(os.environ.get("NOTA_ESCENAS", "6") or 6)
MIN_S, MAX_S = 8, 15
TMP = pathlib.Path("tmp_escenas"); TMP.mkdir(exist_ok=True)
ERR = pathlib.Path("errores_escenas.txt")
CONTEXTO = os.environ.get("CONTEXTO", "Escena del tráiler oficial de GTA 6 (no es un streamer)")


def descargar(url):
    """Prueba varias formas (YouTube a veces bloquea a los servidores de GitHub)."""
    salida = TMP / "fuente.mp4"
    intentos = [[], ["--extractor-args", "youtube:player_client=tv_simply,web_safari"],
                ["--extractor-args", "youtube:player_client=mweb,ios"],
                ["--extractor-args", "youtube:player_client=android_vr"]]
    fallos = []
    for extra in intentos:
        try:
            ejecutar(["yt-dlp", "-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/bv*[height<=1080]+ba/b", "--merge-output-format", "mp4",
                      "-o", str(salida), "--no-playlist", "--force-overwrites", *extra, url])
            if salida.exists() and salida.stat().st_size > 100_000:
                return salida
        except Exception as e:
            fallos.append(f"{' '.join(extra) or 'normal'}: {str(e)[-200:]}")
    raise RuntimeError("No pude descargar el vídeo:\n" + "\n".join(fallos))


def cortes(src):
    """Segundos donde cambia el plano."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src), "-vf", "select='gt(scene,0.32)',showinfo",
                        "-an", "-f", "null", "-"], capture_output=True, text=True)
    return sorted({float(m) for m in re.findall(r"pts_time:([\d.]+)", r.stderr)})


def trozos(src):
    total = video.duracion(src)
    marcas = [0.0] + [c for c in cortes(src)] + [total]
    ini_ok, fin_ok = 3.0, total - 6.0           # fuera logos del principio y creditos del final
    out, ini = [], None
    for a, b in zip(marcas, marcas[1:]):
        if a < ini_ok or b > fin_ok:
            continue
        if ini is None:
            ini = a
        if b - ini >= MIN_S:
            fin = min(b, ini + MAX_S)
            out.append((round(ini, 2), round(fin, 2)))
            ini = None
    if not out:                                   # sin cortes detectados: trozos fijos de 12 s
        t = ini_ok
        while t + 12 <= fin_ok:
            out.append((t, t + 12)); t += 12
    return out


def main():
    if not URL:
        raise SystemExit("Falta el enlace del vídeo (URL_VIDEO)")
    src = descargar(URL)
    lista = trozos(src)
    print("Trozos candidatos:", len(lista))
    puntuados = []
    for k, (a, b) in enumerate(lista[:24]):
        t = TMP / f"t{k}.mp4"
        try:
            video.recortar(src, a, b, t)
            j = ia.textos("", CONTEXTO, "(sin diálogo: valora solo lo que se ve)", video.fotogramas(t))
        except Exception as e:
            print("Trozo", k, e); continue
        if j:
            print(k, a, b, j.get("tipo"), j.get("nota"), j.get("motivo"))
            if j.get("tipo") in ("escena_guapa", "gracioso") and j["nota"] >= NOTA:
                puntuados.append((j["nota"], k, a, b, t, j))
    puntuados.sort(key=lambda x: -x[0])
    hechos = 0
    for nota, k, a, b, t, j in sorted(puntuados[:MAX_REELS], key=lambda x: x[2]):   # en orden del video
        item = dict(url=f"{URL}#t={a:.0f}", streamer="", titulo=j.get("titulo") or "GTA 6", vistas=0)
        titulo, gancho, texto, _ = pipeline.escribir_textos(item, "gta 6", j)
        final = TMP / f"reel{k}.mp4"
        video.montar(t, final, b - a, titulo, gancho, None, tmp=TMP, partir=False)
        cid = hashlib.md5(item["url"].encode()).hexdigest()[:10]
        hora = pipeline.mejor_hora()
        info = (f"\n\n— Escena {a:.0f}-{b:.0f} s del vídeo · {b - a:.0f} s · IA: 😍 nota {nota:g}/10"
                + (f"\n🕒 Mejor hora para publicarlo: {hora}" if hora else ""))
        tg.enviar_video(final, texto + info, cid)
        pipeline.guardar(dict(item, streamer="escena"), final, cid, titulo, texto, f"IA · escena · nota {nota:g}")
        hechos += 1
    tg.mensaje(f"🎬 Escenas del vídeo: {hechos} reel(s) listos de {len(lista)} trozos mirados." if hechos
               else f"🎬 Escenas: miré {len(lista)} trozos y ninguno llegó a nota {NOTA:g}.")


if __name__ == "__main__":
    try:
        main()
    except BaseException as e:
        import traceback
        ERR.write_text(traceback.format_exc(), encoding="utf-8")
        try:
            tg.mensaje(f"⚠️ Escenas: {str(e)[:300]}")
        except Exception:
            pass
        raise

# GTA VICE CLIPS 6 - cortador de shorts
# 1) Apunta los botones ✅/❌ que hayas pulsado en Telegram
# 2) Busca clips (clips.txt + Twitch), los monta en vertical y te los manda con botones
# 3) Por la noche te manda un resumen del dia
import os, json, pathlib, datetime
import requests
import tg, pipeline
from fuentes import leer_lista, buscar_twitch, elegir_tramo, descargar
from video import ejecutar

MAX_CLIPS = int(os.environ.get("MAX_CLIPS", "5") or 5)
HECHOS = pathlib.Path("hechos.txt")
ERRORES = pathlib.Path("errores.txt")
TMP = pathlib.Path("tmp"); TMP.mkdir(exist_ok=True)


def minutos_del_mes():
    """Minutos de GitHub Actions gastados este mes (aprox.), para el resumen."""
    repo, token = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
    if not repo or not token:
        return None
    desde = datetime.date.today().replace(day=1).isoformat()
    total, pagina = 0, 1
    while pagina < 20:
        r = requests.get(f"https://api.github.com/repos/{repo}/actions/runs", timeout=30,
                         headers={"Authorization": f"Bearer {token}"},
                         params={"created": f">={desde}", "per_page": 100, "page": pagina})
        runs = r.json().get("workflow_runs", []) if r.ok else []
        for x in runs:
            try:
                a = datetime.datetime.fromisoformat(x["run_started_at"].rstrip("Z"))
                b = datetime.datetime.fromisoformat(x["updated_at"].rstrip("Z"))
                total += max(1, -(-int((b - a).total_seconds()) // 60))
            except Exception:
                pass
        if len(runs) < 100:
            break
        pagina += 1
    return total


def resumen_diario():
    hoy = datetime.datetime.utcnow().date().isoformat()
    lista = [json.loads(l) for l in pipeline.LISTA.read_text(encoding="utf-8").splitlines()] if pipeline.LISTA.exists() else []
    de_hoy = [d for d in lista if (d.get("fecha") or "").startswith(hoy)]
    errores = [l for l in (ERRORES.read_text(encoding="utf-8").splitlines() if ERRORES.exists() else []) if l.startswith(hoy)]
    pendientes = [a for a in tg.aprobados() if not a.get("publicado")]
    mins = minutos_del_mes()
    top = sorted(de_hoy, key=lambda d: d.get("vistas", 0), reverse=True)[:3]
    txt = (f"📊 Resumen del día\n\n🎬 Shorts nuevos: {len(de_hoy)}\n⚠️ Clips descartados o con error: {len(errores)}\n"
           f"✅ Aprobados pendientes de programar: {len(pendientes)}\n")
    if mins is not None:
        txt += f"⏱️ Minutos de GitHub este mes: ~{mins} de 2.000\n"
    if top:
        txt += "\n🔥 Los más vistos de hoy:\n" + "\n".join(f"• {d['titulo']} ({d['streamer']})" for d in top)
    if pendientes:
        txt += "\n\n👉 Dile a Claude: «programa los aprobados»"
    tg.mensaje(txt)


def main():
    if not tg.TOKEN or not tg.chat_id():
        raise SystemExit("Falta el token o el chat de Telegram")
    ok, no = tg.procesar_botones()
    print(f"Botones: {ok} aprobados, {no} descartados")
    hechos = set(HECHOS.read_text(encoding="utf-8").split()) if HECHOS.exists() else set()
    items, vistos = [], set()
    lista = [] if os.environ.get("SOLO_VIRALES") == "true" else leer_lista()
    for it in lista + buscar_twitch():
        it.setdefault("vistas", 0)
        if it["url"] in hechos or it["url"] in vistos:
            continue
        if pipeline.ya_hay_igual(it["streamer"], it["titulo"]):
            hechos.add(it["url"]); continue
        vistos.add(it["url"]); items.append(it)
    automatico = os.environ.get("EVENTO") == "schedule"
    if items:
        pendientes = len(items) - MAX_CLIPS
        items = items[:MAX_CLIPS]
        aviso = f" (quedan {pendientes} para la próxima pasada)" if pendientes > 0 else ""
        tg.mensaje(f"🤖 Empiezo a cortar {len(items)} clip(s){aviso}…")
        bien = mal = 0
        for n, it in enumerate(items, 1):
            try:
                meta = json.loads(ejecutar(["yt-dlp", "-J", "--no-playlist", it["url"]]))
                it["streamer"] = it["streamer"] or meta.get("uploader") or meta.get("channel") or ""
                it["titulo"] = it["titulo"] or meta.get("title", "")
                it["vistas"] = it["vistas"] or meta.get("view_count") or 0
                ini, dur, como = elegir_tramo(meta, it["inicio"], it["dur"])
                crudo = TMP / f"c{n}.mp4"
                descargar(it, ini, dur, crudo)
                pipeline.procesar(it, crudo, n, info_extra=f" · {como}", tmp=TMP)
                bien += 1
            except Exception as e:
                mal += 1
                with open(ERRORES, "a", encoding="utf-8") as f:
                    f.write(tg.sin_claves(f"{datetime.datetime.utcnow().isoformat(timespec='minutes')} {it['url']} {e}") + "\n")
                if not str(e).startswith("descartado"):
                    tg.mensaje(f"❌ No pude con:\n{it['url']}\nMotivo: {e}")
            hechos.add(it["url"])
            HECHOS.write_text("\n".join(sorted(hechos)) + "\n", encoding="utf-8")
        tg.mensaje(f"✅ Terminado: {bien} short(s) listos, {mal} descartados o con error.")
    elif not automatico:
        tg.mensaje("🤖 No hay clips nuevos que cortar.")
    if automatico and datetime.datetime.utcnow().hour == 21:   # pasada de las 23:17 (hora de Madrid)
        resumen_diario()


if __name__ == "__main__":
    main()

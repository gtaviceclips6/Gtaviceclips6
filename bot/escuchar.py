# GTA VICE CLIPS 6 - el bot de Telegram ESCUCHANDO SIEMPRE (responde al momento)
# Se queda conectado a Telegram ~5 h 40 min; al terminar, GitHub lanza otro igual (cada 30 min hay uno en cola).
# Cada boton o mensaje se atiende en 1-2 segundos y los cambios se guardan en el repo enseguida.
import os, time, json, subprocess
import tg, comandos

DURACION = int(os.environ.get("DURACION_MIN", "340")) * 60
VIGILADOS = ["aprobados.jsonl", "descartados.txt", "ajustes.json", "telegram_chat.txt", "menu_enviado.txt", "lanzados.json"]


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def guardar():
    for f in VIGILADOS:
        git("add", f)
    if git("diff", "--cached", "--quiet").returncode == 0:
        return
    git("commit", "-q", "-m", "Telegram")
    for _ in range(5):
        if git("pull", "--rebase", "-X", "theirs", "-q").returncode == 0 and git("push", "-q").returncode == 0:
            return
        git("rebase", "--abort"); time.sleep(3)


def refrescar():
    """Trae lo ultimo del repo (shorts nuevos, estado de la IA...) para que /estado sea exacto."""
    if git("pull", "--rebase", "-X", "theirs", "-q").returncode != 0:
        git("rebase", "--abort")


def main():
    fin = time.time() + DURACION
    offset, ultimo_pull = None, 0
    tg.tg("setMyCommands", data={"commands": json.dumps(comandos.COMANDOS)})
    print("Escuchando Telegram…")
    while time.time() < fin - 60:
        datos = {"timeout": 50, "allowed_updates": json.dumps(["message", "callback_query"])}
        if offset:
            datos["offset"] = offset
        try:
            upd = tg.tg("getUpdates", data=datos).json().get("result", [])
        except Exception as e:
            print("Telegram:", e); time.sleep(5); continue
        if upd:
            offset = upd[-1]["update_id"] + 1
            if time.time() - ultimo_pull > 60:
                refrescar(); ultimo_pull = time.time()
            tg.MENSAJES.clear()
            tg.procesar_botones(upd)
            for texto in list(tg.MENSAJES):
                try:
                    comandos.atender(texto)
                except Exception as e:
                    tg.mensaje(f"⚠️ No pude con eso: {tg.sin_claves(e)[:200]}")
            guardar()
        elif time.time() - ultimo_pull > 600:
            refrescar(); ultimo_pull = time.time()
    if offset:   # deja la cola marcada como leida para el siguiente
        tg.tg("getUpdates", data={"offset": offset, "timeout": 0})
    print("Fin del turno; el siguiente coge el relevo.")


if __name__ == "__main__":
    main()

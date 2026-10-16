# 🌴 Vice Clips Bot

**Una fábrica automática de shorts virales para cuentas de fans de videojuegos.**
Busca los mejores momentos de los streamers en Twitch, una IA decide cuáles merecen la pena, los monta en vertical con subtítulos karaoke y te los manda a Telegram listos para publicar. Tú solo pulsas ✅.

Funciona entero en GitHub Actions, **sin servidor y sin coste** (IA de Google con cupo gratuito, repositorio público = minutos ilimitados).

> Cuenta de ejemplo en producción: **@gtaviceclips6** (TikTok · Instagram Reels · YouTube Shorts), cuenta de fans de GTA 6 para España.

---

## ✨ Qué hace

| | Función | Detalle |
|---|---|---|
| 🔎 | **Busca clips** | Cada 3 h: los clips más vistos de tu lista de streamers + los clips en español más vistos del juego en **todo Twitch** (API oficial Helix). |
| 🧠 | **Juez con IA** | Gemini mira 4 fotogramas y la transcripción y clasifica: *gracioso*, *escena guapa* o *nada*. Pone nota de 1 a 10; solo pasan los de nota ≥ 7. Fuera los cortes aburridos. |
| ✂️ | **Recorte inteligente** | Quita silencios al principio y al final; si el clip es largo, se queda con los mejores 40 s (más voz y más picos de volumen). |
| 🎬 | **Montaje vertical 1080×1920** | Si el streamer tiene facecam a un lado: cámara arriba y juego abajo. Si no: vídeo centrado con zoom y fondo difuminado. |
| 💬 | **Subtítulos karaoke** | Whisper *medium* con vocabulario del juego. Bloques cortos (máx. 3 palabras) que siempre caben, palabra actual en amarillo y fuera de la zona de botones de TikTok. |
| 🔥 | **Retención** | Gancho grande los 2,6 primeros segundos, zoom en los gritos, barra de progreso y marca de agua de la cuenta. |
| ✍️ | **Textos virales** | Título, gancho, comentario gracioso, pregunta para comentarios y hashtags concretos de cada clip. Sin bromas sobre orientación, raza, etc. (las redes las castigan). |
| 📲 | **Aprobación en Telegram** | Cada short llega con botones ✅ Publicar / ❌ Descartar y la **mejor hora para publicarlo** (según datos de audiencia). |
| 🔴 | **Vigilante de directos** | Graba los directos del juego, escucha el chat y corta el momento exacto en que el chat explota (risas, KEKW, WTF…). El clip llega minutos después de que pase. |
| 🚨 | **Noticias al momento** | Cada 2 h lee Google Noticias; la IA solo elige noticias **oficiales** (nunca rumores) y monta un vídeo «ÚLTIMA HORA». |
| ⚡ | **Virales al momento** | Cada hora: clips en español que más rápido suben (visitas/hora) de todo Twitch y tendencias de Google del país → vídeo «VIRAL HOY». |
| 📎 | **Mándale un enlace** | Escribe al bot un enlace (X, Twitch, Kick, TikTok…) y te devuelve el reel montado; si es largo, las mejores escenas. Comandos `/estado`, `/virales`, `/ayuda`. |
| 🚀 | **Publicación automática** | Lo que apruebas con ✅ se publica a la vez en TikTok, Reels y Shorts (vía Metricool) en menos de una hora. |
| 🏆 | **TOP 5 semanal** | Domingos: recopilación «TOP 5 momentos de la semana» con los aprobados. |
| 📊 | **Resumen diario** | Cada noche: shorts hechos, descartados, pendientes y minutos gastados. |
| 🌙 | **No molesta** | De 0:00 a 9:00 los avisos llegan en silencio. Si no hay nada bueno, no manda nada. |
| 🧪 | **Simulacro** | Prueba todo con otro juego (p. ej. GTA V) antes del lanzamiento; los clips de prueba se marcan y se descartan solos. |

---

## 🧩 Válido para cualquier juego o cuenta

Todo lo de la marca está en **`config.json`**: nombre y @ de la cuenta, colores, juego de Twitch, fecha de lanzamiento, palabras clave, vocabulario para los subtítulos, idioma y país, hashtags, filtro de calidad y horas de publicación. Cambiando ese archivo, el bot sirve para otra cuenta (otro juego, otro idioma) sin tocar el código.

## 🚀 Puesta en marcha (15 minutos)

1. Haz un *fork* o copia de este repositorio (público, para tener minutos ilimitados).
2. En **Settings → Secrets and variables → Actions** añade:
   - `TELEGRAM_BOT_TOKEN` — crea un bot con @BotFather y escríbele un mensaje.
   - `GEMINI_API_KEY` — gratis en aistudio.google.com.
   - `TWITCH_CLIENT_ID` y `TWITCH_CLIENT_SECRET` — app gratis en dev.twitch.tv.
3. Edita `config.json` (tu marca y tu juego) y `streamers.txt` (un canal por línea).
4. Ve a **Actions → Cortar shorts → Run workflow**. En unos minutos te llegan los primeros shorts a Telegram.

Opcional: en `clips.txt` puedes poner enlaces concretos (`url | streamer | título | inicio | duración`); esos no pasan el filtro de la IA.

## ⚙️ Automatizaciones

| Workflow | Cuándo | Qué |
|---|---|---|
| Cortar shorts | cada 3 h | busca, juzga, monta y manda clips |
| Noticias | cada 2 h | vídeo «ÚLTIMA HORA» si hay noticia oficial |
| Vigilar directos | cada hora en la ventana de lanzamiento | corta momentos en directo |
| Recopilación semanal | domingos | TOP 5 de la semana |

Todos comparten una cola, así que nunca se pisan.

## 🗂️ Código

```
config.json            marca, juego, hashtags, filtro, horarios
bot/fuentes.py         de dónde salen los clips (Twitch, clips.txt)
bot/ia.py              juez y textos con IA (Gemini gratis; Claude opcional)
bot/video.py           subtítulos, detección de facecam, recorte y montaje
bot/pipeline.py        clip → short → Telegram
bot/tg.py              Telegram, botones y modo silencio
bot/cortar.py          pasada programada + resumen diario
bot/directo.py         vigilante de directos (chat de Twitch)
bot/noticias.py        noticias oficiales
bot/recopilacion.py    TOP 5 semanal
```

## 🛡️ Buenas prácticas

- Las claves van **solo** en los *Secrets* de GitHub; nunca en el código.
- Respeta las normas de cada plataforma y de los creadores: lo ideal es tener permiso de los streamers o usar sus programas de clips.
- Cuenta de fans: no uses logotipos oficiales del juego.

---

Hecho con ❤️ para **@gtaviceclips6**.

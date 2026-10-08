"""
Funcionalidades originales del código base de la cátedra, separadas en funciones.
(hora, fecha, Wikipedia, búsquedas, YouTube, chistes y acciones)
"""
import datetime
import webbrowser

import config
from voz import hablar

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# Gancho de la interfaz gráfica: función(titulo, items) que muestra resultados en pantalla.
# Cada item es un dict con "titulo", "url", "texto" y "meta". En consola queda en None
# y las búsquedas siguen abriendo el navegador.
mostrar_resultados = None


def _recortar(texto, largo=240):
    texto = " ".join((texto or "").split())
    return texto if len(texto) <= largo else texto[:largo].rsplit(" ", 1)[0] + "…"


def saludo_inicial():
    hora = datetime.datetime.now().hour
    if hora < 6 or hora >= 20:
        momento = "Buenas noches"
    elif hora < 13:
        momento = "Buen día"
    else:
        momento = "Buenas tardes"
    hablar(f"{momento}{' ' + config.NOMBRE_USUARIO if config.NOMBRE_USUARIO else ''}, soy {config.NOMBRE_ASISTENTE}, "
           f"tu asistente de marketing. ¿En qué te puedo ayudar?")


def pedir_dia():
    hoy = datetime.date.today()
    hablar(f"Hoy es {DIAS_SEMANA[hoy.weekday()]} {hoy.day} de {MESES[hoy.month - 1]}")


def pedir_hora():
    hora = datetime.datetime.now()
    hablar(f"En este momento son las {hora.hour} horas con {hora.minute} minutos")


def abrir_sitio(nombre, url):
    hablar(f"Estoy abriendo {nombre}")
    webbrowser.open(url)


def buscar_wikipedia(tema):
    import wikipedia
    tema = tema.strip()
    if not tema:
        hablar("¿Qué querés que busque en Wikipedia?")
        return
    hablar(f"Buscando {tema} en Wikipedia")
    wikipedia.set_lang("es")
    try:
        if mostrar_resultados:
            resultado = wikipedia.summary(tema, sentences=3)
            try:
                pagina = wikipedia.page(tema)
                titulo, url = pagina.title, pagina.url
            except Exception:
                titulo, url = tema.capitalize(), None
            mostrar_resultados(f"Wikipedia: {tema}", [
                {"titulo": titulo, "url": url, "texto": resultado, "meta": "es.wikipedia.org"}])
            return hablar("Encontré esta información en Wikipedia, la ves en pantalla")
        resultado = wikipedia.summary(tema, sentences=2)
        hablar("Encontré esta información en Wikipedia")
        hablar(resultado)
    except wikipedia.exceptions.DisambiguationError as e:
        hablar(f"Hay varios resultados. ¿Te referís a {', '.join(e.options[:3])}?")
    except wikipedia.exceptions.PageError:
        hablar(f"No encontré nada sobre {tema} en Wikipedia")
    except Exception:
        hablar("No pude conectarme con Wikipedia")


def _videos_youtube(consulta, cantidad=6):
    """Lee los resultados de la página de búsqueda de YouTube (no requiere clave de API)."""
    import json
    import re
    import requests

    r = requests.get("https://www.youtube.com/results", params={"search_query": consulta}, timeout=15,
                     headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                            "(KHTML, like Gecko) Chrome/124 Safari/537.36",
                              "Accept-Language": "es-AR,es;q=0.9"},
                     cookies={"CONSENT": "YES+1", "SOCS": "CAI"})
    datos = json.loads(re.search(r"var ytInitialData = (\{.*?\});</script>", r.text, re.S).group(1))

    def renderers(nodo):
        if isinstance(nodo, dict):
            if "videoRenderer" in nodo:
                yield nodo["videoRenderer"]
            for v in nodo.values():
                yield from renderers(v)
        elif isinstance(nodo, list):
            for v in nodo:
                yield from renderers(v)

    items = []
    for v in renderers(datos):
        canal = (v.get("ownerText", {}).get("runs") or [{}])[0].get("text")
        duracion = v.get("lengthText", {}).get("simpleText") or "En vivo"
        vistas = v.get("viewCountText", {}).get("simpleText")
        items.append({"titulo": v["title"]["runs"][0]["text"],
                      "url": f"https://www.youtube.com/watch?v={v['videoId']}",
                      "texto": "",
                      "meta": " · ".join(x for x in (canal, duracion, vistas) if x)})
        if len(items) == cantidad:
            break
    return items


def _buscar_en_pantalla(consulta, videos=False):
    """Busca y muestra los resultados en la interfaz. Devuelve False si no se pudo."""
    try:
        if videos:
            try:
                items = _videos_youtube(consulta)
            except Exception as e:
                print(f"YouTube: {e}")
                items = []
            if not items:   # segunda opción: el buscador de videos de DuckDuckGo
                from ddgs import DDGS
                items = [{"titulo": r.get("title", ""), "url": r.get("content", ""),
                          "texto": _recortar(r.get("description"), 160),
                          "meta": " · ".join(x for x in (r.get("uploader") or r.get("publisher"),
                                                         r.get("duration")) if x)}
                         for r in DDGS().videos(consulta, max_results=6)]
            titulo = f"Videos de «{consulta}»"
        else:
            from ddgs import DDGS
            crudos = DDGS().text(consulta, region="ar-es", max_results=6)
            items = [{"titulo": r.get("title", ""), "url": r.get("href", ""),
                      "texto": _recortar(r.get("body")),
                      "meta": (r.get("href", "").split("/")[2] if "//" in r.get("href", "") else "")}
                     for r in crudos]
            titulo = f"Resultados de «{consulta}»"
    except Exception as e:
        print(e)
        return False
    if not items:
        return False
    mostrar_resultados(titulo, items)
    hablar(f"Encontré {len(items)} {'videos' if videos else 'resultados'}, los ves en pantalla")
    return True


def buscar_internet(consulta):
    consulta = consulta.strip()
    if not consulta:
        return hablar("¿Qué querés que busque?")
    hablar("Buscando información")
    if mostrar_resultados:
        if _buscar_en_pantalla(consulta):
            return
        hablar("No pude traer los resultados, te abro el navegador")
    import pywhatkit  # import diferido: pywhatkit verifica internet al importarse
    pywhatkit.search(consulta)


def reproducir_youtube(cancion):
    cancion = cancion.strip()
    if mostrar_resultados:
        hablar(f"Buscando {cancion} en YouTube")
        if _buscar_en_pantalla(cancion, videos=True):
            return
        hablar("No pude traer los videos, te abro YouTube")
    else:
        hablar(f"Reproduciendo {cancion}")
    import pywhatkit
    pywhatkit.playonyt(cancion)


def contar_chiste():
    import pyjokes
    hablar(pyjokes.get_joke("es"))


def precio_accion(nombre):
    import yfinance as yf
    cartera = {"apple": "AAPL", "amazon": "AMZN", "google": "GOOGL", "tesla": "TSLA",
               "meta": "META", "facebook": "META", "shopify": "SHOP", "mercadolibre": "MELI",
               "mercado libre": "MELI"}
    nombre = nombre.strip()
    ticker_id = cartera.get(nombre)
    if not ticker_id:
        hablar(f"No tengo información sobre la acción de {nombre}")
        return
    try:
        precio = yf.Ticker(ticker_id).fast_info["last_price"]
        hablar(f"El precio de {nombre} es {precio:.2f} dólares")
    except Exception as e:
        print(e)
        hablar("Perdón, no pude obtener la información de la acción")

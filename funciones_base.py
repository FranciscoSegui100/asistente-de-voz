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


def saludo_inicial():
    hora = datetime.datetime.now().hour
    if hora < 6 or hora >= 20:
        momento = "Buenas noches"
    elif hora < 13:
        momento = "Buen día"
    else:
        momento = "Buenas tardes"
    hablar(f"{momento} {config.NOMBRE_USUARIO}, soy {config.NOMBRE_ASISTENTE}, "
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
        resultado = wikipedia.summary(tema, sentences=2)
        hablar("Encontré esta información en Wikipedia")
        hablar(resultado)
    except wikipedia.exceptions.DisambiguationError as e:
        hablar(f"Hay varios resultados. ¿Te referís a {', '.join(e.options[:3])}?")
    except wikipedia.exceptions.PageError:
        hablar(f"No encontré nada sobre {tema} en Wikipedia")
    except Exception:
        hablar("No pude conectarme con Wikipedia")


def buscar_internet(consulta):
    import pywhatkit  # import diferido: pywhatkit verifica internet al importarse
    hablar("Buscando información")
    pywhatkit.search(consulta.strip())


def reproducir_youtube(cancion):
    import pywhatkit
    cancion = cancion.strip()
    hablar(f"Reproduciendo {cancion}")
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

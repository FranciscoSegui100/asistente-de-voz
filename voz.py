"""
Módulo de voz: conversión texto a voz (pyttsx3) y voz a texto (speech_recognition).
Mantiene los nombres de funciones del código base: hablar() y transformar_audio_texto().
"""
import re
import threading
import unicodedata

import config

# Lock para que el hilo de recordatorios y el principal no hablen a la vez
_lock_voz = threading.Lock()
_id_voz_cache = None

# Ganchos de la interfaz gráfica (interfaz.py los define; en consola quedan en None)
salida_gui = None     # función(texto): muestra en pantalla lo que dice el asistente
entrada_gui = None    # función() -> str: espera lo que escribe o dice el usuario


def normalizar(texto):
    """Pasa a minúsculas y quita tildes para comparar comandos ('Qué' == 'que')."""
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn").strip()


def _elegir_voz(engine):
    """Usa la voz del código base si existe; si no, busca cualquier voz en español."""
    global _id_voz_cache
    if _id_voz_cache:
        return _id_voz_cache
    voces = engine.getProperty("voices")
    ids = [v.id for v in voces]
    if config.ID_VOZ_ESPANOL in ids:
        _id_voz_cache = config.ID_VOZ_ESPANOL
    else:
        for v in voces:
            datos = f"{v.id} {v.name} {getattr(v, 'languages', '')}".lower()
            if "spanish" in datos or "espa" in datos or "es-" in datos or "es_" in datos:
                _id_voz_cache = v.id
                break
    return _id_voz_cache


def hablar(mensaje):
    """Pronuncia el mensaje en voz alta (y lo muestra por consola)."""
    if salida_gui:
        salida_gui(mensaje)
    else:
        print(f"🔊 {config.NOMBRE_ASISTENTE}: {mensaje}")
    if not config.VOZ_ACTIVA:
        return
    with _lock_voz:
        try:
            import pyttsx3
            # Se inicializa en cada llamada (como el código base): evita que pyttsx3
            # se quede mudo después del primer runAndWait() en Windows.
            engine = pyttsx3.init()
            id_voz = _elegir_voz(engine)
            if id_voz:
                engine.setProperty("voice", id_voz)
            engine.setProperty("rate", config.VELOCIDAD_VOZ)
            engine.setProperty("volume", config.VOLUMEN_VOZ)
            engine.say(mensaje)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            # Sin motor de voz disponible: el mensaje igual queda impreso
            print(f"   (sin audio: {e})")


def transformar_audio_texto():
    """Devuelve lo que pide el usuario: por interfaz gráfica, teclado (modo texto) o micrófono."""
    if entrada_gui:
        return entrada_gui()
    if config.MODO_TEXTO:
        try:
            return input("⌨️  Vos: ")
        except EOFError:
            return "adios"
    return escuchar_microfono()


def escuchar_microfono(timeout=None, limite=None):
    """Escucha el micrófono y devuelve lo dicho como texto ('sigo esperando' si no se entendió).
    timeout: segundos máximos esperando que empiece a hablar; limite: duración máxima de la frase."""
    import speech_recognition as sr
    r = sr.Recognizer()
    with sr.Microphone() as origen:
        r.pause_threshold = 0.8
        r.adjust_for_ambient_noise(origen, duration=0.5)
        print("🎙️  Ya podés hablar...")
        try:
            audio = r.listen(origen, timeout=timeout, phrase_time_limit=limite)
        except sr.WaitTimeoutError:
            print("Ups, no escuché nada")
            return "sigo esperando"
        try:
            pedido = r.recognize_google(audio, language=config.IDIOMA_RECONOCIMIENTO)
            print(f"🗣️  Dijiste: {pedido}")
            return pedido
        except sr.UnknownValueError:
            print("Ups, no entendí")
            return "sigo esperando"
        except sr.RequestError:
            print("Ups, no hay servicio")
            return "sigo esperando"
        except Exception:
            print("Ups, algo ha salido mal")
            return "sigo esperando"


def preguntar(pregunta, crudo=False):
    """Hace una pregunta en voz alta y devuelve la respuesta.
    crudo=True conserva mayúsculas y tildes (para textos de piezas o temas)."""
    hablar(pregunta)
    respuesta = transformar_audio_texto().strip()
    if normalizar(respuesta) == "sigo esperando":
        return ""
    return respuesta if crudo else normalizar(respuesta)


def es_afirmativo(respuesta):
    return any(p in re.findall(r"\w+", normalizar(respuesta)) for p in ("si", "dale", "ok", "okay", "claro", "confirmo", "obvio"))

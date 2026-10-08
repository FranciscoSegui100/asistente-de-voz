"""
Configuración central del asistente de marketing digital.
Modificar acá los datos del usuario, la marca y las credenciales.
"""
import os

# ---------------- Usuario / asistente ----------------
NOMBRE_ASISTENTE = "Nova"

# Modo texto: escribir comandos por teclado en vez de hablar
# (útil para probar sin micrófono). Se activa con:  python main.py --texto
MODO_TEXTO = os.getenv("MODO_TEXTO", "0") == "1"

# ---------------- Voz ----------------
VOZ_ACTIVA = True            # False: el asistente solo escribe, sin hablar (la interfaz lo cambia con un botón)
IDIOMA_RECONOCIMIENTO = "es-AR"
VELOCIDAD_VOZ = 350          # palabras por minuto aprox.
VOLUMEN_VOZ = 1.0            # 0.0 a 1.0
# Voz del código base (Windows). Si no existe, se busca automáticamente una voz en español.
ID_VOZ_ESPANOL = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_ES-ES_HELENA_11.0"

# ---------------- Rutas ----------------
CARPETA_BASE = os.path.dirname(os.path.abspath(__file__))
RUTA_DB = os.path.join(CARPETA_BASE, "datos", "calendario.db")
CARPETA_PIEZAS = os.path.join(CARPETA_BASE, "piezas")

# ---------------- Identidad de marca (diseño) ----------------
NOMBRE_MARCA = "@mimarca"
PALETAS = {
    "oscuro":   {"fondo": (18, 18, 18),    "texto": (255, 255, 255), "acento": (255, 107, 53)},
    "claro":    {"fondo": (245, 241, 234), "texto": (25, 25, 25),    "acento": (214, 64, 69)},
    "vibrante": {"fondo": (76, 44, 214),   "texto": (255, 255, 255), "acento": (255, 214, 10)},
}
PALETA_POR_DEFECTO = "oscuro"

# ---------------- Meta Graph API (Instagram / Facebook) ----------------
# Si no hay token, el módulo de comunidad funciona en MODO DEMO con datos simulados.
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
IG_USER_ID = os.getenv("IG_USER_ID", "")
GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v21.0")
# Instagram solo publica imágenes desde una URL pública: carpeta donde se suben las piezas
URL_PUBLICA_PIEZAS = os.getenv("URL_PUBLICA_PIEZAS", "")

MODO_DEMO_REDES = not (META_ACCESS_TOKEN and IG_USER_ID)

# ---------------- Recordatorios ----------------
MINUTOS_AVISO_PREVIO = 15    # avisar X minutos antes de cada publicación

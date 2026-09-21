"""
Interfaz gráfica del asistente de marketing (tkinter).

Uso:
    python interfaz.py

Cuatro secciones:
    Asistente  -> chat con el mismo motor de pedidos de main.py (escribiendo o por micrófono)
    Calendario -> agendar y administrar publicaciones
    Diseño     -> crear placas y carruseles con vista previa
    Comunidad  -> leer, clasificar y responder comentarios

La lógica sigue en los módulos originales; acá solo se dibuja y se conectan los ganchos de voz.py.
"""
import datetime
import glob
import os
import queue
import re
import threading
import time
import tkinter as tk
import traceback
import webbrowser
from tkinter import messagebox, simpledialog, ttk

from PIL import Image, ImageTk

import calendario
import comunidad
import config
import diseno
import funciones_base as base
import main as nucleo
import voz

# ---------------- Estilo ----------------
def _hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


FUENTE = "Segoe UI"
BG = "#121212"
PANEL = "#1c1c1e"
PANEL2 = "#2a2a2e"
BORDE = "#3a3a40"
TEXTO = "#f5f5f5"
SUAVE = "#9a9aa2"
ACENTO = _hex(config.PALETAS["oscuro"]["acento"])
ACENTO_H = "#ff8558"
ACENTO_OSC = "#5c2a14"
OK = "#3ecf8e"
ERR = "#ff6b6b"


def boton(master, texto, comando, primario=False, **kw):
    bg = ACENTO if primario else PANEL2
    fg = "#1b1b1b" if primario else TEXTO
    hover = ACENTO_H if primario else "#3a3a40"
    b = tk.Button(master, text=texto, command=comando, bg=bg, fg=fg, activebackground=hover,
                  activeforeground=fg, disabledforeground=SUAVE, relief="flat", bd=0, padx=16, pady=8,
                  cursor="hand2", font=(FUENTE, 10, "bold" if primario else "normal"), **kw)
    b.bind("<Enter>", lambda e: b.config(bg=hover) if str(b["state"]) != "disabled" else None)
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b


def _borde_foco(w):
    w.config(highlightthickness=1, highlightbackground=BORDE, highlightcolor=ACENTO, relief="flat", bd=0)


def entrada(master, **kw):
    e = tk.Entry(master, bg=PANEL2, fg=TEXTO, insertbackground=TEXTO, font=(FUENTE, 11),
                 disabledbackground=PANEL, **kw)
    _borde_foco(e)
    return e


def caja_texto(master, alto, **kw):
    t = tk.Text(master, height=alto, bg=PANEL2, fg=TEXTO, insertbackground=TEXTO, font=(FUENTE, 11),
                wrap="word", padx=8, pady=6, **kw)
    _borde_foco(t)
    return t


def etiqueta(master, texto, suave=True, **kw):
    return tk.Label(master, text=texto, bg=kw.pop("bg", BG), fg=SUAVE if suave else TEXTO,
                    font=kw.pop("font", (FUENTE, 10)), anchor="w", **kw)


def aplicar_estilos(root):
    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXTO, rowheight=34,
                borderwidth=0, bordercolor=PANEL, lightcolor=PANEL, darkcolor=PANEL, font=(FUENTE, 10))
    s.configure("Treeview.Heading", background=PANEL2, foreground=SUAVE, relief="flat",
                font=(FUENTE, 9, "bold"), padding=(8, 8))
    s.map("Treeview", background=[("selected", ACENTO_OSC)], foreground=[("selected", TEXTO)])
    s.map("Treeview.Heading", background=[("active", PANEL2)])
    s.configure("TCombobox", fieldbackground=PANEL2, background=PANEL2, foreground=TEXTO, arrowcolor=TEXTO,
                bordercolor=BORDE, lightcolor=PANEL2, darkcolor=PANEL2, padding=6)
    s.map("TCombobox", fieldbackground=[("readonly", PANEL2)], foreground=[("readonly", TEXTO)],
          selectbackground=[("readonly", PANEL2)], selectforeground=[("readonly", TEXTO)],
          bordercolor=[("focus", ACENTO)])
    s.configure("Vertical.TScrollbar", background=PANEL2, troughcolor=BG, arrowcolor=SUAVE,
                bordercolor=BG, lightcolor=PANEL2, darkcolor=PANEL2)
    s.map("Vertical.TScrollbar", background=[("active", BORDE)])
    root.option_add("*TCombobox*Listbox.background", PANEL2)
    root.option_add("*TCombobox*Listbox.foreground", TEXTO)
    root.option_add("*TCombobox*Listbox.selectBackground", ACENTO_OSC)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXTO)
    root.option_add("*TCombobox*Listbox.font", (FUENTE, 10))


def en_hilo(tarea):
    threading.Thread(target=tarea, daemon=True).start()


# ---------------- Base de las vistas ----------------
class Vista(tk.Frame):
    titulo = ""
    subtitulo = ""

    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        cab = tk.Frame(self, bg=BG)
        cab.pack(fill="x", padx=28, pady=(24, 10))
        tk.Label(cab, text=self.titulo, font=(FUENTE, 20, "bold"), bg=BG, fg=TEXTO, anchor="w").pack(anchor="w")
        etiqueta(cab, self.subtitulo).pack(anchor="w")
        self.aviso = tk.Label(self, text="", bg=BG, fg=OK, font=(FUENTE, 10), anchor="w")
        self.aviso.pack(side="bottom", fill="x", padx=28, pady=(4, 12))
        self.cuerpo = tk.Frame(self, bg=BG)
        self.cuerpo.pack(fill="both", expand=True, padx=28)
        self.construir(self.cuerpo)

    def construir(self, cuerpo):
        raise NotImplementedError

    def msg(self, texto, error=False):
        self.aviso.config(text=texto, fg=ERR if error else OK)

    def al_mostrar(self):
        pass


# ---------------- Asistente (chat) ----------------
class VistaChat(Vista):
    titulo = "Asistente"
    subtitulo = "Escribí o hablá: agendá publicaciones, creá piezas y gestioná tus comentarios."
    ATAJOS = [("¿Qué hora es?", "qué hora es"), ("Publicaciones de hoy", "qué tengo para publicar hoy"),
              ("Leer comentarios", "leé los comentarios"), ("Resumen de comentarios", "resumen de comentarios"),
              ("Contame un chiste", "contame un chiste"), ("Ayuda", "ayuda")]

    def construir(self, cuerpo):
        self._fotos = []
        self._burbujas = []
        self._ultimo = None
        self._wrap = 520

        atajos = tk.Frame(cuerpo, bg=BG)
        atajos.pack(fill="x", pady=(0, 8))
        for texto, pedido in self.ATAJOS:
            b = boton(atajos, texto, lambda p=pedido: self._enviar_texto(p))
            b.config(padx=12, pady=5, font=(FUENTE, 9))
            b.pack(side="left", padx=(0, 6))

        marco = tk.Frame(cuerpo, bg=PANEL)
        marco.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(marco, bg=PANEL, highlightthickness=0)
        barra = ttk.Scrollbar(marco, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.interior = tk.Frame(self.canvas, bg=PANEL)
        self._ventana = self.canvas.create_window((0, 0), window=self.interior, anchor="nw")
        self.canvas.bind("<Configure>", self._ajustar)
        self.interior.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._rueda(self.canvas)
        self._rueda(self.interior)

        self.estado = tk.Label(cuerpo, text="", bg=BG, fg=ACENTO, font=(FUENTE, 9, "italic"), anchor="w")
        self.estado.pack(fill="x", pady=(6, 0))
        fila = tk.Frame(cuerpo, bg=BG)
        fila.pack(fill="x", pady=(2, 8))
        self.entrada = entrada(fila)
        self.entrada.pack(side="left", fill="x", expand=True, ipady=9)
        self.entrada.bind("<Return>", lambda e: self._enviar_texto())
        self.b_mic = boton(fila, "🎙  Hablar", self.app.escuchar)
        self.b_mic.pack(side="left", padx=(8, 0))
        boton(fila, "Enviar", self._enviar_texto, primario=True).pack(side="left", padx=(8, 0))

    # -- desplazamiento y ajuste al ancho --
    def _rueda(self, widget):
        widget.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))

    def _ajustar(self, evento):
        self.canvas.itemconfigure(self._ventana, width=evento.width)
        self._wrap = max(240, int(evento.width * 0.66))
        for lab in self._burbujas:
            lab.configure(wraplength=self._wrap)

    def _al_final(self):
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    # -- mensajes --
    def _nueva_burbuja(self, quien):
        """Crea la fila y la burbuja de un mensaje ('user' a la derecha, 'bot' a la izquierda)."""
        es_usuario = quien == "user"
        fila = tk.Frame(self.interior, bg=PANEL)
        fila.pack(fill="x", padx=16, pady=(2, 0))
        if quien != self._ultimo and not es_usuario:
            etiqueta(fila, config.NOMBRE_ASISTENTE, bg=PANEL, font=(FUENTE, 9, "bold")).pack(anchor="w", pady=(10, 2))
        elif quien != self._ultimo:
            tk.Frame(fila, bg=PANEL, height=10).pack()
        self._ultimo = quien
        color = ACENTO if es_usuario else PANEL2
        burbuja = tk.Frame(fila, bg=color)
        burbuja.pack(anchor="e" if es_usuario else "w")
        self._rueda(fila)
        self._rueda(burbuja)
        return burbuja, color

    def agregar_resultados(self, titulo, items):
        """Muestra resultados de una búsqueda como una tarjeta con enlaces clicables."""
        burbuja, color = self._nueva_burbuja("bot")
        tarjeta = tk.Frame(burbuja, bg=color)
        tarjeta.pack(padx=14, pady=10)

        def texto(fuente, fg, contenido, **kw):
            lab = tk.Label(tarjeta, text=contenido, bg=color, fg=fg, font=fuente, justify="left", anchor="w",
                           wraplength=self._wrap - 28, **kw)
            lab.pack(fill="x", anchor="w")
            self._burbujas.append(lab)
            self._rueda(lab)
            return lab

        texto((FUENTE, 11, "bold"), TEXTO, titulo).pack_configure(pady=(0, 6))
        for i, it in enumerate(items):
            if i:
                tk.Frame(tarjeta, bg=BORDE, height=1).pack(fill="x", pady=8)
            enlace = texto((FUENTE, 11, "bold"), ACENTO_H, it["titulo"] or it["url"])
            if it.get("url"):
                enlace.config(cursor="hand2")
                enlace.bind("<Button-1>", lambda e, u=it["url"]: webbrowser.open(u))
                enlace.bind("<Enter>", lambda e, l=enlace: l.config(font=(FUENTE, 11, "bold underline")))
                enlace.bind("<Leave>", lambda e, l=enlace: l.config(font=(FUENTE, 11, "bold")))
            if it.get("meta"):
                texto((FUENTE, 9), SUAVE, it["meta"])
            if it.get("texto"):
                texto((FUENTE, 10), TEXTO, it["texto"]).pack_configure(pady=(2, 0))
        self.after_idle(self._al_final)

    def agregar(self, quien, texto=None, imagen=None):
        es_usuario = quien == "user"
        burbuja, color = self._nueva_burbuja(quien)
        if texto:
            lab = tk.Label(burbuja, text=texto, bg=color, fg="#1b1b1b" if es_usuario else TEXTO,
                           font=(FUENTE, 11), justify="left", anchor="w", wraplength=self._wrap, padx=14, pady=9)
            lab.pack()
            self._burbujas.append(lab)
            self._rueda(lab)
        if imagen:
            foto = ImageTk.PhotoImage(imagen)
            self._fotos.append(foto)
            lab = tk.Label(burbuja, image=foto, bg=color, padx=6, pady=6)
            lab.pack(padx=6, pady=6)
            self._rueda(lab)
        self.after_idle(self._al_final)

    def poner_estado(self, texto):
        self.estado.config(text=texto)

    def mic_activo(self, activo):
        self.b_mic.config(state="disabled" if activo else "normal")
        self.poner_estado("🎙  Escuchando… hablá ahora" if activo else "")

    def _enviar_texto(self, texto=None):
        texto = (texto if texto is not None else self.entrada.get()).strip()
        if not texto:
            return
        self.entrada.delete(0, "end")
        self.agregar("user", texto)
        self.app.enviar(texto)

    def al_mostrar(self):
        self.entrada.focus_set()


# ---------------- Calendario ----------------
def leer_fecha(texto):
    """Acepta 25/09/2026, 25/9, 'mañana', 'el jueves', '25 de septiembre'..."""
    texto = texto.strip()
    for formato in ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(texto, formato).date()
        except ValueError:
            pass
    return calendario.interpretar_fecha(texto)


def leer_hora(texto):
    """Acepta 18, 18:30, 18h30 o 'a las 9 y media de la noche'."""
    m = re.fullmatch(r"(\d{1,2})(?:[:.h](\d{2}))?\s*(?:hs?)?", texto.strip().lower())
    if m:
        hora, minuto = int(m.group(1)), int(m.group(2) or 0)
        return (hora, minuto) if hora < 24 and minuto < 60 else None
    return calendario.interpretar_hora(texto)


class VistaCalendario(Vista):
    titulo = "Calendario"
    subtitulo = "Planificá tus publicaciones. Nova te avisa por voz 15 minutos antes."

    def construir(self, cuerpo):
        form = tk.Frame(cuerpo, bg=PANEL)
        form.pack(fill="x")
        interior = tk.Frame(form, bg=PANEL)
        interior.pack(fill="x", padx=16, pady=14)

        def campo(col, nombre, widget):
            marco = tk.Frame(interior, bg=PANEL)
            marco.grid(row=0, column=col, sticky="ew", padx=(0, 10))
            etiqueta(marco, nombre, bg=PANEL, font=(FUENTE, 9)).pack(anchor="w", pady=(0, 3))
            widget(marco).pack(fill="x", ipady=5)
            interior.grid_columnconfigure(col, weight=1 if col == 4 else 0)

        self.v_red = tk.StringVar(value="instagram")
        self.v_tipo = tk.StringVar(value="post")
        self.v_fecha = tk.StringVar(value=(datetime.date.today() + datetime.timedelta(days=1)).strftime("%d/%m/%Y"))
        self.v_hora = tk.StringVar(value="18:00")
        self.v_tema = tk.StringVar()
        campo(0, "Red", lambda m: ttk.Combobox(m, textvariable=self.v_red, values=calendario.REDES,
                                              state="readonly", width=11))
        campo(1, "Tipo", lambda m: ttk.Combobox(m, textvariable=self.v_tipo, values=calendario.TIPOS,
                                                state="readonly", width=10))
        campo(2, "Fecha (dd/mm/aaaa o «mañana»)", lambda m: entrada(m, textvariable=self.v_fecha, width=18))
        campo(3, "Hora", lambda m: entrada(m, textvariable=self.v_hora, width=8))
        campo(4, "Tema de la publicación", lambda m: entrada(m, textvariable=self.v_tema))
        boton(interior, "Agendar", self.agendar, primario=True).grid(row=0, column=5, sticky="s")

        barra = tk.Frame(cuerpo, bg=BG)
        barra.pack(fill="x", pady=(16, 8))
        self.v_filtro = tk.StringVar(value="Pendientes")
        cb = ttk.Combobox(barra, textvariable=self.v_filtro, values=["Pendientes", "Todas"], state="readonly", width=12)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.actualizar())
        boton(barra, "Actualizar", self.actualizar).pack(side="left", padx=8)
        boton(barra, "Eliminar", self.eliminar).pack(side="right")
        boton(barra, "Marcar como publicada", self.marcar_publicada).pack(side="right", padx=8)

        marco = tk.Frame(cuerpo, bg=PANEL)
        marco.pack(fill="both", expand=True)
        columnas = (("id", "N°", 50), ("fecha", "Fecha", 130), ("hora", "Hora", 70), ("red", "Red", 100),
                    ("tipo", "Tipo", 100), ("tema", "Tema", 320), ("estado", "Estado", 100))
        self.tabla = ttk.Treeview(marco, columns=[c[0] for c in columnas], show="headings", selectmode="browse")
        for clave, nombre, ancho in columnas:
            self.tabla.heading(clave, text=nombre, anchor="w")
            self.tabla.column(clave, width=ancho, anchor="w", stretch=(clave == "tema"))
        barra_v = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra_v.set)
        barra_v.pack(side="right", fill="y")
        self.tabla.pack(fill="both", expand=True)
        self.tabla.tag_configure("publicada", foreground=SUAVE)
        self.tabla.tag_configure("vencida", foreground=ERR)

    def al_mostrar(self):
        self.actualizar()

    def actualizar(self):
        hoy = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        pubs = calendario.listar_publicaciones(hoy - datetime.timedelta(days=30), hoy + datetime.timedelta(days=730),
                                               solo_pendientes=self.v_filtro.get() == "Pendientes")
        self.tabla.delete(*self.tabla.get_children())
        ahora = datetime.datetime.now()
        for p in pubs:
            f = datetime.datetime.strptime(p["fecha"], "%Y-%m-%d %H:%M")
            dia = calendario.NOMBRES_DIAS[f.weekday()][:3].capitalize()
            etiqueta_fila = "publicada" if p["estado"] == "publicada" else "vencida" if f < ahora else ""
            self.tabla.insert("", "end", iid=str(p["id"]), tags=(etiqueta_fila,),
                              values=(p["id"], f"{dia} {f.strftime('%d/%m/%Y')}", f.strftime("%H:%M"),
                                      p["red"].capitalize(), p["tipo"].capitalize(), p["tema"],
                                      p["estado"].capitalize()))

    def agendar(self):
        fecha, hora, tema = leer_fecha(self.v_fecha.get()), leer_hora(self.v_hora.get()), self.v_tema.get().strip()
        if not fecha:
            return self.msg("No entendí la fecha. Probá con 25/09/2026 o «mañana».", error=True)
        if not hora:
            return self.msg("No entendí la hora. Probá con 18:30.", error=True)
        if not tema:
            return self.msg("Escribí de qué trata la publicación.", error=True)
        id_pub = calendario.agregar_publicacion(self.v_red.get(), self.v_tipo.get(), fecha, hora, tema)
        self.v_tema.set("")
        self.msg(f"Listo, agendé la publicación número {id_pub} para el {fecha.strftime('%d/%m/%Y')} "
                 f"a las {hora[0]}:{hora[1]:02d}.")
        self.actualizar()
        self.tabla.selection_set(str(id_pub))

    def _seleccionada(self):
        sel = self.tabla.selection()
        if not sel:
            self.msg("Elegí primero una publicación de la lista.", error=True)
            return None
        return int(sel[0])

    def marcar_publicada(self):
        id_pub = self._seleccionada()
        if id_pub is not None and calendario.cambiar_estado(id_pub, "publicada"):
            self.msg(f"Marqué la publicación número {id_pub} como publicada.")
            self.actualizar()

    def eliminar(self):
        id_pub = self._seleccionada()
        if id_pub is None:
            return
        if messagebox.askyesno("Eliminar publicación", f"¿Borrar la publicación número {id_pub}?", parent=self.app):
            calendario.eliminar_publicacion(id_pub)
            self.msg(f"Eliminé la publicación número {id_pub}.")
            self.actualizar()


# ---------------- Diseño ----------------
FORMATOS_UI = {"Post 4:5": "post", "Cuadrado 1:1": "cuadrado", "Historia 9:16": "historia"}


class VistaDiseno(Vista):
    titulo = "Diseño"
    subtitulo = "Creá placas y carruseles con la identidad de tu marca."

    def construir(self, cuerpo):
        self.rutas, self.indice, self._foto, self._original, self._pendiente = [], 0, None, None, None
        self.modo = tk.StringVar(value="placa")
        self.paleta = tk.StringVar(value=config.PALETA_POR_DEFECTO)

        izq = tk.Frame(cuerpo, bg=BG, width=380)
        izq.pack(side="left", fill="y", padx=(0, 24))
        izq.pack_propagate(False)

        modos = tk.Frame(izq, bg=BG)
        modos.pack(fill="x", pady=(0, 14))
        self.b_placa = boton(modos, "Placa", lambda: self.cambiar_modo("placa"))
        self.b_carrusel = boton(modos, "Carrusel", lambda: self.cambiar_modo("carrusel"))
        self.b_placa.pack(side="left", expand=True, fill="x")
        self.b_carrusel.pack(side="left", expand=True, fill="x", padx=(6, 0))

        self.l_texto = etiqueta(izq, "")
        self.l_texto.pack(anchor="w", pady=(0, 3))
        self.t_texto = caja_texto(izq, 5)
        self.t_texto.pack(fill="x")

        self.l_sub = etiqueta(izq, "Subtítulo (opcional)")
        self.l_sub.pack(anchor="w", pady=(12, 3))
        self.e_sub = entrada(izq)
        self.e_sub.pack(fill="x", ipady=6)

        etiqueta(izq, "Formato").pack(anchor="w", pady=(12, 3))
        self.v_formato = tk.StringVar(value="Post 4:5")
        ttk.Combobox(izq, textvariable=self.v_formato, values=list(FORMATOS_UI), state="readonly").pack(fill="x", ipady=3)

        etiqueta(izq, "Paleta").pack(anchor="w", pady=(12, 4))
        paletas = tk.Frame(izq, bg=BG)
        paletas.pack(fill="x")
        self.muestras = {}
        for nombre, c in config.PALETAS.items():
            cv = tk.Canvas(paletas, width=104, height=66, bg=BG, highlightthickness=0, cursor="hand2")
            cv.create_rectangle(4, 4, 100, 50, fill=_hex(c["fondo"]), outline="", tags="fondo")
            cv.create_text(52, 24, text="Aa", fill=_hex(c["texto"]), font=(FUENTE, 15, "bold"))
            cv.create_rectangle(36, 38, 68, 43, fill=_hex(c["acento"]), outline="")
            cv.create_text(52, 59, text=nombre.capitalize(), fill=SUAVE, font=(FUENTE, 8))
            cv.bind("<Button-1>", lambda e, n=nombre: self.elegir_paleta(n))
            cv.pack(side="left", padx=(0, 6))
            self.muestras[nombre] = cv

        boton(izq, "Generar pieza", self.generar, primario=True).pack(fill="x", pady=(18, 0), ipady=4)

        der = tk.Frame(cuerpo, bg=PANEL)
        der.pack(side="left", fill="both", expand=True)
        self.area = tk.Label(der, bg=PANEL, fg=SUAVE, font=(FUENTE, 11), text="Tu pieza aparece acá")
        self.area.pack(fill="both", expand=True, padx=10, pady=10)
        self.area.bind("<Configure>", lambda e: self._programar_render())
        pie = tk.Frame(der, bg=PANEL)
        pie.pack(fill="x", padx=10, pady=(0, 10))
        # Los botones de la derecha se empaquetan primero para que nunca queden tapados
        boton(pie, "Publicar en Instagram", self.publicar).pack(side="right")
        boton(pie, "Abrir carpeta", self.abrir_carpeta).pack(side="right", padx=(0, 8))
        self.b_ant = boton(pie, "◀", lambda: self.navegar(-1))
        self.b_sig = boton(pie, "▶", lambda: self.navegar(1))
        self.l_pos = etiqueta(pie, "", bg=PANEL, font=(FUENTE, 10), width=6)
        self.b_ant.pack(side="left")
        self.l_pos.pack(side="left", padx=6)
        self.b_sig.pack(side="left")

        self.cambiar_modo("placa")
        self.elegir_paleta(config.PALETA_POR_DEFECTO)

    # -- formulario --
    def cambiar_modo(self, modo):
        self.modo.set(modo)
        for b, activo in ((self.b_placa, modo == "placa"), (self.b_carrusel, modo == "carrusel")):
            b.config(bg=ACENTO if activo else PANEL2, fg="#1b1b1b" if activo else TEXTO)
            b.bind("<Leave>", lambda e, b=b, a=activo: b.config(bg=ACENTO if a else PANEL2))
        if modo == "placa":
            self.l_texto.config(text="Mensaje principal")
            self.l_sub.pack(anchor="w", pady=(12, 3), after=self.t_texto)
            self.e_sub.pack(fill="x", ipady=6, after=self.l_sub)
        else:
            self.l_texto.config(text="Texto de cada slide (una por línea, de 2 a 10)")
            self.l_sub.pack_forget()
            self.e_sub.pack_forget()

    def elegir_paleta(self, nombre):
        self.paleta.set(nombre)
        for n, cv in self.muestras.items():
            cv.delete("marco")
            if n == nombre:
                cv.create_rectangle(2, 2, 102, 52, outline=ACENTO, width=2, tags="marco")

    def generar(self):
        texto = self.t_texto.get("1.0", "end").strip()
        if not texto:
            return self.msg("Escribí el texto de la pieza.", error=True)
        formato, paleta = FORMATOS_UI[self.v_formato.get()], self.paleta.get()
        if self.modo.get() == "placa":
            rutas = [diseno.crear_placa(texto, formato, paleta, self.e_sub.get().strip() or None)]
            self.msg("Placa creada y guardada en la carpeta piezas.")
        else:
            textos = [linea.strip() for linea in texto.splitlines() if linea.strip()]
            if len(textos) < 2:
                return self.msg("Un carrusel necesita al menos 2 slides: escribí una por línea.", error=True)
            rutas = diseno.crear_carrusel(textos[:10], paleta, formato)
            self.msg(f"Carrusel de {len(rutas)} slides creado y guardado en la carpeta piezas.")
        self.mostrar(rutas)

    # -- vista previa --
    def mostrar(self, rutas, indice=0):
        self.rutas, self.indice = list(rutas), indice
        self._cargar()

    def navegar(self, paso):
        if self.rutas:
            self.indice = (self.indice + paso) % len(self.rutas)
            self._cargar()

    def _cargar(self):
        if not self.rutas:
            return
        self._original = Image.open(self.rutas[self.indice])
        self._original.load()
        varias = len(self.rutas) > 1
        for b in (self.b_ant, self.b_sig):
            b.config(state="normal" if varias else "disabled")
        self.l_pos.config(text=f"{self.indice + 1} / {len(self.rutas)}")
        self._render()

    def _programar_render(self):
        if self._pendiente:
            self.after_cancel(self._pendiente)
        self._pendiente = self.after(80, self._render)

    def _render(self):
        self._pendiente = None
        if self._original is None:
            return
        ancho, alto = max(self.area.winfo_width() - 8, 100), max(self.area.winfo_height() - 8, 100)
        copia = self._original.copy()
        copia.thumbnail((ancho, alto), Image.LANCZOS)
        self._foto = ImageTk.PhotoImage(copia)
        self.area.config(image=self._foto, text="")

    def al_mostrar(self):
        if not self.rutas:
            ultima = diseno.ultima_pieza()
            if ultima:
                self.mostrar([ultima])

    # -- acciones --
    def abrir_carpeta(self):
        os.makedirs(config.CARPETA_PIEZAS, exist_ok=True)
        os.startfile(config.CARPETA_PIEZAS)

    def publicar(self):
        if not self.rutas:
            return self.msg("Primero generá una pieza.", error=True)
        ruta = self.rutas[self.indice]
        descripcion = simpledialog.askstring("Publicar en Instagram", "Descripción de la publicación:", parent=self.app)
        if descripcion is None:
            return
        demo = "\n\n(Modo demostración: no se publica de verdad.)" if config.MODO_DEMO_REDES else ""
        if not messagebox.askyesno("Confirmar", f"¿Publicar {os.path.basename(ruta)} en Instagram?{demo}", parent=self.app):
            return

        def tarea():
            try:
                comunidad.publicar_en_instagram(ruta, descripcion)
                self.app.ui(lambda: self.msg("¡Publicado en Instagram!" + (" (demo)" if config.MODO_DEMO_REDES else "")))
            except Exception as e:
                self.app.ui(lambda: self.msg(f"No pude publicar: {e}", error=True))
        en_hilo(tarea)


# ---------------- Comunidad ----------------
class VistaComunidad(Vista):
    titulo = "Comunidad"
    subtitulo = "Comentarios sin responder, clasificados por la base de conocimiento."

    def construir(self, cuerpo):
        self.items, self.cargado = {}, False
        barra = tk.Frame(cuerpo, bg=BG)
        barra.pack(fill="x", pady=(0, 8))
        self.resumen = tk.Label(barra, text="", bg=BG, fg=TEXTO, font=(FUENTE, 11, "bold"), anchor="w")
        self.resumen.pack(side="left")
        boton(barra, "Actualizar", self.actualizar).pack(side="right")
        if config.MODO_DEMO_REDES:
            tk.Label(barra, text=" MODO DEMO ", bg=ACENTO_OSC, fg=ACENTO_H, font=(FUENTE, 8, "bold")
                     ).pack(side="right", padx=10)

        marco = tk.Frame(cuerpo, bg=PANEL)
        marco.pack(fill="both", expand=True)
        columnas = (("usuario", "Usuario", 130), ("texto", "Comentario", 380), ("tipo", "Clasificación", 210),
                    ("prioridad", "Prioridad", 90))
        self.tabla = ttk.Treeview(marco, columns=[c[0] for c in columnas], show="headings", selectmode="browse", height=7)
        for clave, nombre, ancho in columnas:
            self.tabla.heading(clave, text=nombre, anchor="w")
            self.tabla.column(clave, width=ancho, anchor="w", stretch=(clave == "texto"))
        self.tabla.pack(fill="both", expand=True)
        self.tabla.tag_configure("alta", foreground=ERR)
        self.tabla.bind("<<TreeviewSelect>>", self._al_elegir)

        etiqueta(cuerpo, "Respuesta (podés editarla antes de enviar)").pack(anchor="w", pady=(14, 3))
        self.t_resp = caja_texto(cuerpo, 3)
        self.t_resp.pack(fill="x")
        botones = tk.Frame(cuerpo, bg=BG)
        botones.pack(fill="x", pady=(10, 0))
        self.b_enviar = boton(botones, "Enviar respuesta", self.enviar, primario=True)
        self.b_enviar.pack(side="left")
        boton(botones, "Omitir por ahora", self.omitir).pack(side="left", padx=8)

    def al_mostrar(self):
        if not self.cargado:
            self.actualizar()

    def actualizar(self):
        self.resumen.config(text="Cargando comentarios…")

        def tarea():
            try:
                comentarios, error = comunidad.obtener_comentarios(), None
            except Exception as e:
                comentarios, error = None, e
            self.app.ui(lambda: self._mostrar(comentarios, error))
        en_hilo(tarea)

    def _mostrar(self, comentarios, error):
        self.cargado = True
        self.tabla.delete(*self.tabla.get_children())
        self.items.clear()
        self.t_resp.delete("1.0", "end")
        if error:
            self.resumen.config(text="")
            return self.msg("No pude conectarme con Instagram. Revisá el token de acceso.", error=True)
        orden = {"alta": 0, "media": 1, "baja": 2}
        comentarios = sorted(comentarios, key=lambda c: orden[comunidad.clasificar_comentario(c["texto"])["prioridad"]])
        for c in comentarios:
            regla = comunidad.clasificar_comentario(c["texto"])
            self.items[c["id"]] = (c, regla)
            self.tabla.insert("", "end", iid=c["id"], tags=(regla["prioridad"],),
                              values=(c["usuario"], c["texto"], comunidad.NOMBRES_INTENCION[regla["intencion"]].capitalize(),
                                      regla["prioridad"].capitalize()))
        self._actualizar_resumen()
        primero = self.tabla.get_children()
        if primero:
            self.tabla.selection_set(primero[0])

    def _actualizar_resumen(self):
        total = len(self.items)
        if not total:
            self.resumen.config(text="No hay comentarios sin responder. ¡Bien ahí!")
            return
        quejas = sum(1 for _, r in self.items.values() if r["intencion"] == "queja")
        extra = f"  ·  {quejas} {'queja urgente' if quejas == 1 else 'quejas urgentes'}" if quejas else ""
        self.resumen.config(text=f"{total} sin responder{extra}")

    def _al_elegir(self, _evento=None):
        sel = self.tabla.selection()
        if sel:
            self.t_resp.delete("1.0", "end")
            self.t_resp.insert("1.0", self.items[sel[0]][1]["respuesta"])

    def _quitar_seleccionado(self):
        sel = self.tabla.selection()[0]
        siguiente = self.tabla.next(sel) or self.tabla.prev(sel)
        self.tabla.delete(sel)
        self.items.pop(sel, None)
        self.t_resp.delete("1.0", "end")
        if siguiente:
            self.tabla.selection_set(siguiente)
        self._actualizar_resumen()

    def enviar(self):
        sel = self.tabla.selection()
        mensaje = self.t_resp.get("1.0", "end").strip()
        if not sel:
            return self.msg("Elegí un comentario de la lista.", error=True)
        if not mensaje:
            return self.msg("Escribí la respuesta.", error=True)
        comentario = self.items[sel[0]][0]
        self.b_enviar.config(state="disabled")

        def tarea():
            try:
                comunidad.responder_comentario(comentario["id"], mensaje)
                self.app.ui(lambda: self._respondido(comentario))
            except Exception as e:
                self.app.ui(lambda: self.msg(f"No pude enviar esa respuesta: {e}", error=True))
            self.app.ui(lambda: self.b_enviar.config(state="normal"))
        en_hilo(tarea)

    def _respondido(self, comentario):
        if comentario["id"] in self.items and self.tabla.exists(comentario["id"]):
            self.tabla.selection_set(comentario["id"])
            self._quitar_seleccionado()
        self.msg(f"Respuesta enviada a {comentario['usuario']}." + (" (demo)" if config.MODO_DEMO_REDES else ""))

    def omitir(self):
        if self.tabla.selection():
            self._quitar_seleccionado()
            self.msg("Comentario omitido por ahora.")


# ---------------- Ventana principal ----------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{config.NOMBRE_ASISTENTE} · Asistente de marketing")
        # Se adapta a pantallas chicas (por ejemplo 1366x768) y arranca centrada
        ancho = min(1200, self.winfo_screenwidth() - 60)
        alto = min(780, self.winfo_screenheight() - 110)
        self.geometry(f"{ancho}x{alto}+{(self.winfo_screenwidth() - ancho) // 2}+{max(0, (self.winfo_screenheight() - alto) // 2 - 20)}")
        self.minsize(min(1000, ancho), min(640, alto))
        self.configure(bg=BG)
        aplicar_estilos(self)

        self.cola_ui = queue.Queue()
        self.entradas = queue.Queue()
        self.vistas, self.botones_nav = {}, {}

        self._barra_lateral()
        self.contenido = tk.Frame(self, bg=BG)
        self.contenido.pack(side="left", fill="both", expand=True)
        self.chat = self._agregar_vista("asistente", VistaChat)
        self.calendario = self._agregar_vista("calendario", VistaCalendario)
        self.diseno = self._agregar_vista("diseno", VistaDiseno)
        self.comunidad = self._agregar_vista("comunidad", VistaComunidad)
        self.mostrar_vista("asistente")

        voz.salida_gui = self._salida
        voz.entrada_gui = self._esperar_respuesta
        diseno.mostrar_pieza = lambda ruta: self.ui(lambda: self._pieza_creada(ruta))
        base.mostrar_resultados = lambda titulo, items: self.ui(lambda: self.chat.agregar_resultados(titulo, items))

        self.after(50, self._vaciar_cola)
        en_hilo(self._bucle_asistente)

    # -- construcción --
    def _barra_lateral(self):
        lado = tk.Frame(self, bg=PANEL, width=220)
        lado.pack(side="left", fill="y")
        lado.pack_propagate(False)
        tk.Label(lado, text=config.NOMBRE_ASISTENTE, bg=PANEL, fg=ACENTO, font=(FUENTE, 24, "bold"), anchor="w"
                 ).pack(fill="x", padx=22, pady=(26, 0))
        etiqueta(lado, "Asistente de marketing", bg=PANEL).pack(fill="x", padx=22, pady=(0, 24))
        self.lado = lado
        self._nav = tk.Frame(lado, bg=PANEL)
        self._nav.pack(fill="x")

        pie = tk.Frame(lado, bg=PANEL)
        pie.pack(side="bottom", fill="x", padx=16, pady=18)
        self.b_voz = boton(pie, "", self.alternar_voz)
        self.b_voz.pack(fill="x")
        self._texto_voz()
        redes = "Redes: modo demo" if config.MODO_DEMO_REDES else "Redes: Instagram conectado"
        etiqueta(pie, redes, bg=PANEL, font=(FUENTE, 9)).pack(fill="x", pady=(10, 0))
        etiqueta(pie, f"Usuario: {config.NOMBRE_USUARIO}", bg=PANEL, font=(FUENTE, 9)).pack(fill="x")

    def _agregar_vista(self, clave, clase):
        vista = clase(self.contenido, self)
        vista.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.vistas[clave] = vista
        nombres = {"asistente": "💬  Asistente", "calendario": "📅  Calendario", "diseno": "🎨  Diseño",
                   "comunidad": "💌  Comunidad"}
        b = tk.Button(self._nav, text=nombres[clave], anchor="w", relief="flat", bd=0, padx=22, pady=12,
                      font=(FUENTE, 11), bg=PANEL, fg=SUAVE, activebackground=PANEL2, activeforeground=TEXTO,
                      cursor="hand2", command=lambda: self.mostrar_vista(clave))
        b.pack(fill="x")
        self.botones_nav[clave] = b
        return vista

    def mostrar_vista(self, clave):
        for k, b in self.botones_nav.items():
            b.config(bg=PANEL2 if k == clave else PANEL, fg=TEXTO if k == clave else SUAVE)
        self.vistas[clave].tkraise()
        self.vistas[clave].al_mostrar()

    # -- voz --
    def _texto_voz(self):
        self.b_voz.config(text="🔊  Voz activada" if config.VOZ_ACTIVA else "🔇  Voz silenciada")

    def alternar_voz(self):
        config.VOZ_ACTIVA = not config.VOZ_ACTIVA
        self._texto_voz()

    # -- puente entre la interfaz y el hilo del asistente --
    def ui(self, funcion):
        """Pide ejecutar algo en el hilo de la interfaz (tkinter no es seguro entre hilos)."""
        self.cola_ui.put(funcion)

    def _vaciar_cola(self):
        try:
            while True:
                try:
                    self.cola_ui.get_nowait()()
                except queue.Empty:
                    break
                except Exception:
                    traceback.print_exc()
        finally:
            self.after(50, self._vaciar_cola)

    def enviar(self, texto):
        self.entradas.put(texto)

    def _salida(self, mensaje):
        self.ui(lambda: self.chat.agregar("bot", mensaje))

    def _esperar_respuesta(self):
        self.ui(lambda: self.chat.poner_estado("Nova espera tu respuesta…"))
        texto = self.entradas.get()
        self.ui(lambda: self.chat.poner_estado(""))
        return texto

    def _bucle_asistente(self):
        base.saludo_inicial()
        calendario.iniciar_recordatorios()
        while True:
            pedido = self.entradas.get()
            try:
                if not nucleo.procesar_pedido(pedido):
                    time.sleep(1.2)
                    self.ui(self.destroy)
                    return
            except Exception as e:
                print(f"Error: {e}")
                voz.hablar("Ups, algo salió mal con ese pedido. Probemos de nuevo")

    def escuchar(self):
        self.chat.mic_activo(True)

        def tarea():
            try:
                texto = voz.escuchar_microfono(timeout=8, limite=20)
            except Exception as e:
                print(f"Micrófono: {e}")
                return self.ui(lambda: self._mic_terminado(None, "No pude usar el micrófono. Revisá que esté conectado y habilitado."))
            self.ui(lambda: self._mic_terminado(texto))
        en_hilo(tarea)

    def _mic_terminado(self, texto, error=None):
        self.chat.mic_activo(False)
        if error or not texto or texto == "sigo esperando":
            return self.chat.agregar("bot", error or "No te escuché bien. Probá de nuevo o escribime el pedido.")
        self.chat.agregar("user", texto)
        self.enviar(texto)

    # -- piezas creadas desde el chat --
    def _pieza_creada(self, ruta):
        rutas = [ruta]
        m = re.match(r"(carrusel_\d{8}_\d{6})_\d+\.png$", os.path.basename(ruta))
        if m:
            rutas = sorted(glob.glob(os.path.join(os.path.dirname(ruta), m.group(1) + "_*.png")),
                           key=lambda r: int(re.search(r"_(\d+)\.png$", r).group(1)))
        self.diseno.mostrar(rutas)
        miniatura = Image.open(rutas[0])
        miniatura.thumbnail((220, 275))
        self.chat.agregar("bot", imagen=miniatura)


def main():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)   # texto nítido en pantallas con escala
    except Exception:
        pass
    App().mainloop()


if __name__ == "__main__":
    main()

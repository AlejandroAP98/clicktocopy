# -*- coding: utf-8 -*-
"""
C2C — Click to Copy (v3, filas multi-campo)
- Cada fila puede tener 1, 2 o más campos (definidos al crear/editar).
- Cada campo es un solo valor: una línea del formulario = un valor.
- El nombre de la fila es opcional.
- Click en un campo -> copia ese campo (los valores quedan ocultos con ███).
- Se agrupan por categorías plegables.
- Todo se guarda automáticamente en datos.json.
- Estilo dual: temas "pixel" (Pico-8/CRT) y "normal" (clásico), elegibles
  con el botón Tema y recordados en config.json.
"""

import json
import os
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox

try:
    import pyperclip
except ImportError:
    pyperclip = None

try:
    import tksvg
except ImportError:
    tksvg = None

if getattr(sys, "frozen", False):
    # ejecutable compilado: recursos empacados en _MEIPASS, datos junto al exe
    APP_DIR = os.path.dirname(sys.executable)
    RES_DIR = getattr(sys, "_MEIPASS", APP_DIR)
else:
    APP_DIR = RES_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = APP_DIR
DATA_FILE = os.path.join(APP_DIR, "datos.json")

# ---------- Paleta (Pico-8 / CRT) ----------
BG        = "#13142b"   # fondo general (azul noche)
BG_SOFT   = "#1a1b3a"   # fondo suave (formularios)
CARD      = "#222447"   # tarjeta
CARD_HOV  = "#2c2f5e"   # tarjeta al pasar el mouse
FLASH     = "#008751"   # destello verde al copiar (Pico-8)
STROKE    = "#3b3f77"   # bordes pixel
FG        = "#fff1e8"   # texto principal (blanco cálido Pico-8)
MUTED     = "#83769c"   # texto secundario (Pico-8)
ACCENT    = "#29adff"   # acento principal (azul Pico-8)
ACCENT_HV = "#5fc2ff"
RED       = "#ff004d"   # acciones destructivas (Pico-8)
VAL_FG    = "#aebdff"   # valor oculto (azul suave)
GROUP_COLORS = ["#ff004d", "#29adff", "#ffec27", "#00e436", "#ff77a8", "#ffa300"]

FONT       = ("Segoe UI", 10)   # se cambian a pixel en _setup_fonts()
FONT_BOLD  = ("Segoe UI", 10, "bold")
FONT_SMALL = ("Segoe UI", 9)
FONT_TITLE = ("Segoe UI", 12, "bold")

MAX_COLS = 3   # bloques por línea en cada fila


def _load_font_files():
    """Registra los TTF pixel solo para este proceso (sin instalarlos)."""
    if os.name != "nt":
        return
    try:
        import ctypes
        gdi32 = ctypes.windll.gdi32
        for name in ("PressStart2P-Regular.ttf", "VT323-Regular.ttf"):
            path = os.path.join(RES_DIR, "fonts", name)
            if os.path.exists(path):
                gdi32.AddFontResourceExW(path, 0x10, 0)   # FR_PRIVATE
    except Exception:
        pass


_load_font_files()

# ---------- Temas ----------
THEMES = {
    "pixel": {
        "BORDER": 2,
        "BG": "#13142b", "BG_SOFT": "#1a1b3a", "CARD": "#222447",
        "CARD_HOV": "#2c2f5e", "FLASH": "#008751", "STROKE": "#3b3f77",
        "FG": "#fff1e8", "MUTED": "#83769c", "ACCENT": "#29adff",
        "ACCENT_HV": "#5fc2ff", "RED": "#ff004d", "VAL_FG": "#aebdff",
        "GROUP_COLORS": ["#ff004d", "#29adff", "#ffec27", "#00e436",
                         "#ff77a8", "#ffa300"],
    },
    "normal": {
        "BORDER": 1,
        "BG": "#141518", "BG_SOFT": "#191b1f", "CARD": "#1e2126",
        "CARD_HOV": "#262a31", "FLASH": "#2e5d3a", "STROKE": "#2c2f35",
        "FG": "#e9eaee", "MUTED": "#8b8f98", "ACCENT": "#6c8cff",
        "ACCENT_HV": "#5a79e6", "RED": "#e05c6e", "VAL_FG": "#aebdff",
        "GROUP_COLORS": ["#e05c6e", "#6c8cff", "#f5a623", "#4ecb8d",
                         "#9b6cff", "#39c5cf"],
    },
}

FONT_SETS = {
    "pixel": {"FONT": ("VT323", 14), "FONT_BOLD": ("Press Start 2P", 8),
              "FONT_SMALL": ("VT323", 12),
              "FONT_TITLE": ("Press Start 2P", 8)},
    "normal": {"FONT": ("Segoe UI", 10),
               "FONT_BOLD": ("Segoe UI", 10, "bold"),
               "FONT_SMALL": ("Segoe UI", 9),
               "FONT_TITLE": ("Segoe UI", 12, "bold")},
}

PIXEL_FONTS_OK = False   # se comprueba al crear la ventana

CONFIG_FILE = os.path.join(APP_DIR, "config.json")


def load_theme():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if cfg.get("theme") in THEMES:
            return cfg["theme"]
    except (OSError, ValueError):
        pass
    return "pixel"


def save_theme(name):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"theme": name}, f)
    except OSError:
        pass


def copy_to_clipboard(text):
    """Copia al portapapeles. Usa pyperclip si está; si no, el de Tk."""
    if pyperclip is not None:
        pyperclip.copy(text)
        return
    root = tk._default_root
    if root is None:
        raise RuntimeError("No hay forma de copiar")
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()


def masked(value):
    n = max(6, min(len(value), 12))
    return "█" * n


# ---------- Iconos pixel (rejillas 12x12; "#" = píxel encendido) ----------
PIXEL_ICONS = {
    "plus": (
        "............",
        ".....##.....",
        ".....##.....",
        ".....##.....",
        ".....##.....",
        ".##########.",
        ".##########.",
        ".....##.....",
        ".....##.....",
        ".....##.....",
        ".....##.....",
        "............",
    ),
    "anchor": (
        "............",
        ".....##.....",
        "....#..#....",
        "....#..#....",
        ".....##.....",
        ".....##.....",
        ".###.##.###.",
        ".##..##..##.",
        ".##..##..##.",
        ".##..##..##.",
        "..########..",
        "............",
    ),
    "eye": (
        "............",
        "............",
        "....####....",
        "..##....##..",
        ".#...##...#.",
        "#...####...#",
        "#...####...#",
        ".#...##...#.",
        "..##....##..",
        "....####....",
        "............",
        "............",
    ),
    "eye_off": (
        "............",
        ".#..........",
        "..#..###....",
        "..##....##..",
        ".#..#.#...#.",
        "#...##.#...#",
        "#...###....#",
        ".#...###..#.",
        "..##....#...",
        "....####.#..",
        "..........#.",
        "............",
    ),
    "pencil": (
        "............",
        ".#####..#...",
        ".#####.#.#..",
        ".##...#...#.",
        ".##..#...#..",
        ".##.#...#...",
        ".##.##.#.##.",
        ".##.###..##.",
        ".##......##.",
        ".##########.",
        ".##########.",
        "............",
    ),
    "copy": (
        "............",
        "..######....",
        ".#......#...",
        ".#..######..",
        ".#.#......#.",
        ".#.#......#.",
        ".#.#......#.",
        ".#.#......#.",
        "..##......#.",
        "...#......#.",
        "....######..",
        "............",
    ),
    "trash": (
        "............",
        "....####....",
        "...##..##...",
        ".##########.",
        "..#......#..",
        "..#......#..",
        "..#......#..",
        "..#......#..",
        "..#......#..",
        "..#......#..",
        "...######...",
        "............",
    ),
    "chevron_down": (
        "............",
        "............",
        "............",
        "............",
        "..##....##..",
        "...##..##...",
        "....####....",
        ".....##.....",
        "............",
        "............",
        "............",
        "............",
    ),
    "circle": (
        "............",
        "...######...",
        "..#......#..",
        ".#........#.",
        ".#........#.",
        ".#........#.",
        ".#........#.",
        ".#........#.",
        ".#........#.",
        "..#......#..",
        "...######...",
        "............",
    ),
    "card": (
        "............",
        "..########..",
        ".#........#.",
        ".#.#.####.#.",
        ".#.#.####.#.",
        ".#.#.####.#.",
        ".#.#.####.#.",
        ".#.#.####.#.",
        ".#........#.",
        "..########..",
        "............",
        "............",
    ),
    "window": (
        "............",
        ".##########.",
        ".#........#.",
        ".#.##.##..#.",
        ".#........#.",
        ".#........#.",
        ".#........#.",
        ".#........#.",
        ".#........#.",
        ".#........#.",
        ".##########.",
        "............",
    ),
    "pixelart": (
        "............",
        "..########..",
        ".#........#.",
        "...####.....",
        "...####.....",
        "...####.....",
        ".......##...",
        ".......##...",
        "......####..",
        "............",
        "..########..",
        "............",
    ),
}
# chevron arriba = chevron abajo volteado
PIXEL_ICONS["chevron_up"] = tuple(reversed(PIXEL_ICONS["chevron_down"]))


def _render_pixel_icon(name, color, scale=2):
    """Dibuja una rejilla pixel en una PhotoImage (sin anti-aliasing)."""
    grid = PIXEL_ICONS[name]
    w, h = len(grid[0]), len(grid)
    img = tk.PhotoImage(width=w, height=h)
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch == "#":
                img.put(color, (x, y))
    return img.zoom(scale) if scale > 1 else img


# ---------- Iconos SVG suavizados (tema "normal"; requieren tksvg) ----------
ICONS = {
    "plus":
        '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5V19M5 12H19" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "trash":
        '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M16 6V5.2C16 4.0799 16 3.51984 15.782 3.09202C15.5903 2.71569 15.2843 2.40973 14.908 2.21799C14.4802 2 13.9201 2 12.8 2H11.2C10.0799 2 9.51984 2 9.09202 2.21799C8.71569 2.40973 8.40973 2.71569 8.21799 3.09202C8 3.51984 8 4.0799 8 5.2V6M3 6H21M19 6V17.2C19 18.8802 19 19.7202 18.673 20.362C18.3854 20.9265 17.9265 21.3854 17.362 21.673C16.7202 22 15.8802 22 14.2 22H9.8C8.11984 22 7.27976 22 6.63803 21.673C6.07354 21.3854 5.6146 20.9265 5.32698 20.362C5 19.7202 5 18.8802 5 17.2V6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "anchor":
        '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 8C13.6569 8 15 6.65685 15 5C15 3.34315 13.6569 2 12 2C10.3431 2 9 3.34315 9 5C9 6.65685 10.3431 8 12 8ZM12 8V22M12 22C9.34784 22 6.8043 20.9464 4.92893 19.0711C3.05357 17.1957 2 14.6522 2 12H5M12 22C14.6522 22 17.1957 20.9464 19.0711 19.0711C20.9464 17.1957 22 14.6522 22 12H19" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "eye":
        '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M2.42012 12.7132C2.28394 12.4975 2.21584 12.3897 2.17772 12.2234C2.14909 12.0985 2.14909 11.9015 2.17772 11.7766C2.21584 11.6103 2.28394 11.5025 2.42012 11.2868C3.54553 9.50484 6.8954 5 12.0004 5C17.1054 5 20.4553 9.50484 21.5807 11.2868C21.7169 11.5025 21.785 11.6103 21.8231 11.7766C21.8517 11.9015 21.8517 12.0985 21.8231 12.2234C21.785 12.3897 21.7169 12.4975 21.5807 12.7132C20.4553 14.4952 17.1054 19 12.0004 19C6.8954 19 3.54553 14.4952 2.42012 12.7132Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M12.0004 15C13.6573 15 15.0004 13.6569 15.0004 12C15.0004 10.3431 13.6573 9 12.0004 9C10.3435 9 9.0004 10.3431 9.0004 12C9.0004 13.6569 10.3435 15 12.0004 15Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "eye_off":
        '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M10.7429 5.09232C11.1494 5.03223 11.5686 5 12.0004 5C17.1054 5 20.4553 9.50484 21.5807 11.2868C21.7169 11.5025 21.785 11.6103 21.8231 11.7767C21.8518 11.9016 21.8517 12.0987 21.8231 12.2236C21.7849 12.3899 21.7164 12.4985 21.5792 12.7156C21.2793 13.1901 20.8222 13.8571 20.2165 14.5805M6.72432 6.71504C4.56225 8.1817 3.09445 10.2194 2.42111 11.2853C2.28428 11.5019 2.21587 11.6102 2.17774 11.7765C2.1491 11.9014 2.14909 12.0984 2.17771 12.2234C2.21583 12.3897 2.28393 12.4975 2.42013 12.7132C3.54554 14.4952 6.89541 19 12.0004 19C14.0588 19 15.8319 18.2676 17.2888 17.2766M3.00042 3L21.0004 21M9.8791 9.87868C9.3362 10.4216 9.00042 11.1716 9.00042 12C9.00042 13.6569 10.3436 15 12.0004 15C12.8288 15 13.5788 14.6642 14.1217 14.1213" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "pencil":
        '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M18 10L14 6M2.49997 21.5L5.88434 21.124C6.29783 21.078 6.50457 21.055 6.69782 20.9925C6.86926 20.937 7.03242 20.8586 7.18286 20.7594C7.35242 20.6475 7.49951 20.5005 7.7937 20.2063L21 7C22.1046 5.89543 22.1046 4.10457 21 3C19.8954 1.89543 18.1046 1.89543 17 3L3.7937 16.2063C3.49952 16.5005 3.35242 16.6475 3.24061 16.8171C3.1414 16.9676 3.06298 17.1307 3.00748 17.3022C2.94493 17.4954 2.92195 17.7021 2.87601 18.1156L2.49997 21.5Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "chevron_down":
        '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M6 9L12 15L18 9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "chevron_up":
        '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M18 15L12 9L6 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "card":
        '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17.5 17H6.5M17.5 13H6.5M3 9H21M7.8 3H16.2C17.8802 3 18.7202 3 19.362 3.32698C19.9265 3.6146 20.3854 4.07354 20.673 4.63803C21 5.27976 21 6.11984 21 7.8V16.2C21 17.8802 21 18.7202 20.673 19.362C20.3854 19.9265 19.9265 20.3854 19.362 20.673C18.7202 21 17.8802 21 16.2 21H7.8C6.11984 21 5.27976 21 4.63803 20.673C4.07354 20.3854 3.6146 19.9265 3.32698 19.362C3 18.7202 3 17.8802 3 16.2V7.8C3 6.11984 3 5.27976 3.32698 4.63803C3.6146 4.07354 4.07354 3.6146 4.63803 3.32698C5.27976 3 6.11984 3 7.8 3Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "copy":
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M8 6h12v2H8zM4 2h12v2H4zm2 6h2v12H6zM2 4h2v12H2zm6 16h12v2H8zM20 8h2v12h-2zm-4-4h2v2h-2zM4 16h2v2H4z"/></svg>',
    "pixelart":
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M7 13h2v2H7zm0-6h6v2H7zM4 2h16v2H4zm0 18h16v2H4zm-2 0V4h2v16zm18 0V4h2v16zM7 11h6v2H7zm4-2h2v2h-2zM7 9h2v2H7zm6 4h2v2h-2zm2-2h2v2h-2zm0 4h2v2h-2zm-4 0h2v2h-2z"/></svg>',
    "window":
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7h18v12H3z"/><path d="M3 10h18"/><path d="M5.5 8.5h1"/><path d="M8.5 8.5h1"/></svg>',
}


def _render_pixel_icon(name, color, scale=2):
    """Dibuja una rejilla pixel en una PhotoImage (sin anti-aliasing)."""
    grid = PIXEL_ICONS[name]
    w, h = len(grid[0]), len(grid)
    img = tk.PhotoImage(width=w, height=h)
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch == "#":
                img.put(color, (x, y))
    return img.zoom(scale) if scale > 1 else img


# ---------- Persistencia ----------
def empty_data():
    return [{"name": "General", "rows": []}]


def load_data():
    """Devuelve grupos v3: [{"name": str, "rows": [{"name": str|"",
    "fields": [{"name": str|"", "value": str}]}]}]"""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if (isinstance(data, dict) and data.get("version") == 3
                and isinstance(data.get("groups"), list)):
            return data["groups"]
    except (OSError, ValueError):
        pass
    return empty_data()


def save_data(groups):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"version": 3, "groups": groups}, f,
                      ensure_ascii=False, indent=2)
    except OSError as e:
        messagebox.showerror("Error", f"No se pudo guardar datos.json:\n{e}")


def _set_bg(widget, color):
    """Cambia el bg de un widget y de todos sus descendientes (si se puede)."""
    try:
        widget.configure(bg=color)
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        _set_bg(child, color)


def _set_titlebar(window, bg_hex, fg_hex):
    """Colorea la barra de título (Windows 10/11 vía DWM)."""
    if os.name != "nt":
        return
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        dwm = ctypes.windll.dwmapi

        def colorref(h):
            h = h.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return ctypes.c_int((b << 16) | (g << 8) | r)

        dark = ctypes.c_int(1)
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), 4)
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(colorref(bg_hex)), 4)
        dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(colorref(fg_hex)), 4)
    except Exception:
        pass


_DBLCLICK_PROCS = {}   # hwnd -> callback vivo del subclass (Windows)
_SUBCLASS_PROC_TYPE = None


_DBLCLICK_PROCS = {}   # hwnd -> callback vivo del subclass (Windows)
_SUBCLASS_PROC_TYPE = None
_def_subclass_proc = None   # puntero resuelto una sola vez (camino caliente)


def _ncl_proc(hwnd, msg, wparam, lparam, uid, ref):
    if msg == 0x00A3 and wparam == 3:   # WM_NCLBUTTONDBLCLK sobre HTSYSMENU
        return 0   # no se convierte en "cerrar"
    return _def_subclass_proc(hwnd, msg, wparam, lparam)


def _block_icon_dblclose(window):
    """Evita que el doble clic en el icono de la barra de título cierre
    la ventana. El botón ✕ y Alt+F4 siguen cerrando normalmente.
    Se instala una sola vez por ventana."""
    global _SUBCLASS_PROC_TYPE, _def_subclass_proc
    if os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import wintypes

        if _SUBCLASS_PROC_TYPE is None:
            _SUBCLASS_PROC_TYPE = ctypes.WINFUNCTYPE(
                ctypes.c_ssize_t, wintypes.HWND, ctypes.c_uint,
                wintypes.WPARAM, ctypes.c_ssize_t, ctypes.c_uint,
                ctypes.c_size_t)
            comctl32 = ctypes.windll.comctl32
            comctl32.DefSubclassProc.restype = ctypes.c_ssize_t
            comctl32.DefSubclassProc.argtypes = [wintypes.HWND, ctypes.c_uint,
                                                 wintypes.WPARAM,
                                                 ctypes.c_ssize_t]
            _def_subclass_proc = comctl32.DefSubclassProc
            comctl32.SetWindowSubclass.restype = ctypes.c_int
            comctl32.SetWindowSubclass.argtypes = [
                wintypes.HWND, _SUBCLASS_PROC_TYPE, ctypes.c_uint,
                ctypes.c_size_t]

        user32 = ctypes.windll.user32
        hwnd = user32.GetParent(window.winfo_id())
        if hwnd in _DBLCLICK_PROCS:
            return                     # ya está protegida
        callback = _SUBCLASS_PROC_TYPE(_ncl_proc)
        if ctypes.windll.comctl32.SetWindowSubclass(hwnd, callback, 1, 0):
            _DBLCLICK_PROCS[hwnd] = callback
    except Exception:
        pass


class Panel(tk.Tk):
    def __init__(self):
        super().__init__()
        self._icon_cache = {}
        self.title("Click to copy")
        self._app_icon = None
        try:
            png_path = os.path.join(RES_DIR, "clicktocopy.png")
            if os.path.exists(png_path):
                self._app_icon = tk.PhotoImage(file=png_path)
                self.iconphoto(True, self._app_icon)
        except Exception:
            pass
        self.geometry("580x800")
        self.minsize(460, 400)
        self.groups = load_data()
        self.reveal = False
        self.pinned = False
        self.collapsed = {g["name"] for g in self.groups}  # todos plegados
        self.editing = None             # (gi, ri) cuando se edita una fila
        self.theme = load_theme()

        global PIXEL_FONTS_OK
        fams = set(tkfont.families())
        PIXEL_FONTS_OK = ("Press Start 2P" in fams and "VT323" in fams)

        self._apply_theme()

        self.bind("<Escape>", lambda e: self.cancel_edit())
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.row_name_entry.focus_set()

    # ================= UI =================
    def _build_header(self):
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", padx=14, pady=(14, 2))
        # Botón de tema arriba a la derecha: muestra el icono del tema
        # al que cambiaría (pixelart = ir a pixel, ventana = ir a clásico)
        target = "pixelart" if self.theme == "normal" else "window"
        self.theme_btn = tk.Label(head, text="Tema", compound="left",
                                  image=self._icon(target, ACCENT),
                                  bg=CARD, fg=FG, font=FONT_SMALL,
                                  padx=12, pady=5, cursor="hand2")
        self.theme_btn.pack(side="right")
        self.theme_btn.bind("<Button-1>", lambda e: self.toggle_theme())
        self.theme_btn.bind("<Enter>", lambda e, w=self.theme_btn:
                            w.configure(image=self._icon(target, FG),
                                        bg=CARD_HOV))
        self.theme_btn.bind("<Leave>", lambda e, w=self.theme_btn:
                            w.configure(image=self._icon(target, ACCENT),
                                        bg=CARD))
        self.theme_btn.bind("<Button-1>", lambda e: self.toggle_theme())
        self.theme_btn.bind("<Enter>", lambda e, w=self.theme_btn:
                            w.configure(image=self._icon(target, FG)))
        self.theme_btn.bind("<Leave>", lambda e, w=self.theme_btn:
                            w.configure(image=self._icon(target, ACCENT)))
        tk.Label(head, text="Panel de copiado", bg=BG, fg=FG,
                 font=FONT_TITLE, anchor="w").pack(side="left")
        tk.Label(head, text="  click en un campo para copiarlo", bg=BG,
                 fg=MUTED, font=FONT_SMALL, anchor="w").pack(side="left",
                                                            pady=(3, 0))

    def _entry(self, parent):
        return tk.Entry(parent, bg=CARD, fg=FG, insertbackground=FG,
                        relief="flat", font=FONT, highlightthickness=self.bd,
                        highlightbackground=STROKE, highlightcolor=ACCENT)

    def _apply_theme(self):
        """Aplica el tema actual: reasigna colores/fuentes y reconstruye."""
        global BG, BG_SOFT, CARD, CARD_HOV, FLASH, STROKE, FG, MUTED
        global ACCENT, ACCENT_HV, RED, VAL_FG, GROUP_COLORS
        global FONT, FONT_BOLD, FONT_SMALL, FONT_TITLE
        t = THEMES[self.theme]
        for key, val in t.items():
            if key != "BORDER":
                globals()[key] = val
        self.bd = t["BORDER"]
        fs = dict(FONT_SETS[self.theme])
        if self.theme == "pixel" and not PIXEL_FONTS_OK:
            fs = FONT_SETS["normal"]     # sin TTF pixel -> fuentes normales
        FONT = fs["FONT"]
        FONT_BOLD = fs["FONT_BOLD"]
        FONT_SMALL = fs["FONT_SMALL"]
        FONT_TITLE = fs["FONT_TITLE"]
        self._icon_cache.clear()

        self.configure(bg=BG)   # evita bordes claros en los huecos de la raíz

        for w in self.winfo_children():
            w.destroy()
        self.editing = None
        self._form_open = False
        self._build_header()
        self._build_form()
        self._build_controls()
        self._build_list()
        self._build_statusbar()

        # reflejar el estado de revelar/fijar en los botones reconstruidos
        self.eye_btn.configure(
            text="Ocultar" if self.reveal else "Mostrar",
            image=self._icon("eye_off" if self.reveal else "eye",
                             "#ffffff" if self.reveal else FG),
            bg=ACCENT if self.reveal else CARD,
            fg="white" if self.reveal else FG)
        self.pin_btn.configure(
            bg=ACCENT if self.pinned else CARD,
            fg="white" if self.pinned else FG,
            image=self._icon("anchor", "#ffffff" if self.pinned else FG))

        self.update_idletasks()
        try:
            if self._app_icon is not None:
                self.iconphoto(True, self._app_icon)
        except tk.TclError:
            pass
        if self.pinned:
            _set_titlebar(self, ACCENT, "#ffffff")
        else:
            _set_titlebar(self, BG, FG)
        _block_icon_dblclose(self)

        self.refresh_form_groups()
        self.add_field()
        self.refresh_list()

    def toggle_theme(self):
        self.theme = "normal" if self.theme == "pixel" else "pixel"
        save_theme(self.theme)
        self._apply_theme()
        self.set_status(f"Tema {self.theme} aplicado")

    def _icon(self, name, color=FG, scale=2):
        """Devuelve un icono cacheado: SVG suave o pixel según el tema."""
        key = (self.theme, name, color, scale)
        if key not in self._icon_cache:
            if self.theme == "normal" and tksvg is not None:
                svg = ICONS[name].replace("currentColor", color)
                self._icon_cache[key] = tksvg.SvgImage(
                    data=svg, scaletowidth=max(10, 10 * scale))
            else:
                self._icon_cache[key] = _render_pixel_icon(name, color,
                                                           scale)
        return self._icon_cache[key]

    def _build_form(self):
        # --- Barra plegable del formulario ---
        toggle = tk.Frame(self, bg=BG, cursor="hand2")
        toggle.pack(fill="x", padx=10, pady=(6, 0))
        self._form_open = False
        plus = self._icon("plus", ACCENT)
        plus_lbl = tk.Label(toggle, image=plus, bg=BG, cursor="hand2")
        plus_lbl.pack(side="left")
        text_lbl = tk.Label(toggle, text="Agregar elemento", bg=BG, fg=FG,
                            font=FONT_BOLD, anchor="w", cursor="hand2")
        text_lbl.pack(side="left", padx=(8, 0))
        self.form_chev = tk.Label(toggle, bg=BG, fg=MUTED, cursor="hand2")
        self.form_chev.pack(side="right")
        for w in (toggle, plus_lbl, text_lbl, self.form_chev):
            w.bind("<Button-1>", lambda e: self.toggle_form())

        form = tk.Frame(self, bg=BG_SOFT, highlightthickness=self.bd,
                        highlightbackground=STROKE)
        self.form_frame = form
        if self._form_open:
            form.pack(fill="x", padx=10, pady=(6, 8), ipadx=6, ipady=8)
        self._update_form_chevron()

        tk.Label(form, text="Nombre de fila (opcional)", bg=BG_SOFT,
                 fg=MUTED, font=FONT_SMALL, anchor="w").pack(
            fill="x", padx=8)
        self.row_name_entry = self._entry(form)
        self.row_name_entry.pack(fill="x", padx=8, pady=(2, 8))

        # --- Campos dinámicos ---
        self.fields_frame = tk.Frame(form, bg=BG_SOFT)
        self.fields_frame.pack(fill="x", padx=8)
        self.field_rows = []   # [{"frame", "value", "del"}]

        add_f = tk.Button(form, text="Campo",
                          image=self._icon("plus", ACCENT), compound="left",
                          command=self.add_field, bg=CARD, fg=ACCENT,
                          font=FONT_SMALL, activebackground=CARD_HOV,
                          activeforeground=ACCENT, relief="flat",
                          cursor="hand2", padx=10, pady=3,
                          bd=0, highlightthickness=0)
        add_f.pack(anchor="w", padx=8, pady=(8, 4))

        # --- Pie: grupo + acciones ---
        foot = tk.Frame(form, bg=BG_SOFT)
        foot.pack(fill="x", padx=8, pady=(10, 2))
        tk.Label(foot, text="Grupo", bg=BG_SOFT, fg=MUTED,
                 font=FONT_SMALL, anchor="w").pack(side="left")

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.style.configure("Dark.TCombobox", fieldbackground=CARD,
                             background=CARD, foreground=FG,
                             arrowcolor=MUTED, bordercolor=STROKE,
                             lightcolor=STROKE, darkcolor=STROKE,
                             borderwidth=0, relief="flat")
        self.style.map("Dark.TCombobox",
                       fieldbackground=[("readonly", CARD)],
                       foreground=[("readonly", FG)])
        self.option_add("*TCombobox*Listbox.background", CARD)
        self.option_add("*TCombobox*Listbox.foreground", FG)
        self.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.option_add("*TCombobox*Listbox.selectForeground", "white")

        self.group_combo = ttk.Combobox(foot, style="Dark.TCombobox",
                                        font=FONT, width=16)
        self.group_combo.pack(side="left", padx=(6, 0))

        self.new_group_btn = tk.Button(
            foot, image=self._icon("plus", ACCENT), command=self.add_group,
            bg=CARD, activebackground=CARD_HOV, relief="flat",
            cursor="hand2", padx=4, pady=2, bd=0, highlightthickness=0)
        self.new_group_btn.pack(side="left", padx=(6, 0))

        self.add_btn = tk.Button(foot, text="Agregar", command=self.save_form,
                                 bg=ACCENT, fg="white", font=FONT_BOLD,
                                 activebackground=ACCENT_HV,
                                 activeforeground="white", relief="flat",
                                 cursor="hand2", padx=12, bd=0,
                                 highlightthickness=0)
        self.add_btn.pack(side="right")

        self.cancel_btn = tk.Button(foot, text="✕", command=self.cancel_edit,
                                    bg=CARD, fg=MUTED, font=FONT,
                                    activebackground=CARD_HOV,
                                    activeforeground=FG, relief="flat",
                                    cursor="hand2", padx=6, bd=0,
                                    highlightthickness=0)
        self.cancel_btn.pack(side="right", padx=(0, 6))
        self.cancel_btn.pack_forget()   # visible solo al editar

    def add_field(self, value=""):
        """Agrega una línea con un solo campo (el valor) al formulario."""
        line = tk.Frame(self.fields_frame, bg=BG_SOFT)
        line.pack(fill="x", pady=3)
        val_e = self._entry(line)
        val_e.pack(side="left", fill="x", expand=1)
        if value:
            val_e.insert(0, value)

        del_b = tk.Button(line, image=self._icon("trash", MUTED),
                          command=None, bg=BG_SOFT, activebackground=BG_SOFT,
                          relief="flat", cursor="hand2", padx=2, pady=2,
                          bd=0, highlightthickness=0)
        del_b.pack(side="left", padx=(10, 0))

        ref = {"frame": line, "value": val_e, "del": del_b}
        del_b.configure(command=lambda r=ref: self.remove_field(r))
        self.field_rows.append(ref)
        self._sync_field_delete_buttons()
        val_e.bind("<Return>", lambda e: self.save_form())
        val_e.focus_set()
        return ref

    def remove_field(self, ref):
        if len(self.field_rows) <= 1:
            self.set_status("⚠ Debe quedar al menos un campo")
            return
        if ref not in self.field_rows:
            return
        ref["frame"].destroy()
        self.field_rows.remove(ref)
        self._sync_field_delete_buttons()

    def _sync_field_delete_buttons(self):
        can_delete = len(self.field_rows) > 1
        for ref in self.field_rows:
            ref["del"].configure(
                state="normal" if can_delete else "disabled",
                image=self._icon("trash", MUTED if can_delete else STROKE))

    def toggle_form(self):
        """Muestra u oculta la sección de agregar (como los grupos)."""
        self._form_open = not self._form_open
        if self._form_open:
            self.form_frame.pack(fill="x", padx=10, pady=(6, 8),
                                 ipadx=6, ipady=8,
                                 before=self.controls_bar)
        else:
            self.form_frame.pack_forget()
        self._update_form_chevron()

    def _update_form_chevron(self):
        self.form_chev.configure(
            image=self._icon("chevron_down" if self._form_open
                             else "chevron_up", MUTED))

    # ================= Controles =================
    def _build_controls(self):
        self.controls_bar = tk.Frame(self, bg=BG)
        self.controls_bar.pack(fill="x", padx=14, pady=(2, 8))
        bar = self.controls_bar

        self.pin_btn = self._tool_btn(bar, "Pin", "anchor", self.toggle_pin)
        self.pin_btn.pack(side="left")

        self.eye_btn = self._tool_btn(bar, "Mostrar", "eye", self.toggle_reveal)
        self.eye_btn.pack(side="left", padx=(8, 0))

        self.expand_btn = self._tool_btn(bar, "Expandir todos",
                                         "chevron_down",
                                         self.toggle_expand_all)
        self.expand_btn.pack(side="right")

        self._sync_expand_btn()

    def _tool_btn(self, parent, text, icon, cmd):
        return tk.Button(parent, text=text, image=self._icon(icon, FG),
                         compound="left", command=cmd, bg=CARD, fg=FG,
                         font=FONT_SMALL, activebackground=CARD_HOV,
                         activeforeground=FG, relief="flat", cursor="hand2",
                         padx=12, pady=5, bd=0, highlightthickness=0)

    def _build_list(self):
        wrap = tk.Frame(self, bg=BG)
        wrap.pack(fill="both", expand=True, padx=10, pady=(2, 6))
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0, bd=0)
        self.list_frame = tk.Frame(self.canvas, bg=BG)
        self.scroll = tk.Scrollbar(wrap, orient="vertical", width=10,
                                   command=self.canvas.yview)
        self.scroll.configure(troughcolor=BG, background=CARD,
                              activebackground=CARD_HOV, bd=0, relief="flat")
        self.canvas.configure(yscrollcommand=self.scroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid(row=0, column=1, sticky="ns")
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.list_frame, anchor="nw")

        self.list_frame.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self.canvas_window, width=e.width))
        self.bind_all("<MouseWheel>",
                      lambda e: self.canvas.yview_scroll(-e.delta // 120,
                                                         "units"))

    def _build_statusbar(self):
        self.status = tk.Label(self, text="Listo", bg=BG, fg=MUTED,
                               font=FONT_SMALL, anchor="w")
        self.status.pack(fill="x", side="bottom", padx=14, pady=(0, 10))

    # ================= Acciones =================
    def refresh_form_groups(self):
        names = [g["name"] for g in self.groups]
        self.group_combo.configure(values=names)
        if not self.group_combo.get() and names:
            self.group_combo.current(0)

    def save_form(self):
        row_name = self.row_name_entry.get().strip()
        fields = []
        for ref in self.field_rows:
            value = ref["value"].get().strip()
            if value:   # se ignoran líneas de campo sin valor
                fields.append({"name": "", "value": value})
        if not fields:
            self.set_status("⚠ Agrega al menos un valor")
            return
        group = self.group_combo.get().strip() or "General"

        if self.editing is not None:
            gi, ri = self.editing
            old_g = self.groups[gi]["name"]
            self.groups[gi]["rows"][ri] = {"name": row_name,
                                           "fields": fields}
            if old_g != group:  # mover a otro grupo
                row = self.groups[gi]["rows"].pop(ri)
                self._group_for(group)["rows"].append(row)
                if not self.groups[gi]["rows"]:
                    del self.groups[gi]
                    self.refresh_form_groups()
            self.editing = None
            self.clear_form()
            self.add_btn.configure(text="Agregar")
            self.cancel_btn.pack_forget()
            save_data(self.groups)
            self.refresh_list()
            self.set_status(f'✓ Actualizada la fila "{row_name or "sin nombre"}"')
            return

        self._group_for(group)["rows"].append({"name": row_name,
                                               "fields": fields})
        save_data(self.groups)
        self.refresh_form_groups()
        self.clear_form()
        self.refresh_list()
        self.set_status(f'✓ Agregada la fila en {group}')

    def _group_for(self, name):
        for g in self.groups:
            if g["name"] == name:
                return g
        g = {"name": name, "rows": []}
        self.groups.append(g)
        return g

    def clear_form(self, blank=True):
        self.row_name_entry.delete(0, "end")
        for ref in list(self.field_rows):
            ref["frame"].destroy()
        self.field_rows.clear()
        if blank:
            self.add_field()

    def cancel_edit(self):
        if self.editing is None:
            return
        self.editing = None
        self.clear_form()
        self.add_btn.configure(text="Agregar")
        self.cancel_btn.pack_forget()
        self.row_name_entry.focus_set()
        self.set_status("Edición cancelada")

    def start_edit(self, gi, ri):
        if self.editing is not None:
            self.editing = None
        if not self._form_open:
            self.toggle_form()
        self.editing = (gi, ri)
        row = self.groups[gi]["rows"][ri]
        self.clear_form(blank=False)
        if row.get("name"):
            self.row_name_entry.insert(0, row["name"])
        for f in row["fields"]:
            self.add_field(f.get("value", ""))
        self.group_combo.set(self.groups[gi]["name"])
        self.add_btn.configure(text="Guardar cambios")
        self.cancel_btn.pack(side="right", padx=(0, 6), before=self.add_btn)
        self.row_name_entry.focus_set()
        self.set_status(f'✎ Editando fila "{row.get("name") or "sin nombre"}"'
                        f' · Enter guarda, Esc cancela')

    def delete_row(self, gi, ri):
        if gi >= len(self.groups) or ri >= len(self.groups[gi]["rows"]):
            return
        row = self.groups[gi]["rows"].pop(ri)
        if not self.groups[gi]["rows"]:
            del self.groups[gi]
            self.refresh_form_groups()
        if self.editing == (gi, ri):
            self.editing = None
            self.clear_form()
            self.add_btn.configure(text="Agregar")
            self.cancel_btn.pack_forget()
        save_data(self.groups)
        self.refresh_list()
        self.set_status(f'🗑 Eliminada la fila "{row.get("name") or "sin nombre"}"')

    def delete_group(self, gi):
        g = self.groups[gi]
        msg = (f'¿Eliminar el grupo "{g["name"]}" con sus '
               f'{len(g["rows"])} filas?'
               if g["rows"] else f'¿Eliminar el grupo vacío "{g["name"]}"?')
        if not messagebox.askyesno("Eliminar grupo", msg):
            return
        del self.groups[gi]
        self.collapsed.discard(g["name"])
        save_data(self.groups)
        self.refresh_form_groups()
        self.refresh_list()
        self.set_status(f'🗑 Grupo "{g["name"]}" eliminado')

    def ask_text(self, title, label, initial=""):
        """Diálogo modal pequeño con el tema del panel. Devuelve str o None."""
        dlg = tk.Toplevel(self)
        dlg.title(title)
        dlg.configure(bg=BG_SOFT)
        dlg.resizable(False, False)
        dlg.transient(self)

        tk.Label(dlg, text=label, bg=BG_SOFT, fg=MUTED, font=FONT_SMALL,
                 anchor="w").pack(fill="x", padx=14, pady=(14, 4))
        ent = self._entry(dlg)
        ent.pack(fill="x", padx=14)
        if initial:
            ent.insert(0, initial)

        result = {"text": None}

        def ok(event=None):
            result["text"] = ent.get().strip()
            dlg.destroy()

        def cancel(event=None):
            result["text"] = None
            dlg.destroy()

        btns = tk.Frame(dlg, bg=BG_SOFT)
        btns.pack(fill="x", padx=14, pady=(12, 14))
        tk.Button(btns, text="Guardar", command=ok, bg=ACCENT, fg="white",
                  font=FONT_BOLD, activebackground=ACCENT_HV,
                  activeforeground="white", relief="flat", cursor="hand2",
                  padx=14, pady=4, bd=0,
                  highlightthickness=0).pack(side="right")
        tk.Button(btns, text="Cancelar", command=cancel, bg=CARD, fg=MUTED,
                  font=FONT, activebackground=CARD_HOV, activeforeground=FG,
                  relief="flat", cursor="hand2", padx=12, pady=4, bd=0,
                  highlightthickness=0).pack(side="right", padx=(0, 8))

        ent.bind("<Return>", ok)
        dlg.bind("<Escape>", cancel)
        dlg.protocol("WM_DELETE_WINDOW", cancel)

        dlg.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dlg.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dlg.winfo_height()) // 3
        dlg.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        dlg.wait_visibility()
        dlg.grab_set()
        ent.focus_set()
        dlg.wait_window()
        return result["text"]

    def add_group(self):
        name = self.ask_text("Nuevo grupo", "Nombre del grupo")
        if not name:
            return
        if any(g["name"].lower() == name.lower() for g in self.groups):
            self.set_status(f'⚠ Ya existe el grupo "{name}"')
            return
        self._group_for(name)
        save_data(self.groups)
        self.refresh_form_groups()
        self.group_combo.set(name)
        self.refresh_list()
        self.set_status(f'✓ Grupo "{name}" creado')

    def rename_group(self, gi):
        old = self.groups[gi]["name"]
        name = self.ask_text("Renombrar grupo", "Nuevo nombre", initial=old)
        if not name or name == old:
            return
        if any(g["name"].lower() == name.lower() for g in self.groups):
            self.set_status(f'⚠ Ya existe el grupo "{name}"')
            return
        self.groups[gi]["name"] = name
        if old in self.collapsed:
            self.collapsed.discard(old)
            self.collapsed.add(name)
        save_data(self.groups)
        self.refresh_form_groups()
        if self.group_combo.get() == old:
            self.group_combo.set(name)
        self.refresh_list()
        self.set_status(f'✓ Grupo renombrado a "{name}"')

    def toggle_group(self, gi):
        name = self.groups[gi]["name"]
        if name in self.collapsed:
            # tipo acordeón: abre este y contrae el resto
            self.collapsed = {g["name"] for g in self.groups}
            self.collapsed.discard(name)
        else:
            self.collapsed.add(name)
        self._sync_expand_btn()
        self.refresh_list()

    def toggle_expand_all(self):
        """Abre o cierra todos los grupos de golpe."""
        names = {g["name"] for g in self.groups}
        if names and all(n not in self.collapsed for n in names):
            self.collapsed = set(names)     # contraer todos
        else:
            self.collapsed = set()          # expandir todos
        self._sync_expand_btn()
        self.refresh_list()

    def _sync_expand_btn(self):
        """Ajusta el texto/icono del botón según el estado de los grupos."""
        names = [g["name"] for g in self.groups]
        all_open = bool(names) and all(n not in self.collapsed
                                       for n in names)
        icon = "chevron_up" if all_open else "chevron_down"
        label = "Contraer todos" if all_open else "Expandir todos"
        self.expand_btn.configure(text=label, image=self._icon(icon, FG))

    def toggle_pin(self):
        self.pinned = getattr(self, "pinned", False)
        self.pinned = not self.pinned
        self.attributes("-topmost", self.pinned)
        _set_titlebar(self, ACCENT if self.pinned else BG,
                      "#ffffff" if self.pinned else FG)
        self.pin_btn.configure(
            bg=ACCENT if self.pinned else CARD,
            fg="white" if self.pinned else FG,
            image=self._icon("anchor", "#ffffff" if self.pinned else FG))

    def toggle_reveal(self):
        self.reveal = not self.reveal
        self.eye_btn.configure(
            text="Ocultar" if self.reveal else "Mostrar",
            image=self._icon("eye_off" if self.reveal else "eye",
                             "#ffffff" if self.reveal else FG),
            bg=ACCENT if self.reveal else CARD,
            fg="white" if self.reveal else FG)
        self.refresh_list()

    def copy_field(self, gi, ri, fi, widget):
        if gi >= len(self.groups) or ri >= len(self.groups[gi]["rows"]):
            return
        fields = self.groups[gi]["rows"][ri]["fields"]
        if fi >= len(fields):
            return
        field = fields[fi]
        label = field.get("name") or f'campo {fi + 1}'
        try:
            copy_to_clipboard(field["value"])
        except Exception as e:
            self.set_status(f"✗ No se pudo copiar: {e}")
            return
        self.set_status(f'✓ Copiado {label}')
        self._flash(widget)

    def _flash(self, widget):
        if not widget.winfo_exists():
            return
        _set_bg(widget, FLASH)
        self.after(320, lambda: self._unflash(widget))

    def _unflash(self, widget):
        if not widget.winfo_exists():
            return
        _set_bg(widget, CARD)

    def set_status(self, text):
        self.status.configure(text=text)

    # ================= Render =================
    def refresh_list(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        if not self.groups or all(not g["rows"] for g in self.groups):
            tk.Label(self.list_frame, image=self._icon("copy", MUTED, scale=3),
                     bg=BG).pack(pady=(48, 8))
            tk.Label(self.list_frame, text="Sin filas todavía.\n\n"
                     "Arriba: nombre de fila opcional y uno o más valores\n"
                     "(+ Campo agrega más). Con + Grupo creas uno nuevo.",
                     bg=BG, fg=MUTED, font=FONT_SMALL,
                     justify="center").pack(pady=(0, 48))
            return

        for gi, group in enumerate(self.groups):
            if not group["rows"]:
                continue
            color = GROUP_COLORS[gi % len(GROUP_COLORS)]
            open_ = group["name"] not in self.collapsed

            box = tk.Frame(self.list_frame, bg=CARD, highlightthickness=self.bd,
                           highlightbackground=STROKE)
            box.pack(fill="x", pady=6)

            head = tk.Frame(box, bg=CARD, cursor="hand2")
            head.pack(fill="x")
            inner = tk.Frame(head, bg=CARD)
            inner.pack(fill="x", padx=12, pady=8)

            if self.theme == "pixel":
                dot = tk.Label(inner, image=self._icon("circle", color,
                                                       scale=1), bg=CARD)
            else:
                dot = tk.Label(inner, text="●", bg=CARD, fg=color,
                               font=("Segoe UI", 10))
            dot.pack(side="left")
            tk.Label(inner, text=group["name"].upper(), bg=CARD, fg=FG,
                     font=FONT_BOLD, anchor="w").pack(side="left",
                                                      padx=(8, 6))
            tk.Label(inner, text=str(len(group["rows"])), bg=CARD, fg=MUTED,
                     font=FONT_SMALL).pack(side="left")
            chev = self._icon("chevron_down" if open_ else "chevron_up",
                              MUTED)
            tk.Label(inner, image=chev, bg=CARD,
                     cursor="hand2").pack(side="right", padx=4)

            trash = self._icon("trash", MUTED)
            del_g = tk.Label(inner, image=trash, bg=CARD, cursor="hand2")
            del_g.pack(side="right", padx=4)

            pencil = self._icon("pencil", MUTED)
            ren_g = tk.Label(inner, image=pencil, bg=CARD, cursor="hand2")
            ren_g.pack(side="right", padx=4)

            for w in (head, inner) + tuple(inner.winfo_children()):
                if w is not del_g and w is not ren_g:
                    w.bind("<Button-1>", lambda e, i=gi: self.toggle_group(i))
            ren_g.bind("<Button-1>", lambda e, i=gi: self.rename_group(i))
            del_g.bind("<Button-1>", lambda e, i=gi: self.delete_group(i))
            ren_g.bind("<Enter>", lambda e, w=ren_g: w.configure(
                image=self._icon("pencil", FG)))
            ren_g.bind("<Leave>", lambda e, w=ren_g: w.configure(
                image=self._icon("pencil", MUTED)))
            del_g.bind("<Enter>", lambda e, w=del_g: w.configure(
                image=self._icon("trash", RED)))
            del_g.bind("<Leave>", lambda e, w=del_g: w.configure(
                image=self._icon("trash", MUTED)))

            if not open_:
                continue

            sep = tk.Frame(box, bg=STROKE, height=self.bd, bd=0,
                           highlightthickness=0)
            sep.pack(fill="x")

            for ri, row in enumerate(group["rows"]):
                self._build_row(box, gi, ri, row, color)

        # Asegura que el área de scroll cubra todo el contenido recién creado
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _build_row(self, parent, gi, ri, row, color):
        card = tk.Frame(parent, bg=CARD)
        card.pack(fill="x", padx=8, pady=2)
        card.columnconfigure(1, weight=1)

        strip = tk.Frame(card, bg=color, width=3)
        strip.grid(row=0, column=0, rowspan=2, sticky="nsw")

        body = tk.Frame(card, bg=CARD)
        body.grid(row=0, column=1, sticky="nsew")

        pencil = self._icon("pencil", MUTED)
        edit_b = tk.Button(card, image=pencil, bg=CARD, relief="flat",
                           bd=0, highlightthickness=0, cursor="hand2",
                           activebackground=CARD_HOV, padx=2, pady=4,
                           command=lambda: self.start_edit(gi, ri))
        edit_b.grid(row=0, column=2, sticky="e", padx=(0, 8))
        edit_b.bind("<Enter>", lambda e, b=edit_b: b.configure(
            image=self._icon("pencil", FG)))
        edit_b.bind("<Leave>", lambda e, b=edit_b: b.configure(
            image=self._icon("pencil", MUTED)))

        trash = self._icon("trash", MUTED)
        del_r = tk.Button(card, image=trash, bg=CARD, relief="flat",
                          bd=0, highlightthickness=0, cursor="hand2",
                          activebackground=CARD_HOV, padx=2, pady=4,
                          command=lambda: self.delete_row(gi, ri))
        del_r.grid(row=0, column=3, sticky="e", padx=(0, 10))
        del_r.bind("<Enter>", lambda e, b=del_r: b.configure(
            image=self._icon("trash", RED)))
        del_r.bind("<Leave>", lambda e, b=del_r: b.configure(
            image=self._icon("trash", MUTED)))

        if row.get("name"):
            tk.Label(body, text=row["name"], bg=CARD, fg=FG, font=FONT_SMALL,
                     anchor="w").pack(fill="x", padx=10, pady=(6, 0))

        fields_frame = tk.Frame(body, bg=CARD)
        fields_frame.pack(fill="both", expand=True, padx=8, pady=6)

        fields = row["fields"]
        ncols = min(MAX_COLS, len(fields))
        for c in range(ncols):
            fields_frame.columnconfigure(c, weight=1, uniform="blk")

        for fi, field in enumerate(fields):
            blk = tk.Frame(fields_frame, bg=CARD, cursor="hand2",
                           highlightthickness=1, highlightbackground=STROKE)
            blk.grid(row=fi // MAX_COLS, column=fi % MAX_COLS,
                     sticky="nsew", padx=4, pady=3)

            name = field.get("name")
            value = field["value"] if self.reveal else masked(field["value"])
            if name:
                tk.Label(blk, text=name, bg=CARD, fg=MUTED, font=FONT_SMALL,
                         anchor="w").pack(fill="x", padx=12, pady=(6, 0))
                pady_val = (0, 8)
            else:
                pady_val = (7, 8)
            tk.Label(blk, text=value, bg=CARD, fg=VAL_FG,
                     font=FONT_BOLD if not name else FONT, anchor="w",
                     ).pack(fill="x", padx=12, pady=pady_val)

            def on_copy(event, g=gi, r=ri, f=fi, b=blk):
                self.copy_field(g, r, f, b)

            def on_enter(event, b=blk):
                _set_bg(b, CARD_HOV)

            def on_leave(event, b=blk):
                _set_bg(b, CARD)

            for w in (blk,) + tuple(blk.winfo_children()):
                w.bind("<Button-1>", on_copy)
                w.bind("<Enter>", on_enter)
                w.bind("<Leave>", on_leave)

    def _on_close(self):
        save_data(self.groups)
        self.destroy()


def main():
    if pyperclip is None:
        print("[Aviso] pyperclip no está instalado; se usará el portapapeles "
              "de Tkinter (funciona igual).\n"
              "  Para instalarlo: pip install pyperclip\n")
    app = Panel()
    app.mainloop()


if __name__ == "__main__":
    main()

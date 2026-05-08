import tkinter as tk
import pystray
from PIL import Image
import threading

root = tk.Tk()
root.withdraw()

def show_window(icon, item):
    win = tk.Toplevel(root)
    tk.Label(win, text="Hello").pack()

icon = pystray.Icon("test", Image.new("RGBA", (16,16), "blue"), menu=pystray.Menu(
    pystray.MenuItem("Show Window", show_window),
    pystray.MenuItem("Quit", lambda i, item: i.stop())
))

icon.run()

import os
import threading
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk
from plyer import notification

from launcher_core import APP_ICON, BG_IMAGE, LAUNCHER_NAME, install as install_launcher, launch as launch_launcher


def ui_log(text):
    root.after(0, lambda: _ui_log(text))


def _ui_log(text):
    console.config(state="normal")
    console.insert("end", text + "\n")
    console.see("end")
    console.config(state="disabled")


def ui_status(text):
    root.after(0, lambda: status.config(text=text))


def threaded(func):
    threading.Thread(target=func, daemon=True).start()


def install():
    try:
        install_launcher(on_log=ui_log, on_status=ui_status)
        notification.notify(title=LAUNCHER_NAME, message="Mods installes")
    except Exception as exc:
        ui_log(str(exc))
        ui_status("Erreur")


def launch():
    try:
        pseudo = username.get().strip() or "Player"
        launch_launcher(username=pseudo, on_log=ui_log, on_status=ui_status)
        notification.notify(title=LAUNCHER_NAME, message="Bon jeu !")
    except Exception as exc:
        ui_log(str(exc))
        ui_status("Erreur lancement")


root = tk.Tk()
root.title(LAUNCHER_NAME)
root.geometry("700x520")

if os.path.exists(APP_ICON):
    root.iconbitmap(APP_ICON)

canvas = tk.Canvas(root)
canvas.pack(fill="both", expand=True)

bg_img = None
bg_photo = None


def resize_bg(event):
    global bg_img, bg_photo
    if os.path.exists(BG_IMAGE):
        bg_img = Image.open(BG_IMAGE).resize((event.width, event.height))
        bg_photo = ImageTk.PhotoImage(bg_img)
        canvas.create_image(0, 0, image=bg_photo, anchor="nw")


root.bind("<Configure>", resize_bg)

username = tk.Entry(root, width=30)
install_btn = ttk.Button(root, text="Installer", command=lambda: threaded(install))
play_btn = ttk.Button(root, text="Jouer", command=lambda: threaded(launch))
status = tk.Label(root, text="Pret")
console = tk.Text(root, height=12, state="disabled")
quit_btn = ttk.Button(root, text="Quitter", command=root.destroy)

canvas.create_window(350, 60, window=username)
canvas.create_window(350, 110, window=install_btn)
canvas.create_window(350, 160, window=play_btn)
canvas.create_window(350, 210, window=status)
canvas.create_window(350, 360, window=console)
canvas.create_window(350, 480, window=quit_btn)

root.mainloop()

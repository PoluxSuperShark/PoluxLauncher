import os
import subprocess
import threading
import requests
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from minecraft_launcher_lib import forge, command
from plyer import notification

# ================= CONFIG =================
LAUNCHER_NAME = "PoluxLauncher"
MC_VERSION = "1.20.1"
DEFAULT_SERVER = "poluxcity.falixsrv.me"
APP_ICON = "icon.ico"
BG_IMAGE = "background.png"
# JAVA_RAM = "4G"

MODS = {
    "DerexMaceMod-Balanced-1.20.1-8.1.7.2.jar": "https://poluxsupershark.net/assets/mods/DerexMaceMod-Balanced-1.20.1-8.1.7.2.jar",
    "Dynmap-3.7-beta-6-forge-1.20.jar": "https://poluxsupershark.net/assets/mods/Dynmap-3.7-beta-6-forge-1.20.jar",
    "FramedBlocks-9.4.2.jar": "https://poluxsupershark.net/mods/assets/FramedBlocks-9.4.2.jar",
    "MTR-forge-4.0.2-hotfix-1+1.20.1.jar": "https://poluxsupershark.net/assets/mods/MTR-forge-4.0.2-hotfix-1+1.20.1.jar",
    "Steam_Rails-1.6.14-beta+forge-mc1.20.1.jar": "https://poluxsupershark.net/assets/mods/Steam_Rails-1.6.14-beta+forge-mc1.20.1.jar",
    "TerraBlender-forge-1.20.1-3.0.1.10.jar": "https://poluxsupershark.net/assets/mods/TerraBlender-forge-1.20.1-3.0.1.10.jar",
    "architectury-9.2.14-forge.jar": "https://poluxsupershark.net/assets/mods/architectury-9.2.14-forge.jar",
    "balm-forge-1.20.1-7.3.37-all.jar": "https://poluxsupershark.net/assets/mods/balm-forge-1.20.1-7.3.37-all.jar",
    "cfm-forge-1.20.1-7.0.0-pre36.jar": "https://poluxsupershark.net/assets/mods/cfm-forge-1.20.1-7.0.0-pre36.jar",
    "create-1.20.1-6.0.8.jar": "https://poluxsupershark.net/mods/assets/create-1.20.1-6.0.8.jar",
    "journeymap-1.20.1-5.10.3-forge.jar": "https://poluxsupershark.net/assets/mods/journeymap-1.20.1-5.10.3-forge.jar",
    "lithostitched-forge-1.20.1-1.4.11.jar": "https://poluxsupershark.net/assets/mods/lithostitched-forge-1.20.1-1.4.11.jar",
    "mcef-forge-2.1.6-1.20.1.jar": "https://poluxsupershark.net/assets/mods/mcef-forge-2.1.6-1.20.1.jar",
    "tacz-1.20.1-1.1.7-release.jar": "https://poluxsupershark.net/assets/mods/tacz-1.20.1-1.1.7-release.jar",
    "tectonic-3.0.17-forge-1.20.1.jar": "https://poluxsupershark.net/assets/mods/tectonic-3.0.17-forge-1.20.1.jar",
    "tfmg-1.0.2e.jar": "https://poluxsupershark.net/assets/mods/tfmg-1.0.2e.jar",
    "voicechat-forge-1.20.1-2.6.11.jar": "https://poluxsupershark.net/assets/mods/voicechat-forge-1.20.1-2.6.11.jar",
    "waystones-forge-1.20.1-14.1.17.jar": "https://poluxsupershark.net/assets/mods/waystones-forge-1.20.1-14.1.17.jar",
    "webdisplays-2.0.2-1.20.1.jar": "https://poluxsupershark.net/assets/mods/webdisplays-2.0.2-1.20.1.jar",
    "worldedit-mod-7.2.15.jar": "https://poluxsupershark.net/assets/mods/worldedit-mod-7.2.15.jar"
}

# ================= PATHS =================
APPDATA = os.getenv("APPDATA")
LAUNCHER_DIR = os.path.join(APPDATA, LAUNCHER_NAME)
MC_DIR = os.path.join(LAUNCHER_DIR, "minecraft")
MODS_DIR = os.path.join(MC_DIR, "mods")
VERSIONS_DIR = os.path.join(MC_DIR, "versions")

os.makedirs(MODS_DIR, exist_ok=True)
os.makedirs(VERSIONS_DIR, exist_ok=True)

# ================= UI HELPERS =================
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

# ================= DOWNLOAD =================
def download(url, path):
    r = requests.get(url, stream=True)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0))
    done = 0

    with open(path, "wb") as f:
        for chunk in r.iter_content(8192):
            if chunk:
                f.write(chunk)
                done += len(chunk)
                if total:
                    percent = done / total * 100
                    ui_status(f"Téléchargement {percent:.1f}%")

# ================= INSTALL =================
def install():
    try:
        ui_status("Recherche Forge...")
        forge_version = forge.find_forge_version(MC_VERSION)
        forge.install_forge_version(forge_version, MC_DIR)
        ui_log(f"Forge installé : {forge_version}")

        ui_status("Mods...")
        for name, url in MODS.items():
            dest = os.path.join(MODS_DIR, name)
            if os.path.exists(dest):
                continue
            ui_log(f"Téléchargement de {name}")
            download(url, dest)

        ui_status("Installation terminée")
        notification.notify(title=LAUNCHER_NAME, message="Mods installés")

    except Exception as e:
        ui_log(str(e))
        ui_status("Erreur")

# ================= FORGE DETECT =================
def find_forge():
    for v in os.listdir(VERSIONS_DIR):
        if v.startswith(f"{MC_VERSION}-forge"):
            return v
    return None

# ================= LAUNCH =================
def launch():
    try:
        pseudo = username.get().strip() or "Player"
        version = find_forge()

        if not version:
            ui_status("Forge manquant")
            return

        opts = {
            "username": pseudo,
            "uuid": "00000000000000000000000000000000",
            "token": "",
            # "jvmArguments": [f"-Xmx{JAVA_RAM}"]
        }

        cmd = command.get_minecraft_command(version, MC_DIR, opts)
        cmd += ["--server", DEFAULT_SERVER]

        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)

        ui_status("Minecraft lancé")
        notification.notify(title=LAUNCHER_NAME, message="Bon jeu !")

    except Exception as e:
        ui_log(str(e))
        ui_status("Erreur lancement")

# ================= GUI =================
root = tk.Tk()
root.title(LAUNCHER_NAME)
root.geometry("700x520")

if os.path.exists(APP_ICON):
    root.iconbitmap(APP_ICON)

canvas = tk.Canvas(root)
canvas.pack(fill="both", expand=True)

bg_img = None
bg_photo = None

# Resize Window
def resize_bg(e):
    global bg_img, bg_photo
    if os.path.exists(BG_IMAGE):
        bg_img = Image.open(BG_IMAGE).resize((e.width, e.height))
        bg_photo = ImageTk.PhotoImage(bg_img)
        canvas.create_image(0, 0, image=bg_photo, anchor="nw")

root.bind("<Configure>", resize_bg)

# Tk
username = tk.Entry(root, width=30)
install_btn = ttk.Button(root, text="Installer", command=lambda: threaded(install))
play_btn = ttk.Button(root, text="Jouer", command=lambda: threaded(launch))
status = tk.Label(root, text="Prêt")
console = tk.Text(root, height=12, state="disabled")
quit_btn = ttk.Button(root, text="Quitter", command=root.destroy)

# canvas
canvas.create_window(350, 60, window=username)
canvas.create_window(350, 110, window=install_btn)
canvas.create_window(350, 160, window=play_btn)
canvas.create_window(350, 210, window=status)
canvas.create_window(350, 360, window=console)
canvas.create_window(350, 480, window=quit_btn)

root.mainloop()

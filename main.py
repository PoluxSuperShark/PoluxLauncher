import os
import subprocess
import threading
import requests
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from minecraft_launcher_lib import forge, command
from plyer import notification
from pypresence import Presence

# ================= CONFIG =================
LAUNCHER_NAME = "PoluxLauncher"
MC_VERSION = "1.20.1"
DEFAULT_SERVER = "poluxcity.falixsrv.me"
CLIENT_ID = "1457124661719466207"

MODS = {
    "DerexMaceMod-Balanced-1.20.1-8.1.7.2.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/DerexMaceMod-Balanced-1.20.1-8.1.7.2.jar",
    "Dynmap-3.7-beta-6-forge-1.20.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/Dynmap-3.7-beta-6-forge-1.20.jar",
    "FramedBlocks-9.4.2.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/FramedBlocks-9.4.2.jar",
    "MTR-forge-4.0.2-hotfix-1+1.20.1.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/MTR-forge-4.0.2-hotfix-1+1.20.1.jar",
    "Steam_Rails-1.6.14-beta+forge-mc1.20.1.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/Steam_Rails-1.6.14-beta+forge-mc1.20.1.jar",
    "TerraBlender-forge-1.20.1-3.0.1.10.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/TerraBlender-forge-1.20.1-3.0.1.10.jar",
    "architectury-9.2.14-forge.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/architectury-9.2.14-forge.jar",
    "balm-forge-1.20.1-7.3.37-all.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/balm-forge-1.20.1-7.3.37-all.jar",
    "cfm-forge-1.20.1-7.0.0-pre36.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/cfm-forge-1.20.1-7.0.0-pre36.jar",
    "create-1.20.1-6.0.8.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/create-1.20.1-6.0.8.jar",
    "journeymap-1.20.1-5.10.3-forge.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/journeymap-1.20.1-5.10.3-forge.jar",
    "lithostitched-forge-1.20.1-1.4.11.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/lithostitched-forge-1.20.1-1.4.11.jar",
    "mcef-forge-2.1.6-1.20.1.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/mcef-forge-2.1.6-1.20.1.jar",
    "tacz-1.20.1-1.1.6-hotfix.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/tacz-1.20.1-1.1.6-hotfix.jar",
    "tectonic-3.0.17-forge-1.20.1.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/tectonic-3.0.17-forge-1.20.1.jar",
    "tfmg-1.0.2e.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/tfmg-1.0.2e.jar",
    "voicechat-forge-1.20.1-2.6.9.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/voicechat-forge-1.20.1-2.6.9.jar",
    "waystones-forge-1.20.1-14.1.17.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/waystones-forge-1.20.1-14.1.17.jar",
    "webdisplays-2.0.2-1.20.1.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/webdisplays-2.0.2-1.20.1.jar",
    "worldedit-mod-7.2.15.jar":"https://webdisplays.poluxsupershark.net/www/_files/mods/worldedit-mod-7.2.15.jar"
}

# ===== Paths =====
APPDATA = os.getenv("APPDATA")
LAUNCHER_DIR = os.path.join(APPDATA, LAUNCHER_NAME)
MC_DIR = os.path.join(LAUNCHER_DIR, "minecraft")
MODS_DIR = os.path.join(MC_DIR, "mods")
VERSIONS_DIR = os.path.join(MC_DIR, "versions")
os.makedirs(MODS_DIR, exist_ok=True)
os.makedirs(VERSIONS_DIR, exist_ok=True)

# Discord RPC
rpc = Presence(CLIENT_ID)

def start_discord(pseudo="Player"):
    try:
        rpc.connect()
        while True:
            rpc.update(
                state=f"Joue sur {DEFAULT_SERVER}",
                details=f"Pseudo : {pseudo}",
                large_image="polux_launcher",
                large_text="PoluxLauncher",
                start=time.time()
            )
            time.sleep(15)
    except:
        print("Discord non disponible")

# ===== Helpers =====
def set_status(text):
    status_label.config(text=text)
    root.update_idletasks()

def update_progress(value, maximum):
    progress_bar["maximum"] = maximum
    progress_bar["value"] = value
    root.update_idletasks()

def threaded(func):
    threading.Thread(target=func, daemon=True).start()

# ===== Core functions =====
def download_file(url, path):
    r = requests.get(url, stream=True)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0))
    downloaded = 0
    with open(path, "wb") as f:
        for chunk in r.iter_content(1024):
            f.write(chunk)
            downloaded += len(chunk)
            if total > 0:
                update_progress(downloaded, total)

def install_forge_and_mods():
    try:
        set_status("Recherche de la version Forge compatible...")
        progress_bar["value"] = 0

        forge_version = forge.find_forge_version(MC_VERSION)
        set_status(f"Installation de Forge {forge_version}...")
        forge.install_forge_version(forge_version, MC_DIR)

        set_status("Installation des mods...")
        for filename, url in MODS.items():
            path = os.path.join(MODS_DIR, filename)
            if os.path.exists(path):
                continue
            set_status(f"Téléchargement {filename}...")
            download_file(url, path)

        set_status("Installation terminée ✅")
        progress_bar["value"] = 0
        notification.notify(
            title="PoluxLauncher",
            message="Forge et mods installés ! ✅",
            app_name="PoluxLauncher",
            timeout=5
        )
    except Exception as e:
        notification.notify(
            title="PoluxLauncher",
            message=f"Erreur : {str(e)} ❌",
            app_name="PoluxLauncher",
            timeout=5
        )
        set_status("Erreur ❌")

def find_installed_forge_version():
    if not os.path.isdir(VERSIONS_DIR):
        return None
    for name in os.listdir(VERSIONS_DIR):
        if "forge" in name.lower() and MC_VERSION in name:
            return name
    return None

def launch_game():
    try:
        pseudo = username_entry.get().strip() or "Player"
        # Lancer Discord RPC
        threaded(lambda: start_discord(pseudo))

        set_status("Lancement Minecraft...")

        launch_version = find_installed_forge_version()
        if not launch_version:
            notification.notify(
                title="PoluxLauncher",
                message="Aucune version Forge installée ❌",
                app_name="PoluxLauncher",
                timeout=5
            )
            set_status("Erreur ❌")
            return

        options = {"username": pseudo}
        cmd = command.get_minecraft_command(
            version=launch_version,
            minecraft_directory=MC_DIR,
            options=options
        )
        cmd.append(f"--server {DEFAULT_SERVER}")
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)

        set_status(f"Minecraft lancé 🚀 ({pseudo})")
        notification.notify(
            title="PoluxLauncher",
            message=f"Minecraft lancé 🚀 ({pseudo})",
            app_name="PoluxLauncher",
            timeout=5
        )
    except Exception as e:
        notification.notify(
            title="PoluxLauncher",
            message=f"Erreur : {str(e)} ❌",
            app_name="PoluxLauncher",
            timeout=5
        )
        set_status("Erreur ❌")

# ===== GUI =====
root = tk.Tk()
root.title(LAUNCHER_NAME)
root.geometry("450x380")
root.resizable(False, False)

# Background
bg_image_path = os.path.join(os.path.dirname(__file__), "background.png")
if os.path.exists(bg_image_path):
    bg_img = Image.open(bg_image_path)
    bg_img = bg_img.resize((450, 380), Image.ANTIALIAS)
    bg_photo = ImageTk.PhotoImage(bg_img)
    canvas = tk.Canvas(root, width=450, height=380)
    canvas.pack(fill="both", expand=True)
    canvas.create_image(0, 0, anchor="nw", image=bg_photo)
else:
    canvas = tk.Canvas(root, width=450, height=380, bg="#1e1e1e")
    canvas.pack(fill="both", expand=True)

# Widgets
username_label = tk.Label(root, text="Pseudo :", bg="#000000", fg="#ffffff")
username_entry = tk.Entry(root, width=30)
install_btn = tk.Button(root, text="Installer Forge + Mods", width=30, height=2,
                        bg="#3a3a3a", fg="#ffffff", command=lambda: threaded(install_forge_and_mods))
play_btn = tk.Button(root, text="Jouer Minecraft", width=30, height=2,
                     bg="#3a3a3a", fg="#ffffff", command=lambda: threaded(launch_game))
status_label = tk.Label(root, text="Prêt", bg="#000000", fg="lightgray", font=("Segoe UI", 10))
progress_bar = ttk.Progressbar(root, orient="horizontal", length=350, mode="determinate")
quit_btn = tk.Button(root, text="Quitter", width=30, height=2, bg="#3a3a3a", fg="#ffffff", command=root.destroy)

# Placement
canvas.create_window(225, 40, window=username_label)
canvas.create_window(225, 70, window=username_entry)
canvas.create_window(225, 120, window=install_btn)
canvas.create_window(225, 170, window=play_btn)
canvas.create_window(225, 210, window=status_label)
canvas.create_window(225, 240, window=progress_bar)
canvas.create_window(225, 290, window=quit_btn)

root.mainloop()

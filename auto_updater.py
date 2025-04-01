import requests
import sys
import os
import tempfile
import subprocess
from config import APP_VERSION

GITHUB_USER = "milar2001"
GITHUB_REPO = "company_collector"

def get_latest_release():
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        tag = data["tag_name"]
        for asset in data["assets"]:
            if asset["name"] == "SzukajkaFirm.exe":
                return tag.lstrip("v"), asset["browser_download_url"]
    return None, None

def download_new_version(url):
    temp_exe = os.path.join(tempfile.gettempdir(), "SzukajkaFirm_new.exe")
    with requests.get(url, stream=True) as r:
        with open(temp_exe, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return temp_exe

def launch_updater(current_exe, new_exe):
    updater_code = f"""
import time, os, shutil, subprocess
time.sleep(2)
while True:
    try:
        os.remove(r'{current_exe}')
        break
    except PermissionError:
        time.sleep(1)
shutil.move(r'{new_exe}', r'{current_exe}')
subprocess.Popen([r'{current_exe}'])
"""

    updater_path = os.path.join(tempfile.gettempdir(), "updater.py")
    with open(updater_path, "w") as f:
        f.write(updater_code)

    subprocess.Popen([sys.executable, updater_path])
    sys.exit()

def check_for_update():
    latest_version, download_url = get_latest_release()
    if not latest_version or latest_version == APP_VERSION:
        return

    print(f"\n🆕 Nowa wersja dostępna: {latest_version} (masz {APP_VERSION})")
    confirm = input("Czy chcesz pobrać i zainstalować aktualizację? [T/n]: ").strip().lower()

    if confirm in ["", "t", "tak", "y", "yes"]:
        print("🔄 Pobieranie aktualizacji...")
        new_exe = download_new_version(download_url)
        print("✅ Aktualizacja pobrana. Trwa restart...")
        launch_updater(sys.executable, new_exe)
    else:
        print("ℹ️ Pominięto aktualizację.")
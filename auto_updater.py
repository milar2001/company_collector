import requests
import sys
import os
import tempfile
import subprocess
from config import APP_VERSION

GITHUB_USER = "milar2001"
GITHUB_REPO = "company_collector"
LOG_FILE = os.path.join(tempfile.gettempdir(), "updater_log.txt")

def log_error(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write(msg + "\n")
    except:
        pass  # w razie błędu w logowaniu pomijamy

def get_latest_release():
    try:
        url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            tag = data["tag_name"]
            for asset in data["assets"]:
                if asset["name"] == "SzukajkaFirm.exe":
                    return tag.lstrip("v"), asset["browser_download_url"]
    except Exception as e:
        log_error(f"[get_latest_release] Błąd: {e}")
    return None, None

def download_new_version(url):
    try:
        temp_exe = os.path.join(tempfile.gettempdir(), "SzukajkaFirm_new.exe")
        with requests.get(url, stream=True) as r:
            with open(temp_exe, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return temp_exe
    except Exception as e:
        log_error(f"[download_new_version] Błąd: {e}")
        return None

def launch_updater_bat(current_exe, new_exe):
    try:
        bat_path = os.path.join(tempfile.gettempdir(), "update.bat")
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(f"""@echo off
echo 🔄 Czekam az zamknie sie aplikacja...
:loop
tasklist | findstr /I "{os.path.basename(current_exe)}" >nul
if not errorlevel 1 (
    timeout /t 1 >nul
    goto loop
)
move /Y "{new_exe}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
""")
        subprocess.Popen(["cmd", "/c", bat_path])
        sys.exit()
    except Exception as e:
        log_error(f"[launch_updater_bat] Błąd: {e}")

def check_for_update():
    try:
        latest_version, download_url = get_latest_release()
        if not latest_version or latest_version == APP_VERSION:
            return

        print(f"\n🆕 Nowa wersja dostępna: {latest_version} (masz {APP_VERSION})")
        confirm = input("Czy chcesz pobrać i zainstalować aktualizację? [T/n]: ").strip().lower()

        if confirm in ["", "t", "tak", "y", "yes"]:
            print("🔄 Pobieranie aktualizacji...")
            new_exe = download_new_version(download_url)
            if new_exe:
                print("✅ Aktualizacja pobrana. Trwa restart...")
                launch_updater_bat(sys.executable, new_exe)
            else:
                print("❌ Błąd pobierania. Szczegóły w updater_log.txt")
        else:
            print("ℹ️ Pominięto aktualizację.")
    except Exception as e:
        log_error(f"[check_for_update] Błąd: {e}")
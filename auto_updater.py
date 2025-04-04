import requests
import sys
import os
import tempfile
import subprocess
from config import APP_VERSION
import logger_util
GITHUB_USER = "milar2001"
GITHUB_REPO = "company_collector"

def get_latest_release():
    try:
        url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
        logger_util.log_info("🔍 Sprawdzanie najnowszego wydania z GitHub...")
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            tag = data["tag_name"]
            for asset in data["assets"]:
                if asset["name"] == "SzukajkaFirm.exe":
                    logger_util.log_info(f"✅ Znaleziono wydanie: {tag}")
                    return tag.lstrip("v"), asset["browser_download_url"]
        else:
            logger_util.log_error(f"Nieprawidłowy kod statusu HTTP: {response.status_code}")
    except Exception as e:
        logger_util.log_error(f"[get_latest_release] Błąd: {e}")
    return None, None

def download_new_version(url):
    try:
        temp_exe = os.path.join(tempfile.gettempdir(), "SzukajkaFirm_new.exe")
        logger_util.log_info(f"⬇️ Pobieranie nowej wersji z: {url}")
        with requests.get(url, stream=True) as r:
            with open(temp_exe, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        logger_util.log_info("✅ Plik aktualizacji zapisany.")
        return temp_exe
    except Exception as e:
        logger_util.log_error(f"[download_new_version] Błąd: {e}")
        return None

def launch_updater_bat(current_exe, new_exe):
    try:
        bat_path = os.path.join(tempfile.gettempdir(), "update.bat")
        logger_util.log_info("🚀 Tworzenie pliku .bat do aktualizacji aplikacji...")
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(f"""@echo off
echo 🔄 Czekam az zamknie sie aplikacja...
:loop
tasklist | findstr /I \"{os.path.basename(current_exe)}\" >nul
if not errorlevel 1 (
    timeout /t 1 >nul
    goto loop
)
move /Y \"{new_exe}\" \"{current_exe}\"
start \"\" \"{current_exe}\"
del \"%~f0\"
""")
        subprocess.Popen(["cmd", "/c", bat_path])
        logger_util.log_info("🔁 Uruchomiono plik aktualizacyjny i zamykam aplikację.")
        sys.exit()
    except Exception as e:
        logger_util.log_error(f"[launch_updater_bat] Błąd: {e}")

def check_for_update():
    try:
        logger_util.log_info("🧪 Sprawdzanie dostępności aktualizacji...")
        latest_version, download_url = get_latest_release()
        if not latest_version or latest_version == APP_VERSION:
            logger_util.log_info("🆗 Brak nowej wersji lub już aktualna.")
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
                print("❌ Błąd pobierania. Szczegóły w logach.")
        else:
            print("ℹ️ Pominięto aktualizację.")
            logger_util.log_info("Aktualizacja pominięta przez użytkownika.")
    except Exception as e:
        logger_util.log_error(f"[check_for_update] Błąd: {e}")
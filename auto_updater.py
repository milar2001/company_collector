import requests
import sys
import os
import tempfile
import subprocess
from typing import Optional

import logger_util
from config import APP_VERSION, GITHUB_USER, GITHUB_REPO, ASSET_NAME

# ====== API ======
def get_latest_release():
    try:
        url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
        logger_util.log_info("🔍 Sprawdzanie najnowszego wydania z GitHub...")
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            tag = data.get("tag_name", "")
            asset_url = None
            for asset in data.get("assets", []):
                if asset.get("name") == ASSET_NAME:
                    asset_url = asset.get("browser_download_url")
                    break
            if tag and asset_url:
                logger_util.log_info(f"✅ Znaleziono wydanie: {tag}")
                return tag.lstrip("v"), asset_url
            logger_util.log_warning("⚠ Brak oczekiwanego assetu w releasie.")
        else:
            logger_util.log_error(f"Nieprawidłowy kod HTTP: {r.status_code}")
    except Exception as e:
        logger_util.log_error(f"[get_latest_release] Błąd: {e}")
    return None, None

def download_new_version(url) -> Optional[str]:
    try:
        temp_exe = os.path.join(tempfile.gettempdir(), f"{os.path.splitext(ASSET_NAME)[0]}_new.exe")
        logger_util.log_info(f"⬇️ Pobieranie nowej wersji z: {url}")
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(temp_exe, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        logger_util.log_info("✅ Plik aktualizacji zapisany.")
        return temp_exe
    except Exception as e:
        logger_util.log_error(f"[download_new_version] Błąd: {e}")
        return None

def launch_updater_bat(current_exe: str, new_exe: str):
    """
    Zamienia uruchomione EXE po zamknięciu procesu i restartuje aplikację.
    Działa dla buildów PyInstaller (onefile). W trybie 'python main.py' po prostu uruchomi nowy EXE obok.
    """
    try:
        bat_path = os.path.join(tempfile.gettempdir(), "update_company_collector.bat")
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(f"""@echo off
setlocal
echo 🔄 Czekam aż zamknie się aplikacja...
:loop
tasklist | findstr /I "{os.path.basename(current_exe)}" >nul
if not errorlevel 1 (
    timeout /t 1 >nul
    goto loop
)
move /Y "{new_exe}" "{current_exe}" >nul
start "" "{current_exe}"
del "%~f0"
""")
        subprocess.Popen(["cmd", "/c", bat_path], close_fds=True)
        logger_util.log_info("🔁 Uruchomiono skrypt aktualizacyjny. Kończę bieżącą instancję.")
        sys.exit(0)
    except Exception as e:
        logger_util.log_error(f"[launch_updater_bat] Błąd: {e}")

# ====== Interfejsy: GUI/konsola ======
def _is_frozen_exe() -> bool:
    return getattr(sys, "frozen", False) and os.path.isfile(sys.executable)

def _current_binary_path() -> str:
    # Dla EXE: sys.executable; dla Pythona: próba wskazania docelowego pliku (ASSET_NAME) obok skryptu
    if _is_frozen_exe():
        return sys.executable
    # fallback: jeśli nie EXE, to spróbuj nadpisać istniejący EXE leżący obok
    return os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ASSET_NAME)

def check_for_update_console():
    try:
        logger_util.log_info("🧪 Sprawdzanie dostępności aktualizacji...")
        latest_version, download_url = get_latest_release()
        if not latest_version or latest_version == APP_VERSION:
            logger_util.log_info("🆗 Brak nowej wersji lub już aktualna.")
            return

        print(f"\n🆕 Nowa wersja: {latest_version} (masz {APP_VERSION})")
        confirm = input("Pobrać i zainstalować? [T/n]: ").strip().lower()
        if confirm not in ["", "t", "tak", "y", "yes"]:
            logger_util.log_info("Aktualizacja pominięta przez użytkownika.")
            return

        new_exe = download_new_version(download_url)
        if new_exe:
            print("✅ Aktualizacja pobrana. Trwa restart…")
            launch_updater_bat(_current_binary_path(), new_exe)
        else:
            print("❌ Błąd pobierania. Szczegóły w logach.")
    except Exception as e:
        logger_util.log_error(f"[check_for_update_console] Błąd: {e}")

def check_for_update_gui(parent=None, ask=True):
    """
    Wersja do GUI (PySide6). Jeśli ask=True, pokaże pytanie.
    """
    try:
        from PySide6.QtWidgets import QMessageBox
        logger_util.log_info("🧪 (GUI) Sprawdzanie aktualizacji…")
        latest_version, download_url = get_latest_release()
        if not latest_version or latest_version == APP_VERSION:
            logger_util.log_info("🆗 Brak nowej wersji lub już aktualna.")
            return

        if ask:
            ret = QMessageBox.question(
                parent, "Aktualizacja dostępna",
                f"Nowa wersja: {latest_version}\nTwoja wersja: {APP_VERSION}\n\nZainstalować teraz?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if ret != QMessageBox.Yes:
                logger_util.log_info("Aktualizacja pominięta przez użytkownika (GUI).")
                return

        new_exe = download_new_version(download_url)
        if new_exe:
            QMessageBox.information(parent, "Aktualizacja", "Pobrano nową wersję. Aplikacja uruchomi się ponownie.")
            launch_updater_bat(_current_binary_path(), new_exe)
        else:
            QMessageBox.critical(parent, "Aktualizacja", "Nie udało się pobrać aktualizacji. Szczegóły w logach.")
    except Exception as e:
        logger_util.log_error(f"[check_for_update_gui] Błąd: {e}")
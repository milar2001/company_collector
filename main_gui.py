import sys
import json
import asyncio
import html
from datetime import datetime

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QProgressBar, QMessageBox, QComboBox,
    QTextEdit, QFrame
)
from qasync import QEventLoop, asyncSlot

import logger_util
from collector_core import run_collection
from auto_updater import check_for_update_gui


# ------------------------- STYLES (QSS) -------------------------
APP_QSS = """
* { font-family: Inter, Segoe UI, Arial, Helvetica, sans-serif; }

QMainWindow {
    background: #0f172a; /* slate-900 */
}

QLabel {
    color: #e2e8f0;      /* slate-200 */
    font-size: 13px;
}

#TitleLabel {
    color: #f8fafc;      /* slate-50 */
    font-size: 20px;
    font-weight: 600;
    letter-spacing: 0.3px;
}

#Card {
    background: #111827; /* gray-900 */
    border: 1px solid #1f2937; /* gray-800 */
    border-radius: 14px;
}

QLineEdit, QComboBox {
    color: #e5e7eb;
    background: #0b1220;          /* darker input */
    border: 1px solid #1f2937;
    border-radius: 10px;
    padding: 8px 10px;
    selection-background-color: #2563eb; /* blue-600 */
}

QComboBox QAbstractItemView {
    background: #0b1220;
    color: #e5e7eb;
    border: 1px solid #1f2937;
    selection-background-color: #2563eb;
}

QPushButton {
    color: #e5e7eb;
    background: #1d4ed8; /* blue-700 */
    border: 1px solid #1e40af; /* blue-800 */
    border-radius: 10px;
    padding: 10px 14px;
    font-weight: 600;
}
QPushButton:hover { background: #2563eb; }
QPushButton:pressed { background: #1e40af; }
QPushButton:disabled {
    background: #374151; /* gray-700 */
    border-color: #374151;
    color: #9ca3af;      /* gray-400 */
}

QProgressBar {
    border: 1px solid #1f2937;
    border-radius: 10px;
    text-align: center;
    color: #e5e7eb;
    background: #0b1220;
    height: 18px;
}
QProgressBar::chunk {
    border-radius: 10px;
    background-color: #22c55e; /* green-500 */
}

QTextEdit#LogView {
    color: #e5e7eb;
    background: #0b1220;
    border: 1px solid #1f2937;
    border-radius: 12px;
    padding: 10px;
}

/* subtle separators */
#Separator {
    background: #1f2937;
    min-height: 1px;
    max-height: 1px;
}
"""


class CompanyCollectorUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Company Collector — GUI")
        self.setMinimumWidth(780)

        # ---------- ROOT & TITLE ----------
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        title = QLabel("Company Collector")
        title.setObjectName("TitleLabel")
        root_layout.addWidget(title)

        # ---------- INPUT CARD ----------
        input_card = QFrame()
        input_card.setObjectName("Card")
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(16, 16, 16, 12)
        input_layout.setSpacing(12)

        # row 1
        row = QHBoxLayout()
        row.setSpacing(10)

        lbl_city = QLabel("Miasto")
        self.city = QLineEdit()
        self.city.setPlaceholderText("np. Warszawa, Gdańsk, Kraków…")

        lbl_radius = QLabel("Promień [km]")
        self.radius_combo = QComboBox()
        self.radius_combo.addItems(["10", "20", "30", "40", "50"])
        self.radius_combo.setCurrentText("10")

        self.btn = QPushButton("Szukaj")
        self.btn.clicked.connect(self.on_start_clicked)

        # grow
        row.addWidget(lbl_city)
        row.addWidget(self.city, 1)
        row.addSpacing(6)
        row.addWidget(lbl_radius)
        row.addWidget(self.radius_combo)
        row.addSpacing(12)
        row.addWidget(self.btn)

        input_layout.addLayout(row)

        # progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        input_layout.addWidget(self.progress)

        root_layout.addWidget(input_card)

        # separator
        sep = QFrame()
        sep.setObjectName("Separator")
        root_layout.addWidget(sep)

        # ---------- LOGS CARD ----------
        logs_card = QFrame()
        logs_card.setObjectName("Card")
        logs_layout = QVBoxLayout(logs_card)
        logs_layout.setContentsMargins(16, 16, 16, 16)
        logs_layout.setSpacing(10)

        lbl_logs = QLabel("Log")
        logs_layout.addWidget(lbl_logs)

        self.logs = QTextEdit()
        self.logs.setObjectName("LogView")
        self.logs.setReadOnly(True)
        self.logs.setAcceptRichText(True)
        logs_layout.addWidget(self.logs, 1)

        root_layout.addWidget(logs_card, 1)

        self.setCentralWidget(root)

        # ---------- CONFIG ----------
        self.API_KEY = ""
        self.SEARCH_CATEGORIES = []
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            self.API_KEY = config["API_KEY"]
            self._log_info("Wczytano config.json.")
        except Exception as e:
            self._log_error(f"Błąd wczytywania config.json: {e}")
            QMessageBox.critical(self, "Błąd", f"Nie udało się wczytać config.json:\n{e}")

        try:
            with open("categories.json", "r", encoding="utf-8") as f:
                cats = json.load(f)
            self.SEARCH_CATEGORIES = cats.get("categories", [])
            if not self.SEARCH_CATEGORIES:
                raise ValueError("Brak kategorii w categories.json")
            self._log_info(f"Wczytano {len(self.SEARCH_CATEGORIES)} kategorii.")
        except Exception as e:
            self._log_error(f"Błąd wczytywania categories.json: {e}")
            QMessageBox.critical(self, "Błąd", f"Nie udało się wczytać categories.json:\n{e}")

        # progress math
        self._ticks = 0
        self._expected_ticks = max(1, len(self.SEARCH_CATEGORIES) * 60)
        self._current_city = ""
        self._current_radius_km = 0

        # apply styles
        self.setStyleSheet(APP_QSS)

        # updater (GUI)
        try:
            check_for_update_gui(parent=self, ask=True)
        except Exception:
            pass

    # ------------------- LOGGING (COLORED) -------------------
    def _append_html(self, html_line: str):
        """Append rich HTML line to logs."""
        self.logs.append(html_line)

    def _stamp(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _log(self, msg: str, color: str = "#e5e7eb", bold: bool = False, icon: str = "•"):
        safe = html.escape(msg)
        weight = "600" if bold else "400"
        line = (
            f'<span style="color:#94a3b8;">[{self._stamp()}]</span> '
            f'<span style="color:{color};font-weight:{weight}">{icon} {safe}</span>'
        )
        self._append_html(line)
        # mirror to existing file-logger
        try:
            if color == "#ef4444":  # red
                logger_util.log_error(msg)
            elif color == "#f59e0b":  # amber
                logger_util.log_warning(msg)
            else:
                logger_util.log_info(msg)
        except Exception:
            pass

    def _log_info(self, msg: str):
        self._log(msg, color="#93c5fd", icon="ℹ")  # blue-300

    def _log_success(self, msg: str):
        self._log(msg, color="#22c55e", bold=True, icon="✅")  # green-500

    def _log_warn(self, msg: str):
        self._log(msg, color="#f59e0b", icon="⚠")  # amber-500

    def _log_error(self, msg: str):
        self._log(msg, color="#ef4444", bold=True, icon="❌")  # red-500

    # ------------------- PROGRESS -------------------
    def _progress_tick(self):
        self._ticks += 1
        percent = min(100, int(self._ticks * 100 / self._expected_ticks))
        self.progress.setValue(percent)

    # ------------------- UI ACTIONS -------------------
    @Slot()
    def on_start_clicked(self):
        if not self.API_KEY or not self.SEARCH_CATEGORIES:
            QMessageBox.warning(self, "Braki w konfiguracji", "Sprawdź config.json i categories.json.")
            return

        city = self.city.text().strip()
        if not city:
            QMessageBox.information(self, "Uwaga", "Podaj nazwę miasta.")
            return

        try:
            radius_km = int(self.radius_combo.currentText())
        except ValueError:
            QMessageBox.information(self, "Uwaga", "Wybierz poprawny promień.")
            return

        radius_m = radius_km * 1000
        if not (0 < radius_m <= 50000):
            QMessageBox.information(self, "Uwaga", "Promień musi być w zakresie 1–50 km.")
            return

        # reset UI
        self.btn.setEnabled(False)
        self._ticks = 0
        self._expected_ticks = max(1, len(self.SEARCH_CATEGORIES) * 60)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.logs.clear()
        self._current_city = city
        self._current_radius_km = radius_km

        # banner
        self._log_info(f"Start wyszukiwania — {city}, promień {radius_km} km")

        # run
        self.run(city, radius_m)

    @asyncSlot(str, int)
    async def run(self, city_name: str, radius_m: int):
        try:
            total, unique, added = await run_collection(
                city_name=city_name,
                radius_m=radius_m,
                api_key=self.API_KEY,
                categories=self.SEARCH_CATEGORIES,
                progress_cb=self._progress_tick,
                log_cb=None  # nic nie pushujemy z core do GUI
            )
            self.progress.setValue(100)
            # Jedna, wyraźna linia podsumowania
            self._log_success(
                f"{self._current_city} ({self._current_radius_km} km): "
                f"znaleziono {total}, unikalne {unique}, zapisano {added}."
            )
        except Exception as e:
            self._log_error(f"Błąd: {e}")
            QMessageBox.critical(self, "Błąd", str(e))
        finally:
            self.btn.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    ui = CompanyCollectorUI()
    ui.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()

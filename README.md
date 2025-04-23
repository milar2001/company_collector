<details>
<summary>🇵🇱 Kliknij tutaj, aby przeczytać po polsku</summary>

# Szukajka Firm 📍

**Szukajka Firm** to aplikacja w Pythonie umożliwiająca wyszukiwanie firm w oparciu o lokalizację i frazy branżowe przy użyciu Google Places API. Dane są zbierane w czasie rzeczywistym i zapisywane do pliku Excel z dodatkowymi opcjami filtrowania i formatowania.

## ✨ Główne funkcje

- 🔍 Wyszukiwanie firm w zadanym mieście i promieniu (1–50 km)
- 📊 Kategorie fraz wczytywane z pliku `categories.json`
- 📌 Współrzędne miasta pobierane z Google Geocoding API
- 🌐 Dane pobierane z Google Places API v1 (`places:searchText`)
- 🧾 Eksport danych do Excela z obsługą formatowania, walidacji i linków
- 🧐 Automatyczne filtrowanie firm bez strony www i numeru telefonu
- 🔁 Obsługa paginacji Google API
- 📦 System automatycznej aktualizacji aplikacji z GitHub Releases
- 🩵 Asynchroniczne logowanie do pliku (minimalny wpływ na wydajność)

## 🏧 Struktura projektu

```
├── main.py                # Główna aplikacja (uruchamiana przez użytkownika)
├── excel_saver.py         # Zapis do Excela z walidacją i formatowaniem
├── auto_updater.py        # Obsługa automatycznej aktualizacji
├── logger_util.py         # Asynchroniczny logger z osobnym wątkiem
├── config.json            # Plik konfiguracyjny z kluczem API
├── categories.json        # Lista kategorii do wyszukiwania
├── README.md              # Ten plik 😎
```

## 🚀 Jak uruchomić?

1. Utwórz środowisko virtualne:
```bash
python -m venv venv
source venv/bin/activate  # lub venv\Scripts\activate w Windows
```

2. Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

3. Uzupełnij `config.json`:
```json
{
  "API_KEY": "TU_WSTAW_SWÓJ_KLUCZ_API"
}
```

4. Dodaj frazy do `categories.json`:
```json
{
  "categories": ["mechanik samochodowy", "kwiaciarnia", "wynajem aut"]
}
```

5. Uruchom program:
```bash
python main.py
```

## ⚠️ Wymagania

- Konto Google Cloud z aktywnymi API:
  - Geocoding API
  - Places API v1
- Aktywny billing
- Skonfigurowany API_KEY

## 💡 Wskazówki do portfolio

- 👨‍💻 Asynchroniczne API + integracja z Google Cloud
- 📚 Podział na moduły, czyste logowanie, realny use-case
- 🛡 Automatyczne aktualizacje
- 🧐 Obsługa limitów, błędów 429, 502
- 🔗 Można dodać demo (GIF, wideo, screeny Excela)

## 📄 Licencja

Projekt do celów edukacyjnych i portfolio. Nie przeznaczony do użytku komercyjnego.

## 🧠 Autor

Projekt stworzony przez [Twoje Imię lub nick].

</details>

---

<details open>
<summary>🇬🇧 Click here to read in English</summary>

# Company Finder 📍

**Company Finder** is a Python-based application that searches for companies by location and business category using the Google Places API. Results are stored in Excel with advanced formatting and filtering options.

## ✨ Features

- 🔍 Company lookup by city and radius (1–50 km)
- 📊 Categories loaded from `categories.json`
- 📌 Coordinates retrieved via Google Geocoding API
- 🌐 Uses Google Places API v1 (`places:searchText`)
- 🧾 Export to Excel with validation, formatting, and links
- 🧐 Filters out results with no phone or website
- 🔁 Handles Google pagination
- 📦 Auto-update from GitHub Releases
- 🩵 Async logging system with low performance impact

## 🏧 Project structure

```
├── main.py
├── excel_saver.py
├── auto_updater.py
├── logger_util.py
├── config.json
├── categories.json
├── README.md
```

## 🚀 How to run

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Fill in `config.json`:
```json
{
  "API_KEY": "YOUR_API_KEY"
}
```

4. Create `categories.json`:
```json
{
  "categories": ["car repair", "florist", "car rental"]
}
```

5. Run the app:
```bash
python main.py
```

## ⚠️ Requirements

- Google Cloud account with enabled:
  - Geocoding API
  - Places API v1
- Billing enabled
- Proper API_KEY setup

## 💡 Portfolio Tips

- 👨‍💻 Show async API use and modular design
- 📚 Strong separation of concerns and real use-case
- 🛡 Built-in auto-updater from GitHub
- 🔍 Handles API limits, errors, pagination
- 🎥 Add demo/GIF/screens to stand out!

## 📄 License

Created for educational and portfolio purposes.

## 🧠 Author

Created and maintained by [Your Name or GitHub handle].

</details>


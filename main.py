import json
import asyncio
import aiohttp
import time
from tqdm import tqdm  # Pasek postępu
from excel_saver import save_to_excel
from aiohttp import ClientSession, ClientTimeout
from asyncio import Semaphore

# Wczytanie klucza API
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)
API_KEY = config["API_KEY"]

# Wczytanie kategorii z pliku categories.json
try:
    with open("categories.json", "r", encoding="utf-8") as f:
        categories = json.load(f)
    SEARCH_CATEGORIES = categories.get("categories", [])
    if not SEARCH_CATEGORIES:
        raise ValueError("Plik categories.json nie zawiera żadnych kategorii!")
except Exception as e:
    print(f"❌ Błąd wczytywania pliku categories.json: {e}")
    exit()

# Ograniczenie liczby jednoczesnych zapytań do API (np. 2)
SEMAPHORE = Semaphore(2)

# Pobieranie współrzędnych miasta
async def get_city_coordinates(session, city_name):
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": city_name, "key": API_KEY}

    async with session.get(base_url, params=params) as response:
        data = await response.json()

    if "results" in data and len(data["results"]) > 0:
        location = data["results"][0]["geometry"]["location"]
        return {"lat": location["lat"], "lng": location["lng"]}

    print(f"❌ Nie znaleziono współrzędnych dla miasta: {city_name}")
    return None

# Pobieranie firm z Google Places API z obsługą paginacji i ograniczeniem zapytań
async def fetch_places(session, term, location, radius, progress_bar):
    """ Pobiera firmy z API Google Places dla danej frazy i paginuje wyniki. """
    places_data = []
    next_page_token = None
    first_request = True

    while True:
        if next_page_token and not first_request:
            await asyncio.sleep(5)  # Oczekiwanie wymagane przez Google API

        params = {
            "textQuery": term,
            "pageSize": 20,
            "locationBias": {
                "circle": {
                    "center": {
                        "latitude": location["lat"],
                        "longitude": location["lng"]
                    },
                    "radius": radius
                }
            }
        }

        if next_page_token:
            params["pageToken"] = next_page_token

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": API_KEY,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.googleMapsUri,places.internationalPhoneNumber,places.websiteUri,nextPageToken"
        }

        async with SEMAPHORE:  # Ograniczenie liczby równoczesnych zapytań
            for retry in range(3):  # Maksymalnie 3 próby w przypadku błędu 502
                try:
                    async with session.post("https://places.googleapis.com/v1/places:searchText", json=params, headers=headers) as response:
                        if response.status == 502:
                            print(f"⚠️ Błąd 502, ponawiam próbę ({retry + 1}/3)...")
                            await asyncio.sleep(2**retry)  # Backoff
                            continue

                        data = await response.json()
                        if "places" in data:
                            for place in data["places"]:
                                phone_number = place.get("internationalPhoneNumber", None)
                                if not phone_number:
                                    continue

                                places_data.append([
                                    term,
                                    place.get("websiteUri", "Brak strony"),
                                    place["displayName"]["text"] if "displayName" in place else "Brak nazwy",
                                    place.get("formattedAddress", "Brak adresu"),
                                    phone_number
                                ])

                                # Aktualizacja paska postępu
                                if progress_bar.n < progress_bar.total:
                                    progress_bar.update(1)

                        next_page_token = data.get("nextPageToken", None)
                        break  # Jeśli zapytanie powiodło się, wychodzimy z pętli retry
                except aiohttp.ClientError as e:
                    print(f"⚠️ Błąd sieci: {e}. Ponawianie próby...")
                    await asyncio.sleep(2)  # Ponowienie próby po krótkim czasie
            else:
                print("❌ Błąd: Nie udało się pobrać danych po 3 próbach.")

        if not next_page_token:
            break

        first_request = False

    return places_data

async def get_places(city_name, radius):
    """ Wysyła równolegle zapytania dla wszystkich kategorii z promieniem. """
    async with ClientSession(timeout=ClientTimeout(total=60)) as session:
        location = await get_city_coordinates(session, city_name)
        if not location:
            return []

        # Inicjalizacja paska postępu
        total_estimated = len(SEARCH_CATEGORIES) * 60  # Szacowana liczba firm
        progress_bar = tqdm(total=total_estimated, desc=f"📊 Szukanie firm w {city_name}", unit=" firm", bar_format="{l_bar}{bar} {percentage:3.0f}%")

        tasks = [fetch_places(session, term, location, radius, progress_bar) for term in SEARCH_CATEGORIES]
        results = await asyncio.gather(*tasks)

        # Po zakończeniu ustawienie paska na 100%
        progress_bar.n = progress_bar.total
        progress_bar.refresh()
        progress_bar.close()

    # Łączymy wyniki ze wszystkich kategorii
    places_data = [place for result in results for place in result]

    # Po każdym wyszukaniu od razu zapisujemy do Excela
    save_to_excel(places_data)
    print(f"✅ Zapisano {len(places_data)} firm.\n")

# Pętla do wielokrotnego wyszukiwania miast
async def main():
    while True:
        city_name = input("\n🔍 Podaj nazwę miasta, które chcesz przeszukać (lub naciśnij Enter, aby zakończyć): ")
        if city_name.strip() == "":
            print("✅ Program zakończony.")
            break

        while True:
            try:
                radius_km = float(input("📍 Podaj promień wyszukiwania w kilometrach (maksymalnie 50 km): "))
                radius_m = int(radius_km * 1000)  # Konwersja km na metry
                if 0 < radius_m <= 50000:
                    break
                else:
                    print("❌ Błąd: Podaj liczbę z zakresu 1 - 50 km.")
            except ValueError:
                print("❌ Błąd: Wprowadź poprawną liczbę (np. 5, 10, 25).")

        # Pobieramy dane firm i od razu zapisujemy do Excela
        await get_places(city_name, radius_m)

# Uruchamiamy pętlę wyszukiwania
asyncio.run(main())
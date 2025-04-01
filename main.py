import json
import asyncio
import aiohttp
from tqdm import tqdm
from excel_saver import save_to_excel
from config import APP_VERSION

print(f"Aktualna wersja: {APP_VERSION}")

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


# Pobieranie firm z Google Places API z obsługą paginacji
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

        async with session.post("https://places.googleapis.com/v1/places:searchText", json=params,
                                headers=headers) as response:
            data = await response.json()

            if "places" in data:
                for place in data["places"]:
                    website = place.get("websiteUri", None)  # Pobieramy stronę www
                    phone_number = place.get("internationalPhoneNumber", None)

                    if not phone_number or not website:  # Pomijamy firmy bez numeru telefonu i strony
                        continue

                    places_data.append([
                        term,
                        website,  # Zapisujemy tylko firmy, które mają stronę
                        place["displayName"]["text"] if "displayName" in place else "Brak nazwy",
                        place.get("formattedAddress", "Brak adresu"),
                        phone_number
                    ])

                    # Aktualizacja paska postępu (ograniczenie do 100%)
                    if progress_bar.n < progress_bar.total:
                        progress_bar.update(1)

            next_page_token = data.get("nextPageToken", None)

            if not next_page_token:
                break

            first_request = False

    return places_data


async def get_places(city_name, radius):
    """ Wysyła równolegle zapytania dla wszystkich kategorii z promieniem. """
    async with aiohttp.ClientSession() as session:
        location = await get_city_coordinates(session, city_name)
        if not location:
            return []

        # Inicjalizacja paska postępu (poprawiona wersja)
        total_estimated = len(SEARCH_CATEGORIES) * 60  # Szacowana liczba firm
        progress_bar = tqdm(total=total_estimated, desc=f"📊 Szukanie firm w {city_name}", unit=" firm",
                            bar_format="{l_bar}{bar} {percentage:3.0f}%")

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
    print(f"✅ Zapisano {len(places_data)} firm z numerem telefonu.\n")


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
import json
import asyncio
import aiohttp
from tqdm import tqdm
from excel_saver import save_to_excel
from auto_updater import check_for_update
import math
import logger_util

check_for_update()

# Wczytanie klucza API
try:
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    API_KEY = config["API_KEY"]
    logger_util.log_info("✅ Wczytano klucz API.")
except Exception as e:
    logger_util.log_error(f"Błąd wczytywania config.json: {e}")
    exit()

# Wczytanie kategorii z pliku categories.json
try:
    with open("categories.json", "r", encoding="utf-8") as f:
        categories = json.load(f)
    SEARCH_CATEGORIES = categories.get("categories", [])
    if not SEARCH_CATEGORIES:
        logger_util.log_error("Plik categories.json nie zawiera żadnych kategorii!")
except Exception as e:
    logger_util.log_error(f"❌ Błąd wczytywania pliku categories.json: {e}")
    exit()

def calculate_bounds(lat, lng, radius_m):
    try:
        delta_lat = radius_m / 111000
        delta_lng = radius_m / (111000 * abs(math.cos(math.radians(lat))) + 1e-6)
        return {
            "low": {"latitude": lat - delta_lat, "longitude": lng - delta_lng},
            "high": {"latitude": lat + delta_lat, "longitude": lng + delta_lng}
        }
    except Exception as e:
        logger_util.log_error(f"Błąd w calculate_bounds: {e}")
        return {
            "low": {"latitude": lat, "longitude": lng},
            "high": {"latitude": lat, "longitude": lng}
        }

# Pobieranie współrzędnych miasta
async def get_city_coordinates(session, city_name):
    try:
        base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": city_name, "key": API_KEY}

        async with session.get(base_url, params=params) as response:
            if response.status != 200:
                text = await response.text()
                logger_util.log_error(f"❌ Błąd API geocode ({response.status}): {text}")
                return None
            data = await response.json()

        if "results" in data and len(data["results"]) > 0:
            location = data["results"][0]["geometry"]["location"]
            return {"lat": location["lat"], "lng": location["lng"]}

        logger_util.log_warning(f"❌ Nie znaleziono współrzędnych dla miasta: {city_name}")
        print(f"❌ Nie znaleziono współrzędnych dla miasta: {city_name}")
        return None
    except Exception as e:
        logger_util.log_error(f"Błąd w get_city_coordinates: {e}")
        return None

# Pobieranie firm z Google Places API z obsługą paginacji
async def fetch_places(session, term, location, radius, progress_bar):
    places_data = []
    next_page_token = None
    first_request = True

    bounds = calculate_bounds(location["lat"], location["lng"], radius)

    while True:
        if next_page_token and not first_request:
            await asyncio.sleep(5)

        params = {
            "textQuery": term,
            "locationRestriction": {
                "rectangle": {
                    "low": bounds["low"],
                    "high": bounds["high"]
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

        try:
            async with session.post("https://places.googleapis.com/v1/places:searchText", json=params,
                                    headers=headers) as response:
                if response.status != 200:
                    text = await response.text()
                    logger_util.log_error(f"❌ Błąd zapytania ({response.status}): {text}")
                    return []

                if response.content_type != 'application/json':
                    text = await response.text()
                    logger_util.log_error(f"❌ Nieoczekiwany typ odpowiedzi: {response.content_type}, treść: {text}")
                    return []

                data = await response.json()
        except Exception as e:
            logger_util.log_error(f"❌ Błąd przetwarzania odpowiedzi API ({term}): {e}")
            return []

        if "places" in data:
            for place in data["places"]:
                website = place.get("websiteUri", None)
                phone_number = place.get("internationalPhoneNumber", None)

                if not phone_number or not website:
                    continue

                places_data.append([
                    term,
                    website,
                    place["displayName"]["text"] if "displayName" in place else "Brak nazwy",
                    place.get("formattedAddress", "Brak adresu"),
                    phone_number
                ])

                if progress_bar.n < progress_bar.total:
                    progress_bar.update(1)

        next_page_token = data.get("nextPageToken", None)
        if not next_page_token:
            break

        first_request = False

    return places_data

async def get_places(city_name, radius):
    try:
        async with aiohttp.ClientSession() as session:
            location = await get_city_coordinates(session, city_name)
            if not location:
                return []

            total_estimated = len(SEARCH_CATEGORIES) * 60
            progress_bar = tqdm(total=total_estimated, desc=f"📊 Szukanie firm w {city_name}", unit=" firm",
                                bar_format="{l_bar}{bar} {percentage:3.0f}%")

            tasks = [fetch_places(session, term, location, radius, progress_bar) for term in SEARCH_CATEGORIES]
            results = await asyncio.gather(*tasks)

            progress_bar.n = progress_bar.total
            progress_bar.refresh()
            progress_bar.close()

        places_data = [place for result in results for place in result]
        save_to_excel(places_data)
        logger_util.log_info(f"✅ Znaleziono {len(places_data)} firm.")
        print(f"✅ Znaleziono {len(places_data)} firm.\n")
    except Exception as e:
        logger_util.log_error(f"❌ Błąd w get_places: {e}")

# Pętla do wielokrotnego wyszukiwania miast
async def main():
    try:
        while True:
            city_name = input("\n🔍 Podaj nazwę miasta, które chcesz przeszukać (lub naciśnij Enter, aby zakończyć): ")
            if city_name.strip() == "":
                logger_util.log_info("✅ Program zakończony.")
                print("✅ Program zakończony.")
                break

            while True:
                try:
                    radius_km = float(input("📍 Podaj promień wyszukiwania w kilometrach (maksymalnie 50 km): "))
                    radius_m = int(radius_km * 1000)
                    if 0 < radius_m <= 50000:
                        break
                    else:
                        logger_util.log_error("❌ Błąd: Została wprowadzona zła liczba spoza zakresu.")
                        print("❌ Błąd: Podaj liczbę z zakresu 1 - 50 km.")
                except ValueError:
                    logger_util.log_error("❌ Błąd: Wprowadzono niepoprawną wartość promienia.")
                    print("❌ Błąd: Wprowadź poprawną liczbę (np. 5, 10, 25).")

            logger_util.log_info(f"✅ Podano miasto: {city_name}")
            logger_util.log_info(f"✅ Podano promień: {radius_km} km")
            await get_places(city_name, radius_m)
    except Exception as e:
        logger_util.log_error(f"❌ Błąd w głównej pętli programu: {e}")

asyncio.run(main())
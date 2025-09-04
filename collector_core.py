import math
import asyncio
import aiohttp
from typing import Callable, Iterable, Optional, Dict, Any, List, Tuple
import logger_util
from excel_saver import save_to_excel


# ===== Pomocnicze =====
def _norm_phone(s: str) -> str:
    """Zwraca numer złożony wyłącznie z cyfr (do porównań)."""
    return ''.join(ch for ch in str(s) if ch.isdigit())


def calculate_bounds(lat: float, lng: float, radius_m: int) -> Dict[str, Dict[str, float]]:
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


# ===== Sieć =====
async def get_city_coordinates(session: aiohttp.ClientSession, api_key: str, city_name: str,
                               log_cb: Optional[Callable[[str], None]] = None) -> Optional[Dict[str, float]]:
    try:
        base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": city_name, "key": api_key}

        async with session.get(base_url, params=params) as response:
            if response.status != 200:
                text = await response.text()
                msg = f"❌ Błąd API geocode ({response.status}): {text}"
                (log_cb or logger_util.log_error)(msg)
                return None
            data = await response.json()

        if "results" in data and len(data["results"]) > 0:
            loc = data["results"][0]["geometry"]["location"]
            return {"lat": loc["lat"], "lng": loc["lng"]}

        (log_cb or logger_util.log_warning)(f"⚠ Nie znaleziono współrzędnych dla: {city_name}")
        return None
    except Exception as e:
        (log_cb or logger_util.log_error)(f"❌ Wyjątek w get_city_coordinates: {e}")
        return None


async def fetch_places(session: aiohttp.ClientSession,
                       api_key: str,
                       term: str,
                       location: Dict[str, float],
                       radius_m: int,
                       progress_cb: Optional[Callable[[], None]] = None,
                       log_cb: Optional[Callable[[str], None]] = None) -> List[List[str]]:
    places_data: List[List[str]] = []
    next_page_token: Optional[str] = None
    first_request = True
    bounds = calculate_bounds(location["lat"], location["lng"], radius_m)

    while True:
        if next_page_token and not first_request:
            # wymagane przez Places API przy pageToken
            await asyncio.sleep(5)

        params: Dict[str, Any] = {
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
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,places.googleMapsUri,"
                "places.internationalPhoneNumber,places.websiteUri,nextPageToken"
            ),
        }

        try:
            async with session.post("https://places.googleapis.com/v1/places:searchText",
                                    json=params, headers=headers) as response:
                if response.status != 200:
                    text = await response.text()
                    (log_cb or logger_util.log_error)(f"❌ Błąd zapytania [{term}] ({response.status}): {text}")
                    return places_data

                if response.content_type != "application/json":
                    text = await response.text()
                    (log_cb or logger_util.log_error)(f"❌ Nieoczekiwany typ odpowiedzi: {response.content_type}, treść: {text}")
                    return places_data

                data = await response.json()
        except Exception as e:
            (log_cb or logger_util.log_error)(f"❌ Wyjątek w fetch_places [{term}]: {e}")
            return places_data

        if "places" in data:
            for place in data["places"]:
                website = place.get("websiteUri")
                phone_number = place.get("internationalPhoneNumber")
                if not phone_number or not website:
                    continue

                places_data.append([
                    term,
                    website,
                    place["displayName"]["text"] if "displayName" in place else "Brak nazwy",
                    place.get("formattedAddress", "Brak adresu"),
                    phone_number
                ])
                if progress_cb:
                    progress_cb()

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break
        first_request = False

    return places_data


# ===== Orkiestracja =====
async def run_collection(city_name: str,
                         radius_m: int,
                         api_key: str,
                         categories: Iterable[str],
                         progress_cb: Optional[Callable[[], None]] = None,
                         log_cb: Optional[Callable[[str], None]] = None) -> Tuple[int, int, int]:
    """
    Zbiera firmy dla zadanych kategorii, deduplikuje WYŁĄCZNIE po numerze (znormalizowanym),
    zapisuje do Excela.
    Zwraca (liczba_znalezionych, liczba_po_dedup, dodane_do_excela).
    """
    try:
        async with aiohttp.ClientSession() as session:
            location = await get_city_coordinates(session, api_key, city_name, log_cb)
            if not location:
                return (0, 0, 0)

            tasks = [
                fetch_places(session, api_key, term, location, radius_m, progress_cb, log_cb)
                for term in categories
            ]
            results = await asyncio.gather(*tasks)

        # Spłaszcz
        places_data = [p for batch in results for p in batch]

        # Dedup tylko po numerze (znormalizowanym)
        seen = set()
        deduped: List[List[str]] = []
        for term, website, name, addr, phone in places_data:
            k = _norm_phone(phone)
            if k in seen:
                continue
            seen.add(k)
            deduped.append([term, website, name, addr, phone])

        # Zapis i zwrot licznika dodanych
        added = save_to_excel(deduped)
        # UWAGA: nie logujemy tutaj nic do GUI — GUI wyświetli jedną linię podsumowania.
        return (len(places_data), len(deduped), added)

    except Exception as e:
        (log_cb or logger_util.log_error)(f"❌ Błąd w run_collection: {e}")
        return (0, 0, 0)
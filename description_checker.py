import aiohttp
import asyncio
from bs4 import BeautifulSoup
from collections import Counter

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Słowa kluczowe, które sugerują posiadanie pojazdów
KEYWORDS_POSITIVE = [
    "transport", "spedycja", "logistyka", "przewozy", "flota", "dostawy", "dystrybucja", "kurierskie",
    "przewóz osób", "przewóz towarów", "usługi transportowe", "transport krajowy", "transport międzynarodowy",
    "tabor", "auta dostawcze", "ciężarówki", "naczepy", "autolaweta", "bus", "van", "pojazdy", "samochody służbowe",
    "montaż", "instalacja", "serwis mobilny", "naprawa w terenie",
    "na terenie całego województwa", "na terenie całego powiatu", "mobilny serwis", "prace w terenie",
    "dojazd do klienta", "usługi na miejscu", "obsługa serwisowa", "dojazd w cenie",
    "budowa", "remont", "ekipa budowlana", "roboty ziemne", "maszyny budowlane",
    "wynajem samochodów", "leasing pojazdów", "auto wypożyczalnia", "wynajem busów"
]

# Słowa kluczowe, które sugerują, że firma NIE posiada własnej floty
KEYWORDS_NEGATIVE = [
    "serwis samochodowy", "mechanika", "warsztat", "naprawa pojazdów", "diagnostyka", "stacja kontroli",
    "lakiernia", "blacharnia", "naprawa silników", "naprawa skrzyń biegów", "auto detailing",
    "stacja diagnostyczna", "czyszczenie tapicerki", "myjnia samochodowa"
]


async def fetch_html(session, url):
    """ Pobiera pełny kod HTML strony firmy asynchronicznie """
    try:
        async with session.get(url, timeout=5) as response:
            return await response.text() if response.status == 200 else None
    except:
        return None  # W razie błędu zwracamy None


async def fetch_all_html(urls):
    """ Pobiera strony dla wszystkich firm równocześnie """
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_html(session, url) for url in urls]
        return await asyncio.gather(*tasks)


def count_keyword_matches_in_html(html, positive_keywords, negative_keywords):
    """
    Sprawdza liczbę słów kluczowych w pełnym HTML.
    """
    if not html:
        return 0

    soup = BeautifulSoup(html, "html.parser")
    full_text = soup.get_text(separator=" ").lower()

    words = full_text.split()
    word_count = Counter(words)

    positive_matches = sum(word_count[word] for word in positive_keywords if word in word_count)

    if any(word in word_count for word in negative_keywords):
        return 0

    return positive_matches


async def fetch_and_analyze_html(company_links):
    """ Pobiera pełny HTML i analizuje firmy asynchronicznie """
    html_pages = await fetch_all_html(company_links)

    results = []
    for link, html in zip(company_links, html_pages):
        if html:
            matches = count_keyword_matches_in_html(html, KEYWORDS_POSITIVE, KEYWORDS_NEGATIVE)
            if matches > 0:
                results.append((link, matches))

    return results
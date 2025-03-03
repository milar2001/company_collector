import aiohttp
import asyncio
import json
from bs4 import BeautifulSoup
from collections import Counter

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


# Wczytywanie słów kluczowych z pliku JSON
def load_keywords():
    with open("keywords.json", "r", encoding="utf-8") as file:
        return json.load(file)


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
    Sprawdza liczbę słów kluczowych i fraz w pełnym HTML.
    """
    if not html:
        return 0

    soup = BeautifulSoup(html, "html.parser")
    full_text = soup.get_text(separator=" ").lower()

    # Liczenie wystąpień pojedynczych słów
    words = full_text.split()
    word_count = Counter(words)
    positive_matches = sum(word_count[word] for word in positive_keywords if word in word_count)

    # Liczenie wystąpień fraz dwuczłonowych i dłuższych
    for phrase in positive_keywords:
        if " " in phrase and phrase in full_text:
            positive_matches += full_text.count(phrase)

    # Sprawdzanie czy tekst zawiera negatywne słowa
    if any(word in full_text for word in negative_keywords):
        return 0

    return positive_matches


async def fetch_and_analyze_html(company_links):
    """ Pobiera pełny HTML i analizuje firmy asynchronicznie """
    keywords = load_keywords()
    positive_keywords = keywords.get("positive", [])
    negative_keywords = keywords.get("negative", [])

    html_pages = await fetch_all_html(company_links)

    results = []
    for link, html in zip(company_links, html_pages):
        if html:
            matches = count_keyword_matches_in_html(html, positive_keywords, negative_keywords)
            if matches > 0:
                results.append((link, matches))

    return results
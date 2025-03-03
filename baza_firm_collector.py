import json
import aiohttp
import asyncio
import pandas as pd
from bs4 import BeautifulSoup
import re
from description_checker import fetch_and_analyze_html
from excel_saver import save_to_excel


async def load_config():
    with open("config.json", "r", encoding="utf-8") as file:
        return json.load(file)


async def fetch(session, url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with session.get(url, headers=headers) as response:
        if response.status != 200:
            print(f"Błąd pobierania strony: {url} - Kod HTTP: {response.status}")
            return None
        return await response.text()


async def get_total_pages(session, category, wojewodztwo):
    url = f"https://www.baza-firm.com.pl/vsk/woj/{category}/{wojewodztwo}/strona-1/"
    html = await fetch(session, url)
    if not html:
        return 1

    soup = BeautifulSoup(html, "html.parser")
    pages = soup.find_all("a", class_="pgn")
    if pages:
        last_page = max(
            [int(re.search(r'\d+', p.get("href")).group()) for p in pages if re.search(r'\d+', p.get("href"))]
        )
        return last_page
    return 1


async def get_firmy_links(session, category, wojewodztwo):
    total_pages = await get_total_pages(session, category, wojewodztwo)
    tasks = []
    for page in range(1, total_pages + 1):
        url = f"https://www.baza-firm.com.pl/vsk/woj/{category}/{wojewodztwo}/strona-{page}/"
        tasks.append(fetch(session, url))

    responses = await asyncio.gather(*tasks)

    firmy = []
    for html in responses:
        if html:
            soup = BeautifulSoup(html, "html.parser")
            for link in soup.find_all("a", class_="wizLnk displayInlineBlock padding5"):
                href = link.get("href")
                nazwa_tag = link.find("span", class_="przeppoz")
                if href and nazwa_tag:
                    nazwa = nazwa_tag.text.strip()
                    firmy.append({"nazwa": nazwa, "link": href})

    return firmy


async def get_firma_details(session, firma):
    url = firma["link"]
    html = await fetch(session, url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Adres
    adres_box = soup.find("div", class_="txtDataBox lineHeight26 firstBox")
    adres = " ".join(adres_box.stripped_strings) if adres_box else "Brak danych"

    # Telefon
    telefon_box = soup.find("div", class_="firstBox txtDataBox lineHeight26")
    telefon = " | ".join(telefon_box.stripped_strings) if telefon_box else "Brak danych"

    # Strona WWW
    www_box = soup.find("div", class_="displayInlineBlock")
    if www_box:
        links = [a.get("href") for a in www_box.find_all("a", itemprop="url")]
        strona_www = " | ".join(links) if links else "Brak danych"
    else:
        strona_www = "Brak danych"

    # Branża
    industry_box = soup.find("div", id="brBox")
    industry = " | ".join(industry_box.stripped_strings) if industry_box else "Brak danych"

    firma.update({
        "adres": adres,
        "telefon": telefon,
        "strona_www": strona_www,
        "branża": industry
    })
    return firma if telefon != "Brak danych" and strona_www != "Brak danych" else None


async def main():
    config = await load_config()
    categories = config["categories"]
    wojewodztwa = config["wojewodztwa"]

    async with aiohttp.ClientSession() as session:
        tasks = [get_firmy_links(session, category, wojewodztwo) for category in categories for wojewodztwo in wojewodztwa]
        all_firmy = await asyncio.gather(*tasks)
        firmy_list = sum(all_firmy, [])

        detail_tasks = [get_firma_details(session, firma) for firma in firmy_list]
        detailed_firmy = await asyncio.gather(*detail_tasks)
        unique_companies = {firma["telefon"]: firma for firma in detailed_firmy if firma}

        # Analiza opisów firm pod kątem słów kluczowych
        description_matches = await fetch_and_analyze_html([firma["link"] for firma in unique_companies.values()])
        for firma in unique_companies.values():
            firma["Liczba dopasowanych słów"] = next((matches for link, matches in description_matches if link == firma["link"]), 0)

        sorted_results = sorted(unique_companies.values(), key=lambda x: x["Liczba dopasowanych słów"], reverse=True)
        data_to_save = [(firma["Liczba dopasowanych słów"], firma["link"], firma["nazwa"], firma["adres"], firma["telefon"]) for firma in sorted_results]
        added_count = save_to_excel(data_to_save)
        print(f"Dodano {added_count} nowych rekordów do firmy.xlsx")


if __name__ == "__main__":
    asyncio.run(main())
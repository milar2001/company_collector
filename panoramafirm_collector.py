import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
import math
import urllib.parse
import os
import re
from description_checker import fetch_and_analyze_html
from excel_saver import save_to_excel

CONFIG_FILE = "config.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def load_config():
    """ Wczytuje plik JSON z kategoriami i województwami. """
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Brak pliku konfiguracyjnego: {CONFIG_FILE}")
    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

async def fetch(session, url):
    async with session.get(url, headers=HEADERS) as response:
        return await response.text() if response.status == 200 else None

async def get_total_pages(session, base_url):
    html = await fetch(session, base_url)
    if not html:
        return 1
    soup = BeautifulSoup(html, "html.parser")
    result_tag = soup.find("h1", class_="font-size-base font-weight-normal text-color-inherit")
    if result_tag:
        match = re.search(r"(\d+) firm", result_tag.text)
        if match:
            total_firms = int(match.group(1))
            return math.ceil(total_firms / 25)
    return 1

async def get_page_data(session, page_url):
    html = await fetch(session, page_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    return soup.find_all("li", class_="company-item")

def clean_address(address):
    """ Usuwa zbędne informacje z adresu """
    return re.sub(r"\s+w odległości:.*", "", address.strip(), flags=re.DOTALL)

def parse_company_data(company):
    name_tag = company.find("a", class_="company-name")
    company_name = name_tag.text.strip() if name_tag else "Brak"
    company_link = name_tag["href"] if name_tag else "Brak"
    phone_tag = company.find("a", class_="icon-telephone")
    phone = phone_tag["title"].strip() if phone_tag and "title" in phone_tag.attrs else "Brak"
    website_tag = company.find("a", class_="icon-website")
    website = website_tag["href"].strip() if website_tag and "href" in website_tag.attrs else "Brak"
    address_tag = company.find("div", class_="address")
    address = clean_address(address_tag.text) if address_tag else "Brak"

    if phone == "Brak" or website == "Brak" or address == "Brak":
        return None

    return {
        "Nazwa firmy": company_name,
        "Adres": address,
        "Numer telefonu": phone,
        "Strona WWW": website,
        "Link do firmy": company_link
    }

async def scrape_all():
    config = load_config()
    all_companies = {}
    async with aiohttp.ClientSession() as session:
        tasks = []
        for category in config["categories"]:
            for wojewodztwo in config["wojewodztwa"]:
                base_url = f"https://panoramafirm.pl/{category}/{wojewodztwo}"
                total_pages = await get_total_pages(session, base_url)
                for page in range(1, total_pages + 1):
                    page_url = f"{base_url}/firmy,{page}.html" if page > 1 else base_url
                    tasks.append(get_page_data(session, page_url))
        results = await asyncio.gather(*tasks)
    for companies in results:
        for company in companies:
            company_data = parse_company_data(company)
            if company_data:
                phone = company_data["Numer telefonu"]
                if phone not in all_companies:
                    all_companies[phone] = company_data
    return list(all_companies.values())

async def process_companies(companies):
    company_links = [company["Link do firmy"] for company in companies if company["Link do firmy"] != "Brak"]
    descriptions = await fetch_and_analyze_html(company_links)
    final_companies = []
    for company in companies:
        for link, matches in descriptions:
            if company["Link do firmy"] == link:
                company["Liczba dopasowanych słów"] = matches
                final_companies.append(company)
                break
    return final_companies

def save_results(companies):
    sorted_companies = sorted(companies, key=lambda x: x.get("Liczba dopasowanych słów", 0), reverse=True)
    data_to_save = [(firma["Liczba dopasowanych słów"], firma["Link do firmy"],
                     firma["Nazwa firmy"], firma["Adres"], firma["Numer telefonu"]) for firma in sorted_companies]
    save_to_excel(data_to_save)
    print(f"Zapisano {len(sorted_companies)} firm do firmy.xlsx.")

async def main():
    company_data = await scrape_all()
    filtered_companies = await process_companies(company_data)
    save_results(filtered_companies)

if __name__ == "__main__":
    asyncio.run(main())
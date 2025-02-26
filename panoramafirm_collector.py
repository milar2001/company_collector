import requests
from bs4 import BeautifulSoup
import re
import math
import urllib.parse
import json
import os

CONFIG_FILE = "config.json"
OUTPUT_FILE = "output.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def load_config():
    """ Wczytuje plik JSON z kategoriami i województwami. """
    if not os.path.exists(CONFIG_FILE):
        print(f"Nie znaleziono pliku {CONFIG_FILE}, tworzenie nowego...")
        default_config = {
            "categories": ["uslugi"],
            "wojewodztwa": ["pomorskie"]
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(default_config, file, indent=4, ensure_ascii=False)
        return default_config

    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def get_total_pages(base_url):
    """ Pobiera liczbę stron dla danej kategorii i województwa. """
    response = requests.get(base_url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Błąd pobierania strony głównej: {response.status_code}")
        return 1

    soup = BeautifulSoup(response.text, "html.parser")
    result_tag = soup.find("h1", class_="font-size-base font-weight-normal text-color-inherit")

    if result_tag:
        match = re.search(r"(\d+) firm", result_tag.text)
        if match:
            total_firms = int(match.group(1))
            return math.ceil(total_firms / 25)

    print("Nie udało się znaleźć liczby firm.")
    return 1


def get_page_data(page_url):
    """ Pobiera i przetwarza dane z pojedynczej strony firm. """
    print(f"Pobieram stronę: {page_url}")

    response = requests.get(page_url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Błąd pobierania strony {page_url}: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    return soup.find_all("li", class_="company-item")


def parse_company_data(company):
    """ Parsuje dane firmy z HTML. """
    name_tag = company.find("a", class_="company-name")
    company_name = name_tag.text.strip() if name_tag else "Brak"

    company_link = name_tag["href"] if name_tag else None
    company_link = urllib.parse.quote(company_link, safe=':/?=&') if company_link else "Brak"

    address_tag = company.find("div", class_="address")
    address = address_tag.text.strip() if address_tag else "Brak"
    address = re.sub(r"\s*w odległości:\s*\d+\s*(km|m)", "", address).strip()

    phone_tag = company.find("a", class_="icon-telephone")
    phone = phone_tag["title"].strip() if phone_tag and "title" in phone_tag.attrs else "Brak"

    website_tag = company.find("a", class_="icon-website")
    website = website_tag["href"].strip() if website_tag and "href" in website_tag.attrs else "Brak"

    # Usuwamy firmy, które nie mają numeru telefonu lub strony WWW
    if phone == "Brak" or website == "Brak":
        return None  # Firma nie spełnia warunków, nie dodajemy jej do wyników

    return {
        "Nazwa firmy": company_name,
        "Adres": address,
        "Numer telefonu": phone,
        "Strona WWW": website,
        "Link do firmy": company_link
    }


def scrape_all():
    """ Pobiera dane firm dla wszystkich kategorii i województw z pliku JSON. """
    config = load_config()
    all_companies = {}

    for category in config["categories"]:
        for wojewodztwo in config["wojewodztwa"]:
            base_url = f"https://panoramafirm.pl/{category}/{wojewodztwo}"
            total_pages = get_total_pages(base_url)
            print(f"{category.capitalize()} w {wojewodztwo}: {total_pages} stron do przetworzenia.")

            for page in range(1, total_pages + 1):
                page_url = f"{base_url}/firmy,{page}.html" if page > 1 else base_url
                companies = get_page_data(page_url)

                for company in companies:
                    company_data = parse_company_data(company)

                    if company_data:  # Jeśli firma spełnia warunki (ma telefon + WWW)
                        phone = company_data["Numer telefonu"]

                        # Usuwanie duplikatów na podstawie numeru telefonu
                        if phone not in all_companies:
                            all_companies[phone] = company_data

    return list(all_companies.values())


def save_results(companies):
    """ Zapisuje dane firm do pliku JSON. """
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(companies, file, indent=4, ensure_ascii=False)
    print(f"Zapisano {len(companies)} firm do pliku {OUTPUT_FILE}.")


if __name__ == "__main__":
    company_data = scrape_all()
    save_results(company_data)
import json
import time
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def load_config():
    """ Wczytuje dane z config.json i generuje listę URL-i OLX """
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    categories = config.get("categories", [])
    wojewodztwa = config.get("wojewodztwa", [])

    search_urls = [
        f"https://www.olx.pl/{category}/{woj}/" for category in categories for woj in wojewodztwa
    ]

    return search_urls


def setup_driver():
    """ Konfiguruje przeglądarkę Selenium """
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Tryb bez GUI
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def get_offer_links(search_url):
    """ Pobiera linki do wszystkich ofert z OLX na danej stronie kategorii. """
    driver = setup_driver()
    driver.get(search_url)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.css-qo0cxu'))
        )
    except:
        print(f"❌ Brak ofert dla: {search_url}")
        driver.quit()
        return []

    offer_links = []
    offers = driver.find_elements(By.CSS_SELECTOR, 'a.css-qo0cxu')

    for offer in offers:
        link = offer.get_attribute("href")
        if link:
            offer_links.append("https://www.olx.pl" + link if link.startswith("/d/") else link)

    driver.quit()
    return offer_links


def get_offer_details(offer_url):
    """ Pobiera szczegóły każdej oferty (nazwa firmy, numer telefonu, adres). """
    driver = setup_driver()
    driver.get(offer_url)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="company-name"]'))
        )
    except:
        print(f"❌ Nie udało się załadować danych dla: {offer_url}")

    try:
        company_name = driver.find_element(By.CSS_SELECTOR, '[data-testid="company-name"]').text.replace("Nazwa firmy:",
                                                                                                         "").strip()
        print(f"✅ Firma: {company_name}")
    except:
        company_name = "BRAK"

    try:
        phone = driver.find_element(By.CSS_SELECTOR, '[data-testid="phone"]').text.replace("Numer telefonu:",
                                                                                           "").strip()
        print(f"📞 Telefon: {phone}")
    except:
        phone = "BRAK"

    try:
        address = driver.find_element(By.CSS_SELECTOR, '[data-testid="address"]').text.replace("Adres:", "").strip()
        print(f"📍 Adres: {address}")
    except:
        address = "BRAK"

    driver.quit()

    return {
        "Nazwa firmy": company_name,
        "Numer telefonu": phone,
        "Adres": address,
        "Link do oferty": offer_url
    }

def main():
    search_urls = load_config()
    all_offers = []

    print(f"📌 Przeszukujemy {len(search_urls)} kategorii/województw.")

    # Pobieramy oferty z każdej strony
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(get_offer_links, search_urls))

    offer_links = [link for sublist in results for link in sublist]  # Flatten list
    print(f"📌 Znaleziono {len(offer_links)} ofert.")

    # Pobieramy dane firm równolegle
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(get_offer_details, offer_links))

    all_offers.extend(results)

    # Zapisywanie do JSON
    with open("olx_offers.json", "w", encoding="utf-8") as f:
        json.dump(all_offers, f, indent=4, ensure_ascii=False)

    print("✅ Dane zostały zapisane w pliku olx_offers.json!")


if __name__ == "__main__":
    main()
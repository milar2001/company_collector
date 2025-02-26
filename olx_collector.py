import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.olx.pl"

# Pobranie strony z listą ofert
response = requests.get(BASE_URL + "/uslugi/pomorskie/")

if response.status_code == 200:
    soup = BeautifulSoup(response.text, "html.parser")

    # Pobranie wszystkich linków do ofert
    listings = soup.find_all("a", class_="css-qo0cxu")

    for listing in listings:
        title = listing.find("h4", class_="css-1sq4ur2")  # Pobranie tytułu
        link = BASE_URL + listing["href"]  # Pełny link do oferty

        if title:
            print(f"Pobieram dane dla: {title.text.strip()} -> {link}")

            # Pobranie strony oferty
            offer_response = requests.get(link)

            if offer_response.status_code == 200:
                offer_soup = BeautifulSoup(offer_response.text, "html.parser")

else:
    print(f"Błąd pobierania strony głównej: {response.status_code}")

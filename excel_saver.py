import pandas as pd
import os
from openpyxl import load_workbook, Workbook
from openpyxl.utils import get_column_letter

def save_to_excel(new_data, filename="firmy.xlsx"):
    """Zapisuje dane do pliku Excel, dodając nowe rekordy i unikając duplikatów w odpowiednich kolumnach."""

    # Sprawdzenie, czy plik istnieje
    if os.path.exists(filename):
        try:
            book = load_workbook(filename)
            sheet_name = book.sheetnames[0]
            sheet = book[sheet_name]
            existing_df = pd.read_excel(filename, sheet_name=sheet_name, dtype=str)

            # Sprawdzenie dostępnych kolumn w pliku
            required_cols = ["Branża", "Strona WWW", "Nazwa Firmy", "Adres", "Numer Telefonu"]
            available_cols = [col for col in required_cols if col in existing_df.columns]
            existing_df = existing_df[available_cols]
        except Exception as e:
            print(f"Błąd odczytu pliku Excel: {e}")
            book = Workbook()
            sheet = book.active
            sheet.title = "Firmy"
            sheet.append(["Branża", "Strona WWW", "Nazwa Firmy", "", "Adres", "", "Numer Telefonu"])
            existing_df = pd.DataFrame(columns=required_cols)
    else:
        book = Workbook()
        sheet = book.active
        sheet.title = "Firmy"
        sheet.append(["Branża", "Strona WWW", "Nazwa Firmy", "", "Adres", "", "Numer Telefonu"])
        book.save(filename)
        existing_df = pd.DataFrame(columns=["Branża", "Strona WWW", "Nazwa Firmy", "Adres", "Numer Telefonu"])

    # Tworzenie DataFrame z nowymi danymi, konwersja NaN -> pusty string
    new_df = pd.DataFrame(new_data, columns=["Branża", "Strona WWW", "Nazwa Firmy", "Adres", "Numer Telefonu"]).fillna("")

    # Połączenie danych i usunięcie duplikatów na podstawie numeru telefonu
    merged_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=["Numer Telefonu"], keep="first")

    # Liczba dodanych rekordów
    added_count = len(merged_df) - len(existing_df)

    # Czyszczenie istniejących danych przed zapisem (ale zostawiamy nagłówki!)
    for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row, min_col=1, max_col=7):
        for cell in row:
            cell.value = None

    # Nagłówki w odpowiednich kolumnach
    sheet["A1"] = "Branża"
    sheet["B1"] = "Strona WWW"
    sheet["C1"] = "Nazwa Firmy"
    sheet["E1"] = "Adres"
    sheet["G1"] = "Numer Telefonu"

    # Wypełnianie wierszy danymi
    for i, row in enumerate(merged_df.itertuples(index=False), start=2):
        sheet[f"A{i}"] = row[0]  # Branża firmy

        # Obsługa hiperłącza - poprawny zapis linku
        website_cell = sheet[f"B{i}"]
        if row[1] and row[1] != "Brak strony" and row[1] != "":
            website_cell.value = "Kliknij tutaj"
            website_cell.hyperlink = row[1]  # Poprawne ustawienie linku
            website_cell.style = "Hyperlink"  # Zmienia styl na niebieski, klikalny link
        else:
            website_cell.value = "Brak strony"

        sheet[f"C{i}"] = row[2]  # Nazwa firmy
        sheet[f"E{i}"] = row[3]  # Adres
        sheet[f"G{i}"] = row[4]  # Numer telefonu

    # Dodanie filtrów do nagłówków
    sheet.auto_filter.ref = "A1:G1"

    # Automatyczne dostosowanie szerokości kolumn
    for col in sheet.columns:
        max_length = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        sheet.column_dimensions[col_letter].width = max_length + 2

    book.save(filename)
    print(f"✅ Dodano {added_count} nowych rekordów do {filename}.")
    return added_count
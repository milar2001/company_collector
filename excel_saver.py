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
            existing_df = pd.read_excel(filename, sheet_name=sheet_name)

            # Sprawdzenie dostępnych kolumn w pliku
            required_cols = ["Liczba dopasowanych słów", "Link do firmy", "Nazwa firmy", "Adres", "Numer telefonu"]
            available_cols = [col for col in required_cols if col in existing_df.columns]
            existing_df = existing_df[available_cols]
        except Exception as e:
            print(f"Błąd odczytu pliku Excel: {e}")
            book = Workbook()
            sheet = book.active
            sheet.title = "Sheet1"
            sheet.append(["Liczba dopasowanych słów", "Link do firmy", "Nazwa firmy", "", "Adres", "", "Numer telefonu"])
            existing_df = pd.DataFrame(columns=required_cols)
    else:
        book = Workbook()
        sheet = book.active
        sheet.title = "Sheet1"
        sheet.append(["Liczba dopasowanych słów", "Link do firmy", "Nazwa firmy", "", "Adres", "", "Numer telefonu"])
        book.save(filename)
        existing_df = pd.DataFrame(columns=["Liczba dopasowanych słów", "Link do firmy", "Nazwa firmy", "Adres", "Numer telefonu"])

    # Konwersja nowej i istniejącej bazy do formatu DataFrame
    new_df = pd.DataFrame(new_data, columns=["Liczba dopasowanych słów", "Link do firmy", "Nazwa firmy", "Adres", "Numer telefonu"])

    # Połączenie danych i usunięcie duplikatów na podstawie numeru telefonu
    merged_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=["Numer telefonu"], keep="first")

    # Sortowanie po liczbie dopasowanych słów (malejąco)
    merged_df = merged_df.sort_values(by="Liczba dopasowanych słów", ascending=False)

    # Liczba dodanych rekordów
    added_count = len(merged_df) - len(existing_df)

    # Czyszczenie istniejących danych przed zapisem
    for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row, min_col=1, max_col=7):
        for cell in row:
            cell.value = None

    # Zapis do odpowiednich kolumn: A, B (hiperłącze), C, E, G
    sheet["A1"] = "Liczba dopasowanych słów"
    sheet["B1"] = "Link do firmy"
    sheet["C1"] = "Nazwa firmy"
    sheet["E1"] = "Adres"
    sheet["G1"] = "Numer telefonu"

    for i, row in enumerate(merged_df.itertuples(index=False), start=2):
        sheet[f"A{i}"] = row[0]  # Liczba dopasowanych słów
        sheet[f"B{i}"].value = "link"
        sheet[f"B{i}"].hyperlink = row[1]  # Link do strony jako hiperłącze
        sheet[f"C{i}"] = row[2]  # Nazwa firmy
        sheet[f"E{i}"] = row[3]  # Adres
        sheet[f"G{i}"] = row[4]  # Numer telefonu

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
    print(f"Dodano {added_count} nowych rekordów do {filename}")
    return added_count
import pandas as pd
import os
from openpyxl import load_workbook, Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule


def save_to_excel(new_data, filename="firmy.xlsx"):
    """Zapisuje dane do pliku Excel, zachowując oznaczenia 'TAK/NIE' i dodając nowe firmy."""

    # Sprawdzenie, czy plik istnieje
    if os.path.exists(filename):
        try:
            book = load_workbook(filename)
            sheet = book.active
            existing_df = pd.read_excel(filename, sheet_name=sheet.title)

            # Sprawdzenie dostępnych kolumn w pliku
            required_cols = ["Branża", "Strona WWW", "Nazwa Firmy", "Adres", "Numer Telefonu", "Odrzucić?"]
            available_cols = [col for col in required_cols if col in existing_df.columns]
            existing_df = existing_df[available_cols]

            # Przechowujemy wartości "TAK/NIE" w słowniku, aby nie nadpisać danych
            existing_decisions = existing_df.set_index("Numer Telefonu")["Odrzucić?"].to_dict()

        except Exception as e:
            print(f"Błąd odczytu pliku Excel: {e}")
            book = Workbook()
            sheet = book.active
            sheet.title = "Sheet1"
            sheet.append(["Branża", "Strona WWW", "Nazwa Firmy", "", "Adres", "", "Numer Telefonu", "Odrzucić?"])
            existing_df = pd.DataFrame(columns=required_cols)
            existing_decisions = {}
    else:
        book = Workbook()
        sheet = book.active
        sheet.title = "Sheet1"
        sheet.append(["Branża", "Strona WWW", "Nazwa Firmy", "", "Adres", "", "Numer Telefonu", "Odrzucić?"])
        book.save(filename)
        existing_df = pd.DataFrame(columns=["Branża", "Strona WWW", "Nazwa Firmy", "Adres", "Numer Telefonu"])
        existing_decisions = {}

    # Konwersja nowej i istniejącej bazy do formatu DataFrame
    new_df = pd.DataFrame(new_data, columns=["Branża", "Strona WWW", "Nazwa Firmy", "Adres", "Numer Telefonu"])

    # Zamiana pustych wartości w kolumnie "Strona WWW" na "Brak strony"
    new_df["Strona WWW"] = new_df["Strona WWW"].fillna("Brak strony")

    # Połączenie danych i usunięcie duplikatów na podstawie numeru telefonu
    merged_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=["Numer Telefonu"], keep="first")

    # Przywracamy wcześniejsze oznaczenia TAK/NIE dla istniejących firm
    merged_df["Odrzucić?"] = merged_df["Numer Telefonu"].map(existing_decisions).fillna("")

    # Czyszczenie istniejących danych przed zapisem
    for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row, min_col=1, max_col=8):
        for cell in row:
            cell.value = None

    # Zapis do odpowiednich kolumn: A, B (hiperłącze), C, E, G, H
    sheet["A1"] = "Branża"
    sheet["B1"] = "Strona WWW"
    sheet["C1"] = "Nazwa Firmy"
    sheet["E1"] = "Adres"
    sheet["G1"] = "Numer Telefonu"
    sheet["H1"] = "Odrzucić?"

    for i, row in enumerate(merged_df.itertuples(index=False), start=2):
        sheet[f"A{i}"] = row[0]  # Branża
        if row[1] == "Brak strony":
            sheet[f"B{i}"] = "Brak strony"
        else:
            sheet[f"B{i}"].value = "Kliknij tutaj"
            sheet[f"B{i}"].hyperlink = row[1]

        sheet[f"C{i}"] = row[2]  # Nazwa firmy
        sheet[f"E{i}"] = row[3]  # Adres
        sheet[f"G{i}"] = row[4]  # Numer telefonu
        sheet[f"H{i}"] = row[5]  # Odrzucić? (TAK/NIE)

    # Dodanie walidacji danych dla checkboxa (TAK/NIE)
    dv = DataValidation(type="list", formula1='"TAK,NIE"', allow_blank=True)
    sheet.add_data_validation(dv)
    for row in range(2, sheet.max_row + 1):
        dv.add(sheet[f"H{row}"])

    # Dodanie formatowania warunkowego (jeśli kolumna H == "TAK", kolorujemy A-G na czerwono)
    red_fill = PatternFill(start_color="FF9999", end_color="FF9999", fill_type="solid")

    formula = f'$H2="TAK"'  # Sprawdza wartość w kolumnie H (od wiersza 2)
    rule = FormulaRule(formula=[formula], fill=red_fill)

    sheet.conditional_formatting.add("A2:G{}".format(sheet.max_row), rule)

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

    # Włączenie filtrowania kolumn
    sheet.auto_filter.ref = sheet.dimensions

    book.save(filename)
    print(
        f"✅ Dodano {len(new_df)} nowych rekordów do {filename}.")
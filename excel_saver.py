import pandas as pd
import os
from openpyxl import load_workbook, Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule
from datetime import datetime

def save_to_excel(new_data, filename="firmy.xlsx"):
    today = datetime.today().strftime('%Y-%m-%d')

    if os.path.exists(filename):
        book = load_workbook(filename)
    else:
        book = Workbook()

    # Pobierz lub utwórz arkusz dzisiejszy
    if today in book.sheetnames:
        sheet = book[today]
        try:
            existing_df = pd.read_excel(filename, sheet_name=today)
            existing_decisions = existing_df.set_index("Numer Telefonu")["Odrzucić?"].to_dict()
        except:
            existing_df = pd.DataFrame(columns=["Branża", "Strona WWW", "Nazwa Firmy", "Adres", "Numer Telefonu", "Odrzucić?"])
            existing_decisions = {}
    else:
        sheet = book.create_sheet(title=today)
        sheet.append(["Branża", "Strona WWW", "Nazwa Firmy", "", "Adres", "", "Numer Telefonu", "Odrzucić?"])
        existing_df = pd.DataFrame(columns=["Branża", "Strona WWW", "Nazwa Firmy", "Adres", "Numer Telefonu", "Odrzucić?"])
        existing_decisions = {}

    # Utwórz zbior wszystkich numerów z pliku
    all_existing_numbers = set()
    for sheet_name in book.sheetnames:
        try:
            df = pd.read_excel(filename, sheet_name=sheet_name)
            if "Numer Telefonu" in df.columns:
                all_existing_numbers.update(df["Numer Telefonu"].dropna().astype(str).tolist())
        except:
            continue

    new_df = pd.DataFrame(new_data, columns=["Branża", "Strona WWW", "Nazwa Firmy", "Adres", "Numer Telefonu"])
    new_df["Strona WWW"] = new_df["Strona WWW"].fillna("Brak strony")
    new_df["Numer Telefonu"] = new_df["Numer Telefonu"].astype(str)

    new_unique_df = new_df[~new_df["Numer Telefonu"].isin(all_existing_numbers)].copy()
    new_unique_df["Odrzucić?"] = new_unique_df["Numer Telefonu"].map(existing_decisions).fillna("")

    # Walidacja TAK/NIE
    existing_validation = DataValidation(type="list", formula1='"TAK,NIE"', allow_blank=True)
    sheet.add_data_validation(existing_validation)

    # Formatowanie warunkowe - relatywna formuła
    red_fill = PatternFill(start_color="FF9999", end_color="FF9999", fill_type="solid")
    formula = '$H2="TAK"'  # użyj dokładnego wiersza
    rule = FormulaRule(formula=[formula], fill=red_fill)

    # Zapamiętaj od której linii zaczynamy dopisywać
    start_row = sheet.max_row + 1

    for i, row in enumerate(new_unique_df.itertuples(index=False), start=start_row):
        sheet[f"A{i}"] = row[0]  # Branża
        if row[1] == "Brak strony":
            sheet[f"B{i}"] = "Brak strony"
        else:
            sheet[f"B{i}"].value = "Kliknij tutaj"
            sheet[f"B{i}"].hyperlink = row[1]
        sheet[f"C{i}"] = row[2]  # Nazwa firmy
        sheet[f"E{i}"] = row[3]  # Adres
        sheet[f"G{i}"] = row[4]  # Numer telefonu
        sheet[f"H{i}"] = row[5]  # Odrzucić?

        existing_validation.add(sheet[f"H{i}"])

    end_row = start_row + len(new_unique_df) - 1
    if len(new_unique_df) > 0:
        for i in range(start_row, end_row + 1):
            formula = f'$H{i}="TAK"'
            rule = FormulaRule(formula=[formula], fill=red_fill)
            sheet.conditional_formatting.add(f"A{i}:G{i}", rule)

    # Dostosowanie szerokości kolumn
    for col in sheet.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        sheet.column_dimensions[col_letter].width = max_len + 2

    # Filtrowanie
    sheet.auto_filter.ref = sheet.dimensions

    book.save(filename)
    print(f"✅ Dodano {len(new_unique_df)} nowych rekordów do {filename}.")
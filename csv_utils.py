"""Funkcje pomocnicze do wczytywania i czyszczenia danych z plikow CSV."""

import pandas as pd

# Kody oznaczajace "brak wad" - nie sa zapisywane jako wady
KODY_BEZ_WAD = {"", "NO_FLAW", "BRAK", "NONE", "-"}


def clear_amount(value):
    """Czysci kwote (np. ' 1 809,00  PLN ') i zamienia ja na float."""
    if value is None or pd.isna(value):
        return 0.0
    s = (
        str(value)
        .replace("PLN", "")
        .replace("zł", "")
        .replace("\xa0", "")  # twarda spacja z Excela
        .replace(" ", "")  # spacja jako separator tysiecy
        .replace(",", ".")
        .strip()
    )
    try:
        return float(s)
    except ValueError:
        return 0.0


def clear_percent(value):
    """Zamienia procent na ulamek: '20%' -> 0.2, '0.2' -> 0.2, '20' -> 0.2."""
    if value is None or pd.isna(value):
        return 0.0
    s = str(value).strip()
    if s.endswith("%"):
        return clear_amount(s[:-1]) / 100
    liczba = clear_amount(s)
    # Wartosc wieksza niz 1 traktujemy jako procent zapisany bez znaku '%'
    return liczba / 100 if liczba > 1 else liczba


def clear_int(value):
    """Zamienia wartosc na int (np. rok wydania); zwraca None, gdy sie nie da."""
    if value is None or pd.isna(value):
        return None
    try:
        return int(float(str(value).replace(",", ".").strip()))
    except ValueError:
        return None


def normalize_code(value):
    """Czysci kod wady/przedmiotu: usuwa spacje, tabulatory i smieci po pierwszym slowie."""
    if value is None or pd.isna(value):
        return ""
    czesci = str(value).strip().split()
    return czesci[0].strip().upper() if czesci else ""


def split_defect_codes(value):
    """Rozbija komorke z kodami wad ('MISSING_BOX, MISSING_MANUAL') na liste kodow.

    Kody oznaczajace brak wad (np. NO_FLAW) sa pomijane.
    """
    if value is None or pd.isna(value):
        return []
    kody = []
    for fragment in str(value).replace("|", ",").replace("/", ",").split(","):
        kod = normalize_code(fragment)
        if kod not in KODY_BEZ_WAD and kod not in kody:
            kody.append(kod)
    return kody


def find_column(df, prefix):
    """Zwraca nazwe kolumny zaczynajacej sie od prefix (np. 'cena_bazowa (v_base)' dla 'cena_bazowa')."""
    for col in df.columns:
        if col.startswith(prefix):
            return col
    return None


def load_csv_data(path, required_column):
    """Wczytuje plik CSV (UTF-8, srednik) i sprawdza, czy wymagana kolumna istnieje."""
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig", on_bad_lines="skip", dtype=str)
    # Normalizacja nazw kolumn: male litery, bez spacji i tabulatorow na koncach
    df.columns = [str(col).strip().lower() for col in df.columns]

    if required_column.lower() not in df.columns:
        raise ValueError(f"BLAD: Kolumna '{required_column}' nie zostala znaleziona w pliku {path}.")
    return df

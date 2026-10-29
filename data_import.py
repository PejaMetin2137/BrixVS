"""Skrypt ETL: wczytuje slownik wad, kary wiekowe i przedmioty z plikow CSV do bazy danych.

Uruchomienie (z aktywnym venv i dzialajaca baza w Dockerze):
    python data_import.py

Skrypt mozna uruchamiac wielokrotnie: istniejace rekordy sa aktualizowane, a nie dublowane.
"""

import os

import pandas as pd

from csv_utils import (
    clear_amount,
    clear_int,
    clear_percent,
    find_column,
    load_csv_data,
    normalize_code,
    split_defect_codes,
)
from database import Base, SessionLocal, engine
from models import AgePenalty, ConditionDefect, MarketplaceItem

PLIK_WADY = "damage_table.csv"
PLIK_KARY_WIEKOWE = "kary_wiekowe.csv"
PLIK_PRZEDMIOTY = "PoF.csv"


def import_defects(db):
    """1. Slownik wad (damage_table.csv)."""
    print(f"Importowanie: {PLIK_WADY}")
    df = load_csv_data(PLIK_WADY, "kod_wady")
    nowe, zaktualizowane = 0, 0

    for _, row in df.iterrows():
        kod = normalize_code(row.get("kod_wady"))
        if not kod:
            continue

        dane = dict(
            nazwa_wady=str(row.get("nazwa_wady", "")).strip(),
            typ_przedmiotu=str(row.get("typ_przedmiotu", "")).strip().upper(),
            kara_procentowa=clear_percent(row.get("kara_procentowa")),
            opis=str(row.get("opis")).strip() if not pd.isna(row.get("opis")) else None,
        )

        wada = db.query(ConditionDefect).filter(ConditionDefect.kod_wady == kod).first()
        if wada is None:
            db.add(ConditionDefect(kod_wady=kod, **dane))
            nowe += 1
        else:
            for pole, wartosc in dane.items():
                setattr(wada, pole, wartosc)
            zaktualizowane += 1

    db.flush()
    print(f"  Wady: {nowe} nowych, {zaktualizowane} zaktualizowanych")


def import_age_penalties(db):
    """2. Kary zalezne od wieku zestawu (kary_wiekowe.csv) - plik opcjonalny."""
    if not os.path.exists(PLIK_KARY_WIEKOWE):
        print(f"Pomijam {PLIK_KARY_WIEKOWE} (brak pliku) - uzywane beda kary domyslne ze slownika wad")
        return

    print(f"Importowanie: {PLIK_KARY_WIEKOWE}")
    df = load_csv_data(PLIK_KARY_WIEKOWE, "kod_wady")
    licznik = 0
    wyczyszczone = set()

    for _, row in df.iterrows():
        kod = normalize_code(row.get("kod_wady"))
        wiek_od = clear_int(row.get("wiek_od"))
        wiek_do = clear_int(row.get("wiek_do"))
        if not kod or wiek_od is None or wiek_do is None:
            continue

        wada = db.query(ConditionDefect).filter(ConditionDefect.kod_wady == kod).first()
        if wada is None:
            print(f"  UWAGA: kod '{kod}' z {PLIK_KARY_WIEKOWE} nie istnieje w slowniku wad - pomijam")
            continue

        # Przy pierwszym wierszu danej wady usuwamy jej stare przedzialy (plik jest zrodlem prawdy)
        if wada.id not in wyczyszczone:
            db.query(AgePenalty).filter(AgePenalty.wada_id == wada.id).delete()
            wyczyszczone.add(wada.id)

        db.add(AgePenalty(wada_id=wada.id, wiek_od=wiek_od, wiek_do=wiek_do, kara=clear_percent(row.get("kara"))))
        licznik += 1

    db.flush()
    print(f"  Kary wiekowe: {licznik} przedzialow")


def import_items(db):
    """3. Przedmioty (PoF.csv) wraz z powiazaniami do wad."""
    print(f"Importowanie: {PLIK_PRZEDMIOTY}")
    df = load_csv_data(PLIK_PRZEDMIOTY, "kod_przedmiotu")

    kol_cena = find_column(df, "cena_bazowa")
    kol_wycena = find_column(df, "wycena_algorytmu")
    kol_rok = find_column(df, "rok")
    if kol_rok is None:
        print("  UWAGA: brak kolumny 'rok_wydania' w PoF.csv - kary wiekowe nie beda stosowane")

    nowe, zaktualizowane = 0, 0
    nieznane_kody = set()

    for _, row in df.iterrows():
        kod = str(row.get("kod_przedmiotu", "")).strip() if not pd.isna(row.get("kod_przedmiotu")) else ""
        if not kod:
            continue

        typ = str(row.get("typ", "")).strip().upper()
        dane = dict(
            typ=typ,
            nazwa=str(row.get("nazwa", "")).strip(),
            stan=str(row.get("stan", "")).strip().upper(),
            rok_wydania=clear_int(row.get(kol_rok)) if kol_rok else None,
            cena_bazowa=clear_amount(row.get(kol_cena)),
            wspolczynnik_kary=clear_percent(row.get("wspolczynnik_kary")),
            wycena_algorytmu=clear_amount(row.get(kol_wycena)),
        )

        # Powiazanie z wadami ze slownika
        wady = []
        for kod_wady in split_defect_codes(row.get("kod_wady")):
            wada = db.query(ConditionDefect).filter(ConditionDefect.kod_wady == kod_wady).first()
            if wada is None:
                nieznane_kody.add(kod_wady)
                continue
            if wada.typ_przedmiotu and wada.typ_przedmiotu != typ:
                print(f"  UWAGA: {kod}: wada {kod_wady} dotyczy typu {wada.typ_przedmiotu}, a przedmiot to {typ}")
            wady.append(wada)

        przedmiot = db.query(MarketplaceItem).filter(MarketplaceItem.kod_przedmiotu == kod).first()
        if przedmiot is None:
            przedmiot = MarketplaceItem(kod_przedmiotu=kod, **dane)
            db.add(przedmiot)
            nowe += 1
        else:
            for pole, wartosc in dane.items():
                setattr(przedmiot, pole, wartosc)
            zaktualizowane += 1
        przedmiot.wady = wady

    print(f"  Przedmioty: {nowe} nowych, {zaktualizowane} zaktualizowanych")
    if nieznane_kody:
        print(f"  UWAGA: kody wad nieznalezione w slowniku (popraw PoF.csv): {', '.join(sorted(nieznane_kody))}")


def data_import():
    # Tworzy brakujace tabele (np. nowe: przedmiot_wady, kary_wiekowe)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    print("Rozpoczynanie importu danych z plikow CSV...")
    try:
        import_defects(db)
        import_age_penalties(db)
        import_items(db)
        db.commit()
        print("Import zakonczony pomyslnie.")
    except Exception as e:
        db.rollback()
        print(f"BLAD podczas importu danych (zmiany wycofane): {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    data_import()

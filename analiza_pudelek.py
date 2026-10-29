"""Krok 2 analizy: liczy, o ile brak pudelka i instrukcji obniza wartosc zestawu, w zaleznosci od roku wydania.

Metoda: dla kazdego zestawu z dane/zestawy_sw.csv pobieramy z BrickLink Price Guide
(stan uzywany, transakcje z ostatnich 6 miesiecy, region Europa) srednie ceny:
    - zestawu (SET),
    - oryginalnego pudelka (ORIGINAL_BOX),
    - instrukcji (INSTRUCTION).

Kara za brak pudelka    = cena pudelka / cena zestawu
Kara za brak instrukcji = cena instrukcji / cena zestawu

(kupujacy moze dokupic brakujacy element, wiec zestaw bez niego jest wart mniej mniej wiecej o jego cene)

Dla kazdego roku liczona jest mediana (odporna na pojedyncze nietypowe transakcje).

Uruchomienie:
    python analiza_pudelek.py            # pobiera brakujace ceny i liczy wyniki
    python analiza_pudelek.py --tylko-analiza   # bez laczenia z API, tylko przeliczenie z zapisanych cen

Pliki wynikowe (folder dane/):
    ceny_bricklink.csv   - surowe ceny dla kazdego zestawu (dziala jak cache: kolejne uruchomienie dociaga tylko braki)
    kary_rocznie.csv     - mediana kar dla kazdego roku
    wykres_kar.png       - wykres do pracy
"""

import argparse
import csv
import os
import statistics
from datetime import date

PLIK_ZESTAWY = os.path.join("dane", "zestawy_sw.csv")
PLIK_CENY = os.path.join("dane", "ceny_bricklink.csv")
PLIK_WYNIK = os.path.join("dane", "kary_rocznie.csv")
PLIK_WYKRES = os.path.join("dane", "wykres_kar.png")

# Minimalna liczba transakcji, zeby cena byla wiarygodna
MIN_TRANSAKCJI_ZESTAW = 3
MIN_TRANSAKCJI_ELEMENT = 2

KOLUMNY_CEN = [
    "numer", "nazwa", "rok_wydania",
    "cena_zestawu", "transakcje_zestawu",
    "cena_pudelka", "transakcje_pudelka",
    "cena_instrukcji", "transakcje_instrukcji",
    "waluta", "data_pobrania",
]


def wczytaj_csv(sciezka):
    if not os.path.exists(sciezka):
        return []
    with open(sciezka, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def zapisz_csv(sciezka, kolumny, wiersze):
    with open(sciezka, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=kolumny, delimiter=";")
        w.writeheader()
        w.writerows(wiersze)


def pobierz_ceny(klient):
    """Pobiera ceny dla zestawow, ktorych jeszcze nie ma w ceny_bricklink.csv."""
    from bricklink_client import INSTRUCTION, ORIGINAL_BOX, SET, BrickLinkError

    zestawy = wczytaj_csv(PLIK_ZESTAWY)
    if not zestawy:
        raise SystemExit(f"Brak pliku {PLIK_ZESTAWY} - najpierw uruchom: python pobierz_liste_zestawow.py")

    ceny = wczytaj_csv(PLIK_CENY)
    gotowe = {c["numer"] for c in ceny}
    do_pobrania = [z for z in zestawy if z["numer"] not in gotowe]
    print(f"Zestawow: {len(zestawy)}, juz pobranych: {len(gotowe)}, do pobrania: {len(do_pobrania)}")

    for i, z in enumerate(do_pobrania, 1):
        numer = z["numer"]
        try:
            wyniki = {typ: klient.price_guide(typ, numer) for typ in (SET, ORIGINAL_BOX, INSTRUCTION)}
        except BrickLinkError as e:
            print(f"  BLAD przy {numer}: {e}")
            print("  Przerywam - dotychczasowe wyniki sa zapisane, mozna uruchomic skrypt ponownie.")
            break

        def pole(typ, klucz):
            return wyniki[typ][klucz] if wyniki[typ] else 0

        ceny.append({
            "numer": numer,
            "nazwa": z["nazwa"],
            "rok_wydania": z["rok_wydania"],
            "cena_zestawu": pole(SET, "srednia_cena"),
            "transakcje_zestawu": pole(SET, "liczba_transakcji"),
            "cena_pudelka": pole(ORIGINAL_BOX, "srednia_cena"),
            "transakcje_pudelka": pole(ORIGINAL_BOX, "liczba_transakcji"),
            "cena_instrukcji": pole(INSTRUCTION, "srednia_cena"),
            "transakcje_instrukcji": pole(INSTRUCTION, "liczba_transakcji"),
            "waluta": klient.waluta,
            "data_pobrania": date.today().isoformat(),
        })
        # Zapis po kazdym zestawie - przerwanie skryptu nie traci danych
        zapisz_csv(PLIK_CENY, KOLUMNY_CEN, ceny)
        print(f"  [{i}/{len(do_pobrania)}] {numer} {z['nazwa'][:40]}: "
              f"zestaw {pole(SET, 'srednia_cena'):.2f}, pudelko {pole(ORIGINAL_BOX, 'srednia_cena'):.2f}, "
              f"instrukcja {pole(INSTRUCTION, 'srednia_cena'):.2f}")


def udzial(cena_elementu, transakcje_elementu, cena_zestawu, transakcje_zestawu):
    """Zwraca udzial ceny elementu w cenie zestawu albo None, gdy danych jest za malo."""
    if float(transakcje_zestawu) < MIN_TRANSAKCJI_ZESTAW or float(cena_zestawu) <= 0:
        return None
    if float(transakcje_elementu) < MIN_TRANSAKCJI_ELEMENT or float(cena_elementu) <= 0:
        return None
    return float(cena_elementu) / float(cena_zestawu)


def policz_kary():
    """Liczy mediane kar dla kazdego roku i zapisuje wyniki."""
    ceny = wczytaj_csv(PLIK_CENY)
    if not ceny:
        raise SystemExit(f"Brak danych w {PLIK_CENY}")

    po_roku = {}
    for c in ceny:
        rok = int(c["rok_wydania"])
        rekord = po_roku.setdefault(rok, {"pudelko": [], "instrukcja": []})
        u_p = udzial(c["cena_pudelka"], c["transakcje_pudelka"], c["cena_zestawu"], c["transakcje_zestawu"])
        u_i = udzial(c["cena_instrukcji"], c["transakcje_instrukcji"], c["cena_zestawu"], c["transakcje_zestawu"])
        if u_p is not None:
            rekord["pudelko"].append(u_p)
        if u_i is not None:
            rekord["instrukcja"].append(u_i)

    biezacy_rok = date.today().year
    wyniki = []
    for rok in sorted(po_roku):
        p, i = po_roku[rok]["pudelko"], po_roku[rok]["instrukcja"]
        wyniki.append({
            "rok_wydania": rok,
            "wiek_lat": biezacy_rok - rok,
            "kara_pudelko_mediana": round(statistics.median(p), 4) if p else "",
            "liczba_zestawow_pudelko": len(p),
            "kara_instrukcja_mediana": round(statistics.median(i), 4) if i else "",
            "liczba_zestawow_instrukcja": len(i),
        })

    zapisz_csv(PLIK_WYNIK, list(wyniki[0].keys()), wyniki)

    print("\nRok  | Wiek | Pudelko (mediana, n) | Instrukcja (mediana, n)")
    for w in wyniki:
        p = f"{w['kara_pudelko_mediana'] * 100:5.1f}% ({w['liczba_zestawow_pudelko']})" if w["kara_pudelko_mediana"] != "" else "  brak danych"
        i = f"{w['kara_instrukcja_mediana'] * 100:5.1f}% ({w['liczba_zestawow_instrukcja']})" if w["kara_instrukcja_mediana"] != "" else "  brak danych"
        print(f"{w['rok_wydania']} | {w['wiek_lat']:4d} | {p:>20} | {i:>22}")
    print(f"\nZapisano {PLIK_WYNIK}")

    rysuj_wykres(wyniki)


def rysuj_wykres(wyniki):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 5))
    for klucz, etykieta in (("kara_pudelko_mediana", "Brak pudełka"), ("kara_instrukcja_mediana", "Brak instrukcji")):
        punkty = [(w["rok_wydania"], w[klucz] * 100) for w in wyniki if w[klucz] != ""]
        if punkty:
            ax.plot([x for x, _ in punkty], [y for _, y in punkty], marker="o", label=etykieta)

    ax.set_xlabel("Rok wydania zestawu")
    ax.set_ylabel("Spadek wartości zestawu [%]")
    ax.set_title("Udział ceny pudełka i instrukcji w cenie używanego zestawu LEGO Star Wars\n(BrickLink, mediana roczna)")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLIK_WYKRES, dpi=200)
    print(f"Zapisano {PLIK_WYKRES}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tylko-analiza", action="store_true", help="nie lacz sie z API, przelicz zapisane ceny")
    args = parser.parse_args()

    os.makedirs("dane", exist_ok=True)
    if not args.tylko_analiza:
        from bricklink_client import BrickLinkClient

        pobierz_ceny(BrickLinkClient())
    policz_kary()


if __name__ == "__main__":
    main()

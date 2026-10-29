"""Krok 1 analizy: pobiera z Rebrickable liste zestawow LEGO Star Wars z lat 1999-2026
i losuje z kazdego roku probke zestawow do badania cen na BrickLinku.

Wymaga w pliku .env: REBRICKABLE_API_KEY (darmowy klucz z https://rebrickable.com/users/settings/ -> API)

Uruchomienie:
    python pobierz_liste_zestawow.py                 # domyslnie 6 zestawow na rok
    python pobierz_liste_zestawow.py --na-rok 8
Wynik: dane/zestawy_sw.csv
"""

import argparse
import csv
import os
import random
import time

import requests
from dotenv import load_dotenv

load_dotenv()

API = "https://rebrickable.com/api/v3/lego"
ROK_OD, ROK_DO = 1999, 2026
MIN_ELEMENTOW = 100  # pomijamy polybagi, breloki i male zestawy, ktore rzadko maja pudelka na rynku
ZIARNO_LOSOWANIA = 42  # stale ziarno = powtarzalna proba (wazne dla opisu metodologii w pracy)
WYNIK = os.path.join("dane", "zestawy_sw.csv")


def pobierz_wszystko(sciezka, params, klucz):
    """Pobiera wszystkie strony wynikow z Rebrickable API."""
    url = f"{API}{sciezka}"
    wyniki = []
    while url:
        odp = requests.get(url, params=params, headers={"Authorization": f"key {klucz}"}, timeout=30)
        odp.raise_for_status()
        dane = odp.json()
        wyniki.extend(dane["results"])
        url, params = dane.get("next"), None  # kolejne strony maja juz parametry w URL
        time.sleep(1.1)  # limit Rebrickable: ok. 1 zapytanie na sekunde
    return wyniki


def motywy_star_wars(klucz):
    """Zwraca ID motywu 'Star Wars' oraz wszystkich jego podmotywow (np. UCS, Episode I...)."""
    motywy = pobierz_wszystko("/themes/", {"page_size": 1000}, klucz)
    glowne = [m["id"] for m in motywy if m["name"] == "Star Wars" and not m["parent_id"]]
    if not glowne:
        raise SystemExit("Nie znaleziono motywu 'Star Wars' w Rebrickable")

    ids = set(glowne)
    zmiana = True
    while zmiana:  # dokladamy podmotywy kolejnych poziomow
        zmiana = False
        for m in motywy:
            if m["parent_id"] in ids and m["id"] not in ids:
                ids.add(m["id"])
                zmiana = True
    return ids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--na-rok", type=int, default=6, help="ile zestawow losowac z kazdego roku")
    args = parser.parse_args()

    klucz = os.getenv("REBRICKABLE_API_KEY")
    if not klucz:
        raise SystemExit("Brak REBRICKABLE_API_KEY w pliku .env")

    print("Pobieranie motywow Star Wars...")
    ids = motywy_star_wars(klucz)
    print(f"  {len(ids)} motywow (glowny + podmotywy)")

    zestawy = []
    for theme_id in sorted(ids):
        zestawy += pobierz_wszystko(
            "/sets/",
            {"theme_id": theme_id, "min_year": ROK_OD, "max_year": ROK_DO, "page_size": 1000},
            klucz,
        )

    # Tylko glowne wersje zestawow (koncowka -1) i odpowiednio duze
    zestawy = {z["set_num"]: z for z in zestawy if z["set_num"].endswith("-1") and z["num_parts"] >= MIN_ELEMENTOW}
    print(f"  {len(zestawy)} zestawow spelniajacych kryteria")

    losowanie = random.Random(ZIARNO_LOSOWANIA)
    wybrane = []
    for rok in range(ROK_OD, ROK_DO + 1):
        z_roku = sorted((z for z in zestawy.values() if z["year"] == rok), key=lambda z: z["set_num"])
        proba = losowanie.sample(z_roku, min(args.na_rok, len(z_roku)))
        wybrane += proba
        print(f"  {rok}: {len(z_roku):3d} zestawow, wylosowano {len(proba)}")

    os.makedirs("dane", exist_ok=True)
    with open(WYNIK, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["numer", "nazwa", "rok_wydania", "liczba_elementow"])
        for z in sorted(wybrane, key=lambda z: (z["year"], z["set_num"])):
            w.writerow([z["set_num"], z["name"], z["year"], z["num_parts"]])

    print(f"Zapisano {len(wybrane)} zestawow do {WYNIK}")


if __name__ == "__main__":
    main()

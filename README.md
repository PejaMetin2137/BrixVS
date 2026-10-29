# Brix-V&S-by-nitrobrix.pl
System wspomagania wyceny i obrotu kolekcjonerskimi zestawami, minifigurkami oraz przedmiotami powiązanymi z LEGO Star Wars.

Projekt realizowany w ramach inżynierskiej pracy dyplomowej.
Aplikacja webowa służąca do automatycznej wyceny wartości używanych i nowych zestawów oraz minifigurek (z uwzględnieniem wad fizycznych, kompletności i wieku zestawu) na podstawie danych rynkowych, z możliwym wbudowanym modułem marketplace.

## Struktura plików
| Plik | Opis |
|---|---|
| `database.py` | Konfiguracja połączenia z bazą danych (adres z `.env`), sesja `SessionLocal`, `get_db()` dla FastAPI. |
| `models.py` | Tabele SQLAlchemy: `ConditionDefect` (słownik wad), `AgePenalty` (kary zależne od wieku), `MarketplaceItem` (przedmioty) i tabela łącząca `przedmiot_wady` (wiele wad na przedmiot). |
| `schemas.py` | Schematy Pydantic (dane wejściowe i wyjściowe API). |
| `main.py` | Serwer API (FastAPI): `/items`, `/defects`, `/evaluate`, `/evaluate/compare`. |
| `pricing.py` | Algorytm wyceny: `V = V_base × max(1 − Σ kar, 10%)`, kary zależne od wieku zestawu. |
| `csv_utils.py` | Czyszczenie danych z CSV (kwoty, procenty, kody wad). |
| `data_import.py` | Skrypt ETL: import `damage_table.csv`, `kary_wiekowe.csv` i `PoF.csv` do bazy (aktualizuje istniejące rekordy). |
| `bricklink_client.py` | Klient BrickLink API (OAuth 1.0) – ceny z Price Guide. |
| `pobierz_liste_zestawow.py` | Analiza, krok 1: lista zestawów Star Wars 1999–2026 z Rebrickable i losowa próba z każdego roku. |
| `analiza_pudelek.py` | Analiza, krok 2: udział ceny pudełka i instrukcji w cenie zestawu (BrickLink), mediana per rok, wykres. |

## Pliki CSV
Wymagane ustawienia: eksport jako **.csv**, kodowanie **UTF-8**, separator **średnik**.

- `damage_table.csv`: `kod_wady;nazwa_wady;typ_przedmiotu;kara_procentowa;opis`
- `kary_wiekowe.csv`: `kod_wady;wiek_od;wiek_do;kara` (opcjonalny – wady bez wpisu używają kary domyślnej)
- `PoF.csv`: `kod_przedmiotu;typ;nazwa;stan;rok_wydania;cena_bazowa;kod_wady;wspolczynnik_kary;wycena_algorytmu`
  - kilka wad w jednej komórce oddzielamy przecinkiem, np. `MISSING_BOX, MISSING_MANUAL`
  - brak wad: pusta komórka lub `NO_FLAW`

## Uruchomienie środowiska lokalnego
```bash
docker-compose up -d
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # i uzupełnij klucze API
```

## Import danych i start aplikacji
```bash
python data_import.py
uvicorn main:app --reload
```
Dokumentacja API: http://127.0.0.1:8000/docs

## Analiza wpływu braku pudełka i instrukcji na cenę
```bash
python pobierz_liste_zestawow.py
python analiza_pudelek.py
```
Wyniki w folderze `dane/`: `kary_rocznie.csv` i `wykres_kar.png`.

## Zmiany w modelu bazy danych
`create_all` tworzy tylko brakujące tabele i nie zmienia istniejących. Po zmianie kolumn w `models.py` należy wyczyścić bazę:
```bash
docker-compose down -v
docker-compose up -d
python data_import.py
```

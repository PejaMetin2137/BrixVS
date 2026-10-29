from database import SessionLocal
from models import ConditionDefect, MarketplaceItem

def base_check():
    db = SessionLocal()
    try:
        # Sprawdzenie tabeli ConditionDefect
        condition_defect_count = db.query(ConditionDefect).all()
        items_count = db.query(MarketplaceItem).all()

        print(f"\n-- STAN BAZY DANCH --")
        print(f"Liczba wad w slowniku: {len(condition_defect_count)}")
        for defect in condition_defect_count[:3]:  # Wyświetlamy tylko pierwsze 3 wady dla przykładu
            print(f" - Kod wady: {defect.kod_wady}, Nazwa wady: {defect.nazwa_wady} -> Kara procentowa: {defect.kara_procentowa}")

        print(f"\nLiczba przedmiotów w pliku: {len(items_count)}")
        for item in items_count[:3]:  # Wyświetlamy tylko pierwsze 3 przedmioty dla przykładu
            print(f" - Kod przedmiotu: {item.kod_przedmiotu}, Nazwa: {item.nazwa}, Cena rynkowa: {item.cena_bazowa} PLN, z wadami: {item.wycena_algorytmu} PLN")
    finally:
        db.close()

if __name__ == "__main__":
    base_check()
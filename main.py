from typing import List

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import Base, engine, get_db
from pricing import wycen_z_bazy

# Tworzenie brakujacych tabel w bazie danych na podstawie modeli
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="LEGO Star Wars Pricing API",
    description="API do wyceny przedmiotow LEGO Star Wars na podstawie ich stanu i ewentualnych wad.",
    version="1.1.0",
)


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Serwer jest uruchomiony, tabele zostaly utworzone pomyslnie."}


@app.get("/defects", response_model=List[schemas.DefectOut])
def list_defects(db: Session = Depends(get_db)):
    """Slownik wad wraz z karami zaleznymi od wieku."""
    return db.query(models.ConditionDefect).order_by(models.ConditionDefect.typ_przedmiotu).all()


@app.get("/items", response_model=List[schemas.ItemOut])
def list_items(db: Session = Depends(get_db)):
    """Wszystkie przedmioty z bazy wraz z ich wadami."""
    return db.query(models.MarketplaceItem).all()


@app.get("/items/{kod_przedmiotu}", response_model=schemas.ItemOut)
def get_item(kod_przedmiotu: str, db: Session = Depends(get_db)):
    item = db.query(models.MarketplaceItem).filter(models.MarketplaceItem.kod_przedmiotu == kod_przedmiotu).first()
    if item is None:
        raise HTTPException(status_code=404, detail=f"Nie znaleziono przedmiotu {kod_przedmiotu}")
    return item


@app.post("/evaluate", response_model=schemas.EvaluateResponse)
def evaluate(request: schemas.EvaluateRequest, db: Session = Depends(get_db)):
    """Wycena przedmiotu na podstawie ceny bazowej, listy wad i roku wydania."""
    try:
        return wycen_z_bazy(db, request.cena_bazowa, request.kody_wad, request.rok_wydania)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/evaluate/compare", response_model=List[schemas.ComparisonRow])
def compare_with_manual(db: Session = Depends(get_db)):
    """Porownanie wyceny recznej (z PoF.csv) z wycena algorytmu dla wszystkich przedmiotow."""
    wynik = []
    for item in db.query(models.MarketplaceItem).all():
        algorytm = wycen_z_bazy(db, item.cena_bazowa, [w.kod_wady for w in item.wady], item.rok_wydania)
        wynik.append(
            schemas.ComparisonRow(
                kod_przedmiotu=item.kod_przedmiotu,
                nazwa=item.nazwa,
                wycena_reczna=item.wycena_algorytmu,
                wycena_algorytmu=algorytm["wycena_algorytmu"],
                roznica=round(algorytm["wycena_algorytmu"] - item.wycena_algorytmu, 2),
            )
        )
    return wynik

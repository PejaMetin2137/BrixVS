from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AgePenaltyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    wiek_od: int
    wiek_do: int
    kara: float


class DefectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kod_wady: str
    nazwa_wady: str
    typ_przedmiotu: str
    kara_procentowa: float
    opis: Optional[str] = None
    kary_wiekowe: List[AgePenaltyOut] = []


class DefectShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kod_wady: str
    nazwa_wady: str


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kod_przedmiotu: str
    typ: str
    nazwa: str
    stan: str
    rok_wydania: Optional[int] = None
    cena_bazowa: float
    wspolczynnik_kary: float
    wycena_algorytmu: float
    wady: List[DefectShort] = []


class EvaluateRequest(BaseModel):
    cena_bazowa: float = Field(..., gt=0, description="Cena bazowa (V_base) w PLN")
    kody_wad: List[str] = Field(default_factory=list, description="Kody wad ze slownika, np. ['MISSING_BOX']")
    rok_wydania: Optional[int] = Field(None, ge=1999, le=2100, description="Rok wydania zestawu")


class DefectApplied(BaseModel):
    kod_wady: str
    kara: float
    zrodlo_kary: str


class EvaluateResponse(BaseModel):
    cena_bazowa: float
    rok_wydania: Optional[int] = None
    wiek_lat: Optional[int] = None
    wady: List[DefectApplied]
    suma_kar: float
    limit_zastosowany: bool
    wycena_algorytmu: float
    wycena_multiplikatywna: float


class ComparisonRow(BaseModel):
    kod_przedmiotu: str
    nazwa: str
    wycena_reczna: float
    wycena_algorytmu: float
    roznica: float

"""Algorytm wyceny przedmiotow LEGO na podstawie ceny bazowej i wad.

Wzor (metoda addytywna z dolnym limitem):

    V_suggested = V_base * max(1 - suma_kar, MINIMALNY_UDZIAL_WARTOSCI)

gdzie suma_kar to suma kar za wszystkie wady przedmiotu. Kara za wade jest brana
z tabeli kar wiekowych (jesli wada ma w niej przedzial pasujacy do wieku zestawu),
a w przeciwnym razie z kary domyslnej ze slownika wad.

Dla porownania liczona jest tez metoda multiplikatywna:

    V_mult = V_base * (1 - k1) * (1 - k2) * ...
"""

from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

# Przedmiot nigdy nie jest wyceniany ponizej 10% ceny bazowej
MINIMALNY_UDZIAL_WARTOSCI = 0.10

# Przedzial wieku: (wiek_od, wiek_do, kara) - wiek w latach, granice wlacznie
Przedzial = Tuple[int, int, float]


def wiek_przedmiotu(rok_wydania: Optional[int], rok_biezacy: Optional[int] = None) -> Optional[int]:
    """Zwraca wiek przedmiotu w latach (lub None, gdy rok wydania jest nieznany)."""
    if rok_wydania is None:
        return None
    rok_biezacy = rok_biezacy or date.today().year
    return max(rok_biezacy - rok_wydania, 0)


def kara_dla_wady(
    kara_domyslna: float, przedzialy: Sequence[Przedzial], wiek: Optional[int]
) -> Tuple[float, str]:
    """Zwraca kare za wade oraz jej zrodlo ('wiek X-Y lat' albo 'domyslna')."""
    if wiek is not None:
        for wiek_od, wiek_do, kara in przedzialy:
            if wiek_od <= wiek <= wiek_do:
                return kara, f"wiek {wiek_od}-{wiek_do} lat"
    return kara_domyslna, "domyslna"


def oblicz_wycene(
    cena_bazowa: float,
    wady: List[Dict],
    rok_wydania: Optional[int] = None,
    rok_biezacy: Optional[int] = None,
    minimalny_udzial: float = MINIMALNY_UDZIAL_WARTOSCI,
) -> Dict:
    """Liczy sugerowana wycene.

    wady: lista slownikow {"kod_wady": str, "kara_domyslna": float, "przedzialy": [(od, do, kara), ...]}
    """
    wiek = wiek_przedmiotu(rok_wydania, rok_biezacy)

    szczegoly = []
    suma_kar = 0.0
    mnoznik = 1.0
    for wada in wady:
        kara, zrodlo = kara_dla_wady(wada["kara_domyslna"], wada.get("przedzialy", []), wiek)
        szczegoly.append({"kod_wady": wada["kod_wady"], "kara": round(kara, 4), "zrodlo_kary": zrodlo})
        suma_kar += kara
        mnoznik *= 1 - kara

    udzial = 1 - suma_kar
    limit_zastosowany = udzial < minimalny_udzial
    if limit_zastosowany:
        udzial = minimalny_udzial

    return {
        "cena_bazowa": round(cena_bazowa, 2),
        "rok_wydania": rok_wydania,
        "wiek_lat": wiek,
        "wady": szczegoly,
        "suma_kar": round(suma_kar, 4),
        "limit_zastosowany": limit_zastosowany,
        "wycena_algorytmu": round(cena_bazowa * udzial, 2),
        "wycena_multiplikatywna": round(cena_bazowa * max(mnoznik, minimalny_udzial), 2),
    }


def wycen_z_bazy(db, cena_bazowa: float, kody_wad: List[str], rok_wydania: Optional[int] = None) -> Dict:
    """Pobiera wady ze slownika w bazie i liczy wycene.

    Rzuca ValueError z lista kodow, ktorych nie ma w slowniku wad.
    """
    from models import ConditionDefect  # import lokalny, zeby logike wyceny dalo sie testowac bez bazy

    kody = [k.strip().upper() for k in kody_wad if k and k.strip()]
    rekordy = db.query(ConditionDefect).filter(ConditionDefect.kod_wady.in_(kody)).all() if kody else []
    znalezione = {r.kod_wady: r for r in rekordy}

    nieznane = [k for k in kody if k not in znalezione]
    if nieznane:
        raise ValueError(f"Nieznane kody wad: {', '.join(nieznane)}")

    wady = [
        {
            "kod_wady": kod,
            "kara_domyslna": znalezione[kod].kara_procentowa,
            "przedzialy": [(p.wiek_od, p.wiek_do, p.kara) for p in znalezione[kod].kary_wiekowe],
        }
        for kod in dict.fromkeys(kody)  # bez duplikatow, z zachowaniem kolejnosci
    ]
    return oblicz_wycene(cena_bazowa, wady, rok_wydania)

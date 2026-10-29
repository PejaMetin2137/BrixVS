"""Klient BrickLink API (OAuth 1.0) - pobieranie cen z Price Guide.

Wymaga w pliku .env czterech kluczy z https://www.bricklink.com/v2/api/register_consumer.page:
    BL_CONSUMER_KEY, BL_CONSUMER_SECRET, BL_TOKEN_VALUE, BL_TOKEN_SECRET

Dokumentacja API: https://www.bricklink.com/v3/api.page
"""

import os
import time
from typing import Dict, Optional

import requests
from dotenv import load_dotenv
from requests_oauthlib import OAuth1

load_dotenv()

BASE_URL = "https://api.bricklink.com/api/store/v1"

# Typy przedmiotow w katalogu BrickLink, z ktorych korzystamy
SET = "SET"
ORIGINAL_BOX = "ORIGINAL_BOX"
INSTRUCTION = "INSTRUCTION"
MINIFIG = "MINIFIG"


class BrickLinkError(Exception):
    pass


class BrickLinkClient:
    def __init__(self, pauza_s: float = 0.5):
        klucze = {
            nazwa: os.getenv(nazwa)
            for nazwa in ("BL_CONSUMER_KEY", "BL_CONSUMER_SECRET", "BL_TOKEN_VALUE", "BL_TOKEN_SECRET")
        }
        brakujace = [nazwa for nazwa, wartosc in klucze.items() if not wartosc]
        if brakujace:
            raise BrickLinkError(f"Brak kluczy w pliku .env: {', '.join(brakujace)}")

        self.auth = OAuth1(
            klucze["BL_CONSUMER_KEY"],
            klucze["BL_CONSUMER_SECRET"],
            klucze["BL_TOKEN_VALUE"],
            klucze["BL_TOKEN_SECRET"],
        )
        self.pauza_s = pauza_s  # przerwa miedzy zapytaniami, zeby nie przeciazac API
        self.waluta = os.getenv("BL_CURRENCY", "PLN")
        self.region = os.getenv("BL_REGION", "europe")

    def _get(self, sciezka: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Wysyla zapytanie GET; zwraca pole 'data' albo None, gdy przedmiot nie istnieje."""
        time.sleep(self.pauza_s)
        odp = requests.get(f"{BASE_URL}{sciezka}", params=params, auth=self.auth, timeout=30)

        try:
            tresc = odp.json()
        except ValueError:
            raise BrickLinkError(f"Niepoprawna odpowiedz API ({odp.status_code}): {odp.text[:200]}")

        meta = tresc.get("meta", {})
        kod = meta.get("code", odp.status_code)
        if kod == 404:
            return None  # np. dany zestaw nie ma pudelka w katalogu BrickLink
        if kod != 200:
            raise BrickLinkError(f"BrickLink API blad {kod}: {meta.get('message')} - {meta.get('description')}")
        return tresc.get("data")

    def price_guide(self, typ: str, numer: str, stan: str = "U", rodzaj: str = "sold") -> Optional[Dict]:
        """Zwraca podsumowanie Price Guide dla przedmiotu.

        typ:    SET / ORIGINAL_BOX / INSTRUCTION / MINIFIG
        numer:  numer w katalogu BrickLink, np. '7144-1'
        stan:   'U' (uzywane) albo 'N' (nowe)
        rodzaj: 'sold' (sprzedane w ostatnich 6 miesiacach) albo 'stock' (aktualnie na sprzedaz)
        """
        dane = self._get(
            f"/items/{typ}/{numer}/price",
            params={
                "guide_type": rodzaj,
                "new_or_used": stan,
                "currency_code": self.waluta,
                "region": self.region,
            },
        )
        if dane is None:
            return None
        return {
            "srednia_cena": float(dane.get("avg_price") or 0),
            "srednia_wazona": float(dane.get("qty_avg_price") or 0),
            "min_cena": float(dane.get("min_price") or 0),
            "max_cena": float(dane.get("max_price") or 0),
            "liczba_transakcji": int(dane.get("unit_quantity") or 0),
            "liczba_sztuk": int(dane.get("total_quantity") or 0),
            "waluta": dane.get("currency_code", self.waluta),
        }


if __name__ == "__main__":
    # Szybki test polaczenia: python bricklink_client.py
    klient = BrickLinkClient()
    print("Slave I (7144-1), uzywany, sprzedaz z 6 miesiecy:")
    print(klient.price_guide(SET, "7144-1"))

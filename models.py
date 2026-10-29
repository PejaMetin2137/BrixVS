from sqlalchemy import Column, Float, ForeignKey, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base

# Tabela laczaca przedmioty z wadami (relacja wiele-do-wielu):
# jeden przedmiot moze miec kilka wad, a jedna wada wystepuje w wielu przedmiotach.
przedmiot_wady = Table(
    "przedmiot_wady",
    Base.metadata,
    Column("przedmiot_id", Integer, ForeignKey("przedmioty.id", ondelete="CASCADE"), primary_key=True),
    Column("wada_id", Integer, ForeignKey("slownik_wad.id", ondelete="CASCADE"), primary_key=True),
)


class ConditionDefect(Base):
    __tablename__ = "slownik_wad"

    id = Column(Integer, primary_key=True, index=True)
    kod_wady = Column(String(50), unique=True, index=True, nullable=False)
    nazwa_wady = Column(String(100), nullable=False)
    typ_przedmiotu = Column(String(20), nullable=False)
    kara_procentowa = Column(Float, nullable=False)  # kara domyslna, np. 0.25 = 25%
    opis = Column(Text, nullable=True)

    kary_wiekowe = relationship("AgePenalty", back_populates="wada", cascade="all, delete-orphan")


class AgePenalty(Base):
    """Kara za wade zalezna od wieku zestawu (np. brak pudelka w starym zestawie kosztuje wiecej)."""

    __tablename__ = "kary_wiekowe"
    __table_args__ = (UniqueConstraint("wada_id", "wiek_od", name="uq_wada_wiek_od"),)

    id = Column(Integer, primary_key=True, index=True)
    wada_id = Column(Integer, ForeignKey("slownik_wad.id", ondelete="CASCADE"), nullable=False)
    wiek_od = Column(Integer, nullable=False)  # wiek zestawu w latach, wlacznie
    wiek_do = Column(Integer, nullable=False)  # wiek zestawu w latach, wlacznie
    kara = Column(Float, nullable=False)

    wada = relationship("ConditionDefect", back_populates="kary_wiekowe")


class MarketplaceItem(Base):
    __tablename__ = "przedmioty"

    id = Column(Integer, primary_key=True, index=True)
    kod_przedmiotu = Column(String(50), unique=True, index=True, nullable=False)
    typ = Column(String(20), nullable=False)
    nazwa = Column(String(150), nullable=False)
    stan = Column(String(20), nullable=False)
    rok_wydania = Column(Integer, nullable=True)
    cena_bazowa = Column(Float, nullable=False)
    wspolczynnik_kary = Column(Float, default=0.0)  # wartosc z recznej wyceny (PoF.csv)
    wycena_algorytmu = Column(Float, nullable=False)  # wartosc z recznej wyceny (PoF.csv)

    wady = relationship("ConditionDefect", secondary=przedmiot_wady)

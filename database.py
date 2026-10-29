import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Wczytanie zmiennych z pliku .env (jesli istnieje)
load_dotenv()

# URL do laczenia z baza danych PostgreSQL w Dockerze.
# Mozna go nadpisac zmienna DATABASE_URL w pliku .env.
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://admin:secretpassword@localhost:5432/lego_db",
)

# Tworzenie silnika bazy danych
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Konfiguracja sesji bazy danych dla zapytan
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Klasa bazowa dla modeli
Base = declarative_base()


def get_db():
    """Dostarcza sesje bazy danych dla endpointow FastAPI i zamyka ja po zapytaniu."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

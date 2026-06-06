from sqlalchemy import create_engine
from models import Base

DATABASE_URL = "postgresql://postgres:dasha@localhost:5432/swapi"

def create_tables():
    engine = create_engine(DATABASE_URL, echo=True)
    Base.metadata.create_all(engine)
    engine.dispose()

if __name__ == "__main__":
    create_tables()
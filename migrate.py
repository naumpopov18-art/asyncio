from sqlalchemy import create_engine
from models import Base

DATABASE_URL = "postgresql://swapi_user:swapi_pass@127.0.0.1:5432/swapi"

def create_tables():
    try:
        engine = create_engine(DATABASE_URL, echo=True)
        Base.metadata.create_all(engine)
        engine.dispose()
    except Exception as e:
        pass

if __name__ == "__main__":
    create_tables()
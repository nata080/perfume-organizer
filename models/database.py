from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

DATABASE_URL = "sqlite:///organizer.db"

engine = create_engine(DATABASE_URL, connect_args={"timeout": 30}, echo=False)
Session = scoped_session(sessionmaker(bind=engine, expire_on_commit=False))
Base = declarative_base()

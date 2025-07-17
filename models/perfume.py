from sqlalchemy import Column, Integer, String, Float
from models.database import Base

class Perfume(Base):
    __tablename__ = 'perfumes'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    brand = Column(String)
    purchase_price = Column(Float)
    selling_price = Column(Float)
    quantity = Column(Integer)

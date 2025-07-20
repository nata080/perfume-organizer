from sqlalchemy import Column, Integer, String, Float
from models.database import Base

class Perfume(Base):
    __tablename__ = 'perfumes'
    
    id = Column(Integer, primary_key=True)
    brand = Column(String)
    name = Column(String)
    to_decant = Column(Float)  # ml do odlania
    remaining = Column(Float, default=0.0)  # automatycznie (to_decant - zamówione)
    price_per_ml = Column(Float)
    purchase_price = Column(Float)
    
    # Pola automatyczne
    order_count = Column(Integer, default=0)  # liczba zamówień
    selling_price = Column(Float, default=0.0)  # suma wartości zamówień
    extra_costs = Column(Float, default=5.0)  # dekant + koperta
    balance = Column(Float, default=0.0)  # selling_price - purchase_price - extra_costs
    
    def compute_balance(self):
        self.balance = round((self.selling_price or 0) - (self.purchase_price or 0) - (self.extra_costs or 0), 2)
    
    def __repr__(self):
        return f"<{self.brand} {self.name} ({self.to_decant} ml)>"

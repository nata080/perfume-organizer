from sqlalchemy import Column, Integer, String, Float, Boolean
from models.database import Base

class Perfume(Base):
    __tablename__ = 'perfumes'
    
    id = Column(Integer, primary_key=True)
    status = Column(String, default='Dostępny')  # Dostępny/Niedostępny
    brand = Column(String)
    name = Column(String)
    to_decant = Column(Float)  # ml do odlania
    remaining = Column(Float, default=0.0)  # automatycznie (to_decant - zamówione)
    price_per_ml = Column(Float)
    purchase_price = Column(Float)
    fragrantica_url = Column(String)  # Link do Fragrantica
    
    # Gender categories
    is_feminine = Column(Boolean, default=False)
    is_masculine = Column(Boolean, default=False)
    is_unisex = Column(Boolean, default=False)
    
    # Fragrance notes
    top_notes = Column(String)  # JSON string or comma-separated
    heart_notes = Column(String)  # JSON string or comma-separated
    base_notes = Column(String)  # JSON string or comma-separated
    
    # Image data (can store path or base64)
    image_data = Column(String)
    
    # Pola automatyczne
    order_count = Column(Integer, default=0)  # liczba zamówień
    selling_price = Column(Float, default=0.0)  # suma wartości zamówień
    extra_costs = Column(Float, default=5.0)  # dekant + koperta
    balance = Column(Float, default=0.0)  # selling_price - purchase_price - extra_costs
    
    def compute_balance(self):
        self.balance = round((self.selling_price or 0) - (self.purchase_price or 0) - (self.extra_costs or 0), 2)
    
    def __repr__(self):
        return f"<{self.brand} {self.name} ({self.to_decant} ml)>"

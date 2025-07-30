from sqlalchemy import Column, Integer, String, Float, Boolean, Date
from models.database import Base

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    
    # NOWE POLA - dane kupującego
    name = Column(String, nullable=True)  # Nazwa na Facebook
    first_name = Column(String, nullable=True)  # Imię
    last_name = Column(String, nullable=True)  # Nazwisko
    email = Column(String, nullable=True)  # E-mail
    phone = Column(String, nullable=True)  # Telefon
    
    # STARE POLE - kompatybilność wsteczna
    buyer = Column(String, nullable=True)  # Stare pole kupującego
    
    # Reszta pól bez zmian
    shipping = Column(Float, default=0)
    total = Column(Float, default=0)
    sent_message = Column(Boolean, default=False)
    received_money = Column(Boolean, default=False)
    generated_label = Column(Boolean, default=False)
    packed = Column(Boolean, default=False)
    sent = Column(Boolean, default=False)
    confirmation_obtained = Column(Boolean, default=False)
    sale_date = Column(Date, nullable=True)
    notes = Column(String, default="")
    confirmation_date = Column(Date, nullable=True)
    is_split = Column(Boolean, default=False)
    
    def __repr__(self):
        display_name = self.name or self.buyer or f"{self.first_name} {self.last_name}".strip() or "Brak nazwy"
        return f"<Order({display_name})>"

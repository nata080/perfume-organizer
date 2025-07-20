from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, Boolean
from models.database import Base

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)

    buyer = Column(String)             # Imię/nick kupującego
    shipping = Column(Float, nullable=True)  # Kwota wysyłki
    total = Column(Float)              # Całkowita kwota do zapłaty

    sent_message = Column(Boolean, default=False)
    received_money = Column(Boolean, default=False)
    generated_label = Column(Boolean, default=False)
    packed = Column(Boolean, default=False)
    sent = Column(Boolean, default=False)
    confirmation_obtained = Column(Boolean, default=False)

    sale_date = Column(Date, nullable=True)

    def __repr__(self):
        return f"<Order {self.id} {self.buyer}>"

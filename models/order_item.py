from sqlalchemy import Column, Integer, Float, ForeignKey, Boolean
from models.database import Base

class OrderItem(Base):
    __tablename__ = 'order_items'
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    perfume_id = Column(Integer, ForeignKey('perfumes.id'))
    quantity_ml = Column(Float)
    price_per_ml = Column(Float)
    partial_sum = Column(Float)
    is_flask = Column(Boolean, default=False)      # <--- DODAJ TO
    is_split = Column(Boolean, default=False)      # <--- I TO

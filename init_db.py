from models.database import Base, engine
import models.perfume
import models.order
import models.order_item

Base.metadata.create_all(engine)

print("Wszystkie tabele zostały utworzone (jeśli nie istniały).")

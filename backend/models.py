import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON
from pgvector.sqlalchemy import Vector
from database import Base

class ClosetItem(Base):
    __tablename__ = "closet_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    s3_image_url = Column(String, nullable=False)
    
    # Extracted Metadata
    category = Column(String, nullable=True) # e.g., top, bottom, outerwear, footwear, accessory
    color = Column(String, nullable=True)
    sub_category = Column(String, nullable=True) # e.g., t-shirt, hoodie, jeans, skirt
    season = Column(String, nullable=True) # e.g., summer, winter, all-season
    style_tags = Column(JSON, nullable=True) # e.g., ["casual", "minimalist", "retro"]
    
    # 768-dimensional vector embedding of the styling tags / item context
    style_vector = Column(Vector(768), nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Outfit(Base):
    __tablename__ = "outfits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    item_ids = Column(JSON, nullable=False) # list of closet_item ids included in this outfit
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

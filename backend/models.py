import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey
from pgvector.sqlalchemy import Vector
from database import Base


class CatalogItem(Base):
    __tablename__ = "catalog_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    image_url = Column(String, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=False, index=True)  # Tops, Bottoms, Outerwear, Sports Bras, Accessories, One-Piece
    gender = Column(String, nullable=False, index=True)     # "mens" or "womens"

    # Extra metadata from product feed
    color = Column(String, nullable=True)        # e.g. "black"
    fit = Column(String, nullable=True)          # e.g. "regular fit"
    activity = Column(String, nullable=True)     # e.g. "conditioning"
    collection = Column(String, nullable=True)   # e.g. "collective"
    product_link = Column(String, nullable=True)

    # AI-enriched fields (populated by agent later)
    colors = Column(JSON, nullable=True)        # e.g. ["black"]
    style_tags = Column(JSON, nullable=True)    # e.g. ["casual", "streetwear"]
    style_vector = Column(Vector(768), nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ShopperSession(Base):
    __tablename__ = "shopper_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String, unique=True, index=True, nullable=False)
    selfie_url = Column(String, nullable=True)
    gender_preference = Column(String, nullable=True)   # "mens", "womens", or null for both
    favorite_colors = Column(JSON, nullable=True)
    disliked_styles = Column(JSON, nullable=True)
    occasion = Column(String, nullable=True)            # "gym", "casual", "date night"
    notes = Column(String, nullable=True)               # free-form style input

    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Outfit(Base):
    __tablename__ = "outfits"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("shopper_sessions.id"), nullable=True)
    outfit_id_label = Column(String, nullable=True)     # "rec_001"
    item_ids = Column(JSON, nullable=False)             # list of CatalogItem IDs
    reason = Column(String, nullable=True)
    style_tags = Column(JSON, nullable=True)
    styling_tip = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    ranking = Column(Integer, nullable=True)
    total_price = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

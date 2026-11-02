from sqlalchemy import Column, Integer, String, Boolean
from database.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Local (demo) login
    phone = Column(String, unique=True, index=True, nullable=True)
    password = Column(String, nullable=True)

    # Firebase login -- role is looked up by email so you can promote a
    # Firebase-authenticated user to "owner" by editing this row directly.
    email = Column(String, unique=True, index=True, nullable=True)
    firebase_uid = Column(String, unique=True, index=True, nullable=True)

    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)

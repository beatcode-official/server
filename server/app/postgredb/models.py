from sqlalchemy import Column, Integer, String, Date, Boolean
from postgredb.database import Base


class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    date_joined = Column(Date, nullable=False)
    disabled = Column(Boolean, default=False)

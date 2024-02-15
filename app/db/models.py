from sqlalchemy import Column, Integer, Text, ForeignKey, String, Boolean, DateTime, func, JSON, Date, FLOAT
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import pytz

def get_now():
    return datetime.now(pytz.timezone('Asia/Seoul'))

Base = declarative_base()

class User(Base):
    __tablename__ = 'User'

    id = Column(Integer, primary_key=True)
    nickname = Column(String(50), index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    is_deleted = Column(Boolean, default=False)

class House(Base):
    __tablename__ = 'House'

    id = Column(Integer, primary_key=True)
    aptName = Column(String(50), index=True, nullable=False)
    tradeBuildingTypeCode = Column(String(50), nullable=False)
    aptHeatMethodTypeName = Column(String(50), nullable=False)
    aptHeatFuelTypeName = Column(String(50), nullable=False)
    aptParkingCountPerHousehold = Column(FLOAT, nullable=False)
    aptHouseholdCount = Column(Integer, nullable=False)
    exposureAddress = Column(String(100), nullable=False)
    monthlyManagementCost = Column(Integer, nullable=False)
    articleFeatureDescription = Column(Text, nullable=False)
    detailDescription = Column(Text, nullable=False)
    floorLayerName = Column(String(50), nullable=False)
    principalUse = Column(String(50), nullable=False)
    tagList = Column(JSON, nullable=True)
    schoolName = Column(String(50), nullable=False)
    organizationType = Column(String(50), nullable=False)
    establishmentYmd = Column(Date, nullable=False)
    walkTime = Column(Integer, nullable=False)
    studentCountPerTeacher = Column(FLOAT, nullable=False)
    url = Column(String(100), nullable=False)
    image_url = Column(String(200), nullable=True)
    is_deleted = Column(Boolean, default=False)

class Recommendation(Base):
    __tablename__ = 'Recommendation'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('User.id'))
    house_id = Column(Integer, ForeignKey('House.id'))
    reason = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False)
    create_date = Column(DateTime, default=get_now())

class LikedHouse(Base):
    __tablename__ = 'LikedHouse'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('User.id'))
    house_id = Column(Integer, ForeignKey('House.id'))
    is_deleted = Column(Boolean, default=False)
    create_date = Column(DateTime, default=get_now())

def get_Base():
    return Base
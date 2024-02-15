import json

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.ai import HouseRecommender
from app.db.database import get_db, get_current_user, save_db
from app.db.models import User, House


class HouseService:
    def __init__(self, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        self.db = db
        self.user = user

    async def initailize(self):
        with open('app/service/apartment_info.jsonl', 'r') as f:
            data = f.readlines()
            for line in data:
                house_data = json.loads(line)
                if house_data['url'] == "없음" or house_data['image_url'] == "이미지 없음":
                    continue
                house_info = House(
                    aptName=house_data['aptName'],
                    tradeBuildingTypeCode=house_data['tradeBuildingTypeCode'],
                    aptHeatMethodTypeName=house_data['aptHeatMethodTypeName'],
                    aptHeatFuelTypeName=house_data['aptHeatFuelTypeName'],
                    aptParkingCountPerHousehold=house_data['aptParkingCountPerHousehold'],
                    aptHouseholdCount=house_data['aptHouseholdCount'],
                    exposureAddress=house_data['exposureAddress'],
                    monthlyManagementCost=house_data['monthlyManagementCost'],
                    articleFeatureDescription=house_data['articleFeatureDescription'],
                    detailDescription=house_data['detailDescription'],
                    floorLayerName=house_data['floorLayerName'],
                    principalUse=house_data['principalUse'],
                    tagList=house_data['tagList'],
                    schoolName=house_data['schoolName'],
                    organizationType=house_data['organizationType'],
                    establishmentYmd=house_data['establishmentYmd'],
                    walkTime=house_data['walkTime'],
                    studentCountPerTeacher=house_data['studentCountPerTeacher'],
                    url=house_data['url'],
                    image_url=house_data['image_url']
                )
                save_db(house_info, self.db)


    async def create(self, house_data):
        house = House(
            aptName=house_data['aptName'],
            tradeBuildingTypeCode=house_data['tradeBuildingTypeCode'],
            aptHeatMethodTypeName=house_data['aptHeatMethodTypeName'],
            aptHeatFuelTypeName=house_data['aptHeatFuelTypeName'],
            aptParkingCountPerHousehold=house_data['aptParkingCountPerHousehold'],
            aptHouseholdCount=house_data['aptHouseholdCount'],
            exposureAddress=house_data['exposureAddress'],
            monthlyManagementCost=house_data['monthlyManagementCost'],
            articleFeatureDescription=house_data['articleFeatureDescription'],
            detailDescription=house_data['detailDescription'],
            floorLayerName=house_data['floorLayerName'],
            principalUse=house_data['principalUse'],
            tagList=house_data['tagList'],
            schoolName=house_data['schoolName'],
            organizationType=house_data['organizationType'],
            establishmentYmd=house_data['establishmentYmd'],
            walkTime=house_data['walkTime'],
            studentCountPerTeacher=house_data['studentCountPerTeacher'],
            url=house_data['url']
        )
        save_db(house, self.db)

        return house_data

    async def recommendation(self):
        all_houses = self.db.query(House).filter(House.is_deleted == False).all()
        house_recommender = HouseRecommender([house.__dict__ for house in all_houses])
        persona = {
            "person_count": "3명 이상",
            "period": "한달 이상",
            "identity": "직장인",
            "car": "차 없음",
            "child": "아이 없음",
            "significant": "집에서 편안하게 쉬고 싶어요."
        }
        recommended_houses = house_recommender.recommend(persona)
        print(len(recommended_houses))
        print(recommended_houses[0])

        ## DB에 저장

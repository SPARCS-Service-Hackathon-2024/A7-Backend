import json
import requests

from fastapi import Depends, HTTPException, status
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
            "significant": "유성구에 있는 아파트면 좋겠어"
        }
        recommended_houses = house_recommender.recommend(persona)

        candidates = []
        for house in recommended_houses[:3]:
            house_dict = {}
            house = house[1]
            house_dict['aptName'] = house['aptName']
            house_dict['articleFeatureDescription'] = (house['articleFeatureDescription'] + ' ' + house['detailDescription'])[:100]
            house_dict['tagList'] = house['tagList']
            house_dict['walkTime'] = house['walkTime']
            house_dict['studentCountPerTeacher'] = house['studentCountPerTeacher']
            house_dict['aptParkingCountPerHousehold'] = house['aptParkingCountPerHousehold']
            candidates.append(house_dict)

        request_data = {
            "user_info": json.dumps(persona, ensure_ascii=False),
            "candidates": json.dumps(candidates, ensure_ascii=False)
        }

        url = "https://sarabwayu3.hackathon.sparcs.net/"

        response = requests.post(url, json=request_data)
        rank_section = response.text.split("rank:")[1]
        reason_section = rank_section.split("reason:")[1]
        rank_data = rank_section.split("reason:")[0]

        rank_data = rank_data[rank_data.find("["):rank_data.find("]") + 1]
        reason_section = reason_section[reason_section.find("["):reason_section.find("]") + 1]

        try:
            return_data = [json.loads(rank_data.replace('\\"', '"')), json.loads(reason_section.replace('\\"', '"'))]
        except:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"{rank_data}, {reason_section}"
            )

        return return_data

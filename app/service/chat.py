import json

import requests
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db, get_current_user, save_db
from app.db.models import User, House, Recommendation
from app.schemas.request import Chat
from app.service.house import HouseRecommender


class ChatService:
    def __init__(self, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        self.db = db
        self.user = user

    async def chat(self, chat_data: Chat):

        async def check_format(data):
            if data.person_count not in ["1명", "2명", "3명", "4명 이상"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="person_count가 잘못되었습니다."
                )
            if data.period not in ["1주", "2주", "3주", "4주 이상"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="period가 잘못되었습니다."
                )
            if data.identity not in ["학생", "직장인", "기타"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="identity가 잘못되었습니다."
                )
            if data.car not in ["자차", "대중교통"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="car가 잘못되었습니다."
                )
            if data.child not in ["아이 있음", "아이 없음"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="child가 잘못되었습니다."
                )
            return data

        chat_data = await check_format(chat_data)

        persona = {
            "person_count": chat_data.person_count,
            "period": chat_data.period,
            "identity": chat_data.identity,
            "car": chat_data.car,
            "child": chat_data.child,
            "significant": chat_data.significant
        }

        # 모든 집 데이터 가져오기
        all_houses = self.db.query(House).filter(House.is_deleted == False).all()

        # 이미 추천된 데이터 제거
        recommended_houses = self.db.query(Recommendation).filter(
            Recommendation.user_id == self.user.id,
            Recommendation.is_deleted == False
        ).all()
        for house in all_houses:
            if house.id in [recommended_house.house_id for recommended_house in recommended_houses]:
                all_houses.remove(house)

        # 추천 알고리즘 실행
        house_recommender = HouseRecommender([house.__dict__ for house in all_houses])
        recommended_houses = house_recommender.recommend(persona)

        # 추천된 데이터 이름 - id 매핑
        recommended_map = {}
        for house in recommended_houses:
            recommended_map[house[1]["aptName"]] = house[1]["id"]

        # XAI를 활용한 추천 API 호출
        candidates = []
        for house in recommended_houses:
            house_dict = {}
            house = house[1]
            house_dict['aptName'] = house['aptName']
            house_dict['articleFeatureDescription'] = (house['articleFeatureDescription'] + ' ' + house[
                'detailDescription'])[:100]
            house_dict['tagList'] = house['tagList']
            house_dict['walkTime'] = house['walkTime']
            house_dict['studentCountPerTeacher'] = house['studentCountPerTeacher']
            house_dict['aptParkingCountPerHousehold'] = house['aptParkingCountPerHousehold']
            candidates.append(house_dict)

        request_data = {
            "user_info": json.dumps(persona, ensure_ascii=False),
            "candidates": json.dumps(candidates, ensure_ascii=False)
        }

        retry_count = 3

        while retry_count > 0:
            try:
                response = requests.post(settings.HOUSE_REC_URL, json=request_data)
                rank_section = response.text.split("rank:")[1]
                reason_section = rank_section.split("reason:")[1]
                rank_data = rank_section.split("reason:")[0]
                rank_data = rank_data[rank_data.find("["):rank_data.find("]") + 1]
                reason_section = reason_section[reason_section.find("["):reason_section.find("]") + 1]
                rank_data = json.loads(rank_data.replace('\\"', '"'))
                return_data = json.loads(reason_section.replace('\\"', '"'))
                break
            except:
                retry_count -= 1
                print(f"API 호출 시도 중... {retry_count}회 남음")
                if retry_count == 0:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"{rank_data}, {reason_section}"
                    )

        for rank in rank_data:
            recommendation = Recommendation(
                user_id=self.user.id,
                house_id=recommended_map[rank],
                reason=return_data[rank_data.index(rank)]
            )
            save_db(recommendation, self.db)

        return {"rank": rank_data, "reason": return_data}
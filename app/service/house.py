import json
import requests

from fastapi import Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

from app.core.config import settings
from app.db.database import get_db, get_current_user, save_db
from app.db.models import User, House, Recommendation, LikedHouse


class HouseRecommender:
    def __init__(self, house_info):
        self.house_info = house_info
        self.tfidf_vectorizer = TfidfVectorizer()

        # 모든 텍스트 데이터를 수집하여 TF-IDF 벡터화기를 학습시킵니다.
        all_texts = [
            ' '.join(house['tagList']) + ' ' +
            house['articleFeatureDescription'] +
            (" " + house['detailDescription'] if house['detailDescription'] != "없음" else "")
            for house in self.house_info
        ]

        self.tfidf_vectorizer.fit(all_texts)  # 여기서 fit을 호출합니다.

    def vectorize_categorical_data(self, persona):
        person_count = int(persona['person_count'].replace('명', '').split()[0])

        if '한달' in persona['period'] or '이상' in persona['period']:
            period = 4
        else:
            period = int(persona['period'].replace('주', ''))

        identity_vector = [1 if identity in persona['identity'] else 0 for identity in
                           ['학생', '직장인', '취준생', '기타']]
        car = 1 if persona['car'] == '차 있음' else 0
        child = 1 if persona['child'] == '아이 있음' else 0

        return np.array([person_count, period] + identity_vector + [car, child])

    def vectorize_text_data(self, text):
        return self.tfidf_vectorizer.transform([text]).toarray().flatten()

    def extract_room_count(self, house):
        room_tags = [tag for tag in house['tagList'] if '방' in tag]
        room_count_map = {"한개": 1, "두개": 2, "세개": 3, "네개": 4, "다섯개": 5}

        if room_tags:
            for key, value in room_count_map.items():
                if key in room_tags[0]:
                    return value
        return 1

    def vectorize_data(self, house, persona):
        persona_vector = self.vectorize_categorical_data(persona)
        house_text = house['articleFeatureDescription'] + ' ' + ' '.join(house['tagList']) + (
            " " + house['detailDescription'] if house['detailDescription'] != "없음" else "")
        house_text_vector = self.vectorize_text_data(house_text)
        persona_text_vector = self.vectorize_text_data(persona['significant'])

        # 방 개수와 인원 수의 차이 계산
        room_count = self.extract_room_count(house)
        person_count = int(persona['person_count'].replace('명', '').split()[0])
        room_person_diff = room_count - person_count

        # 벡터 길이 일치화
        max_length = max(len(house_text_vector), len(persona_text_vector))
        house_text_vector = np.pad(house_text_vector, (0, max_length - len(house_text_vector)), 'constant')
        persona_text_vector = np.pad(persona_text_vector, (0, max_length - len(persona_text_vector)),
                                     'constant')

        # 벡터 결합
        house_vector = np.concatenate([persona_vector, house_text_vector, [room_person_diff]])
        persona_vector = np.concatenate([persona_vector, persona_text_vector, [0]])  # 여기서 [0] 대신 다른 값이 들어갈 수 있음

        return house_vector, persona_vector

    def recommend(self, persona, top_n=3):
        house_list = []
        selected_apt_names = set()  # 선택된 매물의 이름을 추적하는 집합

        # 필터링된 매물 정보 사용
        filtered_house_info = [house for house in self.house_info if
                               int(house['walkTime']) <= 10 and float(house['aptParkingCountPerHousehold']) > 0]

        for house in filtered_house_info:
            if house['aptName'] not in selected_apt_names:  # 매물 이름이 아직 선택되지 않았다면
                house_vector, persona_vector = self.vectorize_data(house, persona)
                similarity = cosine_similarity([house_vector], [persona_vector])
                house_list.append((similarity[0][0], house))
                selected_apt_names.add(house['aptName'])  # 매물 이름을 선택된 목록에 추가

        house_list.sort(key=lambda x: x[0], reverse=True)

        return house_list[:top_n]


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

    async def like(self, house_id):

        # db에서 좋아요를 누른 이력이 있는지 확인합니다.
        like = self.db.query(LikedHouse).filter(
            LikedHouse.user_id == self.user.id,
            LikedHouse.house_id == house_id
        ).first()

        # 이미 좋아요를 누른 이력이 있다면 is_deleted를 True로 변경합니다.
        if like and like.is_deleted == False:
            like.is_deleted = True
            save_db(like, self.db)

        elif like and like.is_deleted == True:
            like.is_deleted = False
            save_db(like, self.db)

        # 좋아요를 누른 이력이 없다면 새로운 데이터를 생성합니다.
        else:
            liked_house = LikedHouse(
                user_id=self.user.id,
                house_id=house_id
            )
            save_db(liked_house, self.db)

    async def recommendation_list(self, page):

        # Recommendation 테이블에서 삭제되지 않은 데이터를 페이지네이션 해서 가져옵니다.
        # 이 때 house_id를 이용하여 House 테이블에서 데이터를 가져옵니다.
        houses = self.db.execute(
            select(
                Recommendation.house_id,
                House.aptName,
                House.image_url,
                House.exposureAddress,
            ).join(
                House,
                Recommendation.house_id == House.id
            ).filter(
                Recommendation.user_id == self.user.id,
                Recommendation.is_deleted == False,
                House.is_deleted == False
            ).limit(5).offset((page - 1) * 5)
        ).all()

        # 사용자가 '좋아요'한 집의 ID를 세트로 생성
        liked_houses_set = {liked_house.house_id for liked_house in self.db.query(LikedHouse).filter(
            LikedHouse.user_id == self.user.id,
            LikedHouse.is_deleted == False
        )}

        # 가져온 집 정보에 '좋아요' 정보를 추가하여 반환
        return_houses = [{
            "house_id": house[0],
            "aptName": house[1],
            "image_url": house[2],
            "exposureAddress": house[3],
            "is_like": house[0] in liked_houses_set  # set를 사용하여 빠르게 확인
        } for house in houses]

        return return_houses

    async def list(self, page):
        # House 테이블과 Recommendation 테이블을 left join하고,
        # Recommendation 테이블의 house_id가 NULL인 경우만 필터링합니다.
        houses_query = select(
            House.id,
            House.aptName,
            House.image_url,
            House.exposureAddress
        ).outerjoin(
            Recommendation, and_(
                Recommendation.house_id == House.id,
                Recommendation.user_id == self.user.id,
                Recommendation.is_deleted == False
            )
        ).filter(
            Recommendation.house_id == None,  # Recommendation에 없는 House
            House.is_deleted == False
        ).limit(5).offset((page - 1) * 5)

        houses = self.db.execute(houses_query).all()

        # 사용자가 '좋아요'한 집 목록을 가져옵니다.
        liked_houses_query = select(LikedHouse.house_id).filter(
            LikedHouse.user_id == self.user.id
        )
        liked_houses = {house_id for (house_id,) in self.db.execute(liked_houses_query).all()}

        # 가져온 집 정보에 '좋아요' 정보를 추가하여 반환합니다.
        return_houses = [{
            "house_id": house[0],
            "aptName": house[1],
            "image_url": house[2],
            "exposureAddress": house[3],
            "is_like": house[0] in liked_houses
        } for house in houses]

        return return_houses


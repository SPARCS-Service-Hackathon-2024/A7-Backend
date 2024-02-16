import json
import aioredis
from fastapi import Depends, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
from app.db.database import get_db, get_current_user, save_db, get_redis_client
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
    def __init__(self, db: Session = Depends(get_db), user: User = Depends(get_current_user), redis: aioredis.Redis = Depends(get_redis_client)):
        self.db = db
        self.user = user
        self.redis = redis

    async def initailize(self) -> None:
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


    async def create(self, house_data: dict) -> House:
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

    async def like(self, house_id: int) -> None:

        status = False

        # db에서 좋아요를 누른 이력이 있는지 확인합니다.
        like = self.db.query(LikedHouse).filter(
            LikedHouse.user_id == self.user.id,
            LikedHouse.house_id == house_id
        ).first()

        # 이미 좋아요를 누른 이력이 있다면 is_deleted를 True로 변경합니다.
        if like and like.is_deleted == False:
            like.is_deleted = True
            save_db(like, self.db)
            status = False

        elif like and like.is_deleted == True:
            like.is_deleted = False
            save_db(like, self.db)
            status = True

        # 좋아요를 누른 이력이 없다면 새로운 데이터를 생성합니다.
        else:
            liked_house = LikedHouse(
                user_id=self.user.id,
                house_id=house_id
            )
            save_db(liked_house, self.db)
            status = True

        await self.redis.delete(f"list:{self.user.id}:*")

        return {"is_like": status}

    async def detail(self, house_id: int) -> dict:

        house = await self.redis.get(f"house:{self.user.id}:{house_id}")
        if house:
            return json.loads(house)

        house = self.db.query(House).filter(
            House.id == house_id,
            House.is_deleted == False
        ).first()

        reason = self.db.query(Recommendation.reason).filter(
            Recommendation.user_id == self.user.id,
            Recommendation.house_id == house_id
        ).first()

        if not house:
            return None

        # 좋아요 한 기록이 있는지 확인

        liked_house = self.db.query(LikedHouse).filter(
            LikedHouse.user_id == self.user.id,
            LikedHouse.house_id == house_id
        ).first()

        is_like = False
        if liked_house:
            is_like = True

        house = {
            "id": house.id,
            "aptName": house.aptName,
            "exposureAddress": house.exposureAddress,
            "reason": reason.reason if reason else None,
            "tagList": house.tagList,
            "aptHeatMethodTypeName": house.aptHeatMethodTypeName,
            "aptHeatFuelTypeName": house.aptHeatFuelTypeName,
            "aptHouseholdCount": house.aptHouseholdCount,
            "schoolName": house.schoolName,
            "organizationType": house.organizationType,
            "walkTime": house.walkTime,
            "studentCountPerTeacher": house.studentCountPerTeacher,
            "is_like": is_like,
            "image_url": house.image_url
        }

        await self.redis.set(f"house:{self.user.id}:{house_id}", json.dumps(house, ensure_ascii=False) , ex=3600)

        return house

    async def fetch_rec_houses_data(self, page) -> list:
        houses_query = select(
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
        houses = self.db.execute(houses_query).all()

        liked_houses_set = {liked_house.house_id for liked_house in self.db.query(LikedHouse).filter(
            LikedHouse.user_id == self.user.id,
            LikedHouse.is_deleted == False
        )}

        return [{
            "house_id": house[0],
            "aptName": house[1],
            "image_url": house[2],
            "exposureAddress": house[3],
            "is_like": house[0] in liked_houses_set
        } for house in houses]

    async def cache_recommendation_list(self, page) -> None:
        redis_key = f"list:{self.user.id}:rec:{page}"
        return_houses = await self.fetch_rec_houses_data(page)
        await self.redis.set(redis_key, json.dumps(return_houses, ensure_ascii=False), ex=1800)


    async def recommendation_list(self, background_tasks: BackgroundTasks,  page: int) -> list:

        # backgroud task를 사용하여 다음 페이지의 데이터를 미리 캐싱합니다.
        background_tasks.add_task(self.cache_recommendation_list, page + 1)

        redis_key = f"list:{self.user.id}:rec:{page}"
        cached_data = await self.redis.get(redis_key)

        if cached_data:
            return json.loads(cached_data)

        return_houses = await self.fetch_rec_houses_data(page)

        # redis에 데이터를 저장합니다.
        await self.redis.set(redis_key, json.dumps(return_houses, ensure_ascii=False), ex=1800)



        return return_houses

    async def fetch_house_list(self, page: int) -> list:

        # House 테이블과 Recommendation 테이블을 left join하고,
        # Recommendation 테이블의 house_id가 NULL인 경우만 필터링합니다.
        houses_query = select(
            House.id,
            House.aptName,
            House.image_url,
            House.exposureAddress
        ).filter(
            House.is_deleted == False
        ).limit(5).offset((page - 1) * 5)
        houses = self.db.execute(houses_query).all()

        # 사용자가 '좋아요'한 집 목록을 가져옵니다.
        liked_houses_set = {liked_house.house_id for liked_house in self.db.query(LikedHouse).filter(
            LikedHouse.user_id == self.user.id,
            LikedHouse.is_deleted == False
        )}

        # 가져온 집 정보에 '좋아요' 정보를 추가하여 반환합니다.
        return [{
            "house_id": house[0],
            "aptName": house[1],
            "image_url": house[2],
            "exposureAddress": house[3],
            "is_like": house[0] in liked_houses_set
        } for house in houses]

    async def cache_house_list(self, page: int) -> None:
        redis_key = f"list:{self.user.id}:house:{page}"
        return_houses = await self.fetch_house_list(page)
        await self.redis.set(redis_key, json.dumps(return_houses, ensure_ascii=False), ex=1800)

    async def list(self, background_tasks: BackgroundTasks, page: int) -> list:

        # backgroud task를 사용하여 다음 페이지의 데이터를 미리 캐싱합니다.
        background_tasks.add_task(self.cache_house_list, page + 1)

        # redis에 저장된 데이터를 가져옵니다.
        redis_key = f"list:{self.user.id}:house:{page}"
        redis_data = await self.redis.get(redis_key)

        if redis_data:
            return json.loads(redis_data)

        return_houses = await self.fetch_house_list(page)

        # redis에 데이터를 저장합니다.
        await self.redis.set(redis_key, json.dumps(return_houses, ensure_ascii=False), ex=1800)

        return return_houses
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np


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

    def recommend(self, persona, top_n=100):
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


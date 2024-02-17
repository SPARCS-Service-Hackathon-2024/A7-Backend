# A7-Backend

## 프로젝트 설명
SPARCS Service Hackathon 2024 는 대전광역시와 KAIST가 주최하고,  KAIST 총학생회 산하 특별기구 SPARCS가 주관하는 해커톤입니다.

## 프로젝트 소개

자세한 내용은 [여기](https://github.com/SPARCS-Service-Hackathon-2024/A7-Repo) 에서 확인해주세요.

![](https://github.com/SPARCS-Service-Hackathon-2024/A7-Backend/assets/89565530/a3eb6847-93fd-4c5c-b0e1-d1f475c937a5)

## MVP

### 기능

- 입력한 정보를 바탕으로 사용자에게 맞는 집을 추천해줍니다.
- 추천된 집을 클릭하면 집의 상세 정보를 볼 수 있습니다. 이때, 추천받은 이유를 확인할 수 있습니다.
- 상세 정보를 확인한 후, 원하는 기간만큼 예약을 할 수 있습니다.

### Tech Stack

- FastAPI를 사용해서 백엔드를 구축했습니다.
- Github Actions를 사용해서 CI/CD를 구축했습니다.
- Docker를 활용한 무중단 배포를 구축했습니다.
- NCLOUD를 사용해서 서버를 배포했습니다.
- Redis를 사용해서 데이터를 캐싱했습니다.

### API

![](https://github.com/SPARCS-Service-Hackathon-2024/A7-Backend/assets/89565530/1c1647e8-0882-42a8-a888-9bde366ebc5d)

- /auth/login : 사용자 인증 후 토큰을 발급합니다. db에 저장되지 않은 유저는 자동으로 회원가입 후 토큰을 발급합니다.
- /house/initailize : 집 데이터를 초기화합니다. app/servie/apartment_info.jsonl 파일을 읽어와서 데이터베이스에 저장합니다.
- /chat : 직접 제작한 집 추천 llm 모델을 사용해서 사용자에게 맞는 집을 추천해줍니다. [huggingface 링크](https://huggingface.co/taewan2002/srabwayu-rec-7b)
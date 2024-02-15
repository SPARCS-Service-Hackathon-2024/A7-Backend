from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.request import House
from app.schemas.response import ApiResponse
from app.service.house import HouseService

router = APIRouter(prefix="/house")

@router.get("/initailize", response_model=ApiResponse, tags=["House"])
async def get_house_initailize(
    house_service: Annotated[HouseService, Depends()]
):
    await house_service.initailize()
    return ApiResponse()

@router.post("/create", response_model=ApiResponse, tags=["House"])
async def post_house_create(
    house_data: House,
    house_service: Annotated[HouseService, Depends()]
):
    print(house_data.house_info)
    return ApiResponse()
@router.patch("/like/{house_id}", response_model=ApiResponse, tags=["House"])
async def patch_house_like(
    house_id: int,
    house_service: Annotated[HouseService, Depends()]
):
    return ApiResponse(data=await house_service.like(house_id))

@router.get("/recommendation/list/{page}", response_model=ApiResponse, tags=["House"])
async def get_house_recommendation(
    page: int,
    house_service: Annotated[HouseService, Depends()]
):
    return ApiResponse(data=await house_service.recommendation_list(page))

@router.get("/list/{page}", response_model=ApiResponse, tags=["House"])
async def get_house_list(
    page: int,
    house_service: Annotated[HouseService, Depends()]
):
    return ApiResponse(data=await house_service.list(page))

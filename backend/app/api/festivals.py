from fastapi import APIRouter, Query

from app.schemas.common import SuccessEnvelope
from app.schemas.festival import Festival
from app.services.festivals import list_festivals


router = APIRouter(prefix="/festivals", tags=["festivals"])


@router.get("", response_model=SuccessEnvelope[list[Festival]])
def read_festivals(
    region: str = "all",
    year: int | None = Query(None, ge=1, le=9999),
    month: int | None = Query(None, ge=1, le=12),
):
    data = list_festivals(region=region, year=year, month=month)
    return SuccessEnvelope[list[Festival]](data=data, message="축제 목록을 조회했습니다.")

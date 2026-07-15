from datetime import date

from app.schemas.common import CamelModel


class Festival(CamelModel):
    content_id: str
    title: str
    address: str
    detail_address: str
    telephone: str
    longitude: float | None
    latitude: float | None
    image_url: str
    region: str
    start_date: date
    end_date: date

from pydantic import BaseModel

class MediaCard(BaseModel):
    """媒體卡片資料。"""
    id: str
    title: str
    desc: str
    tag: str
    url: str
    media_type: str = 'image'
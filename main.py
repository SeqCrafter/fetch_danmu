from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Annotated, List, Any
from urllib.parse import unquote_plus
from functions import (
    get_danmu_by_url,
    get_danmu_by_id,
    get_danmu_by_title,
    get_danmu_by_title_caiji,
)
from tortoise.contrib.fastapi import register_tortoise

try:
    from settings import TORTOISE_ORM
except ImportError as e:
    if "No module named 'app'" in str(e):
        import sys
        from pathlib import Path

        _workdir = Path(__file__).parent.parent.as_posix()
        if _workdir not in sys.path:
            sys.path.append(_workdir)
        from settings import TORTOISE_ORM
    else:
        raise e


class DanmukuResponse(BaseModel):
    code: int
    name: str
    danmu: int
    danmuku: List[List[Any]]


# 创建 FastAPI 应用实例
app = FastAPI(
    title="免费弹幕抓取",
    description="This is a free danmuku server.",
    version="1.0.0",
    contact={
        "name": "API Support",
        "url": "https://github.com/SeqCrafter/fetch_danmu",
        "email": "sdupan2015@gmail.com",
    },
)

register_tortoise(app, config=TORTOISE_ORM)
# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/url", response_model=DanmukuResponse)
async def danmu_by_url(
    url: Annotated[str, Query(description="视频URL地址", pattern=r"^https?://.*$")],
):
    """通过URL直接获取弹幕"""
    # URL解码
    decoded_url = unquote_plus(url)
    danmu_data = await get_danmu_by_url(decoded_url)
    return {
        "code": 0,
        "name": decoded_url,
        "danmu": len(danmu_data),
        "danmuku": danmu_data,
    }


@app.get("/api/douban_id", response_model=DanmukuResponse)
async def danmu_by_douban_id(
    douban_id: Annotated[int, Query(description="豆瓣ID")],
    episode_number: Annotated[int, Query(description="集数")],
):
    all_danmu = await get_danmu_by_id(str(douban_id), str(episode_number))
    return {
        "code": 0,
        "name": str(douban_id),
        "danmu": len(all_danmu),
        "danmuku": all_danmu,
    }


@app.get("/api/title", response_model=DanmukuResponse)
async def danmu_by_title(
    title: Annotated[str, Query(description="视频名称")],
    season_number: Annotated[int, Query(description="季数")],
    season: Annotated[bool, Query(description="是否为连续剧, true/false")],
    episode_number: Annotated[int, Query(description="集数")],
):
    """通过视频名称直接获取弹幕"""

    all_danmu = await get_danmu_by_title(
        title, str(season_number), season, str(episode_number)
    )
    return {
        "code": 0,
        "name": title,
        "danmu": len(all_danmu),
        "danmuku": all_danmu,
    }


@app.get("/api/test/title", response_model=DanmukuResponse)
async def danmu_by_title_caiji(
    title: Annotated[str, Query(description="视频名称")],
    season: Annotated[bool, Query(description="是否为连续剧, true/false")],
    episode_number: Annotated[int, Query(description="集数")],
    season_number: Annotated[str | None, Query(description="季数")] = None,
):
    """通过视频名称直接获取弹幕（测试版本）"""

    if season:
        all_danmu = await get_danmu_by_title_caiji(title, episode_number)
    else:
        all_danmu = await get_danmu_by_title_caiji(title, 1)
    ## to avoid type error
    print(season_number)

    return {
        "code": 0,
        "name": title,
        "danmu": len(all_danmu),
        "danmuku": all_danmu,
    }


if __name__ == "__main__":
    from granian.server import Server as Granian
    from granian.constants import Interfaces

    granian_app = Granian(
        target=app,
        factory=True,
        address="0.0.0.0",
        port=8080,
        interface=Interfaces.ASGI,
    )

    granian_app.serve()

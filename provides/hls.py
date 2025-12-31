## try to fetch danmu from other platform

from curl_cffi import requests
from typing import List, Any


async def get_danmu_from_hls(url: str) -> List[List[Any]]:
    danmuku_url = f"https://api.danmu.icu/?ac=dm&url={url}"
    async with requests.AsyncSession() as client:
        res = await client.get(danmuku_url, impersonate="chrome124")
        if res.status_code != 200:
            raise Exception("Failed to get danmu from hls")
        data = res.json()
        if "danmuku" not in data or not data["danmuku"]:
            raise Exception("Failed to get danmu from hls")
        else:
            return data["danmuku"]

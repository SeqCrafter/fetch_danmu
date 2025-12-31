## try to fetch danmu from other platform

import asyncio
from curl_cffi import requests
from typing import List, Any


async def get_danmu_combined(url: str) -> List[List[Any]]:
    """并行请求两个接口，忽略失败，合并结果"""

    async def fetch_safe(endpoint_url: str) -> List[List[Any]]:
        try:
            async with requests.AsyncSession() as client:
                res = await client.get(
                    endpoint_url, impersonate="chrome124", timeout=10
                )
                if res.status_code == 200:
                    data = res.json()
                    return data.get("danmuku") or []
        except Exception:
            pass
        return []

    hls_url = f"https://dmku.hls.one/?ac=dm&url={url}"
    icu_url = f"https://api.danmu.icu/?ac=dm&url={url}"

    tasks = [fetch_safe(hls_url), fetch_safe(icu_url)]
    results = await asyncio.gather(*tasks)

    # 合并结果
    combined = []
    for r in results:
        combined.extend(r)
    return combined

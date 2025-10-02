import asyncio
from typing import List, Optional
from curl_cffi import requests


def time_to_second(time: list[str]) -> int:
    s = 0
    m = 1
    for d in time[::-1]:
        s += m * int(d)
        m *= 60
    return s


async def get_link(client: requests.AsyncSession, url: str) -> List[str]:
    api_video_info = "https://pcweb.api.mgtv.com/video/info"
    api_danmaku = "https://galaxy.bz.mgtv.com/rdbarrage"
    _u = url.split(".")[-2].split("/")
    if len(_u) < 2:
        return []
    cid = _u[-2]
    vid = _u[-1]
    params = {
        "cid": cid,
        "vid": vid,
    }
    res = await client.get(url=api_video_info, params=params)
    _time = res.json().get("data", {}).get("info", {}).get("time")
    if not _time or ":" not in _time:
        return []
    end_time = time_to_second(_time.split(":")) * 1000

    return [
        f"{api_danmaku}?vid={vid}&cid={cid}&time={item}"
        for item in range(0, end_time, 60 * 1000)
    ]


def parse_data(data: dict) -> list[dict]:
    barrage_list = []
    if data.get("data", {}).get("items", []) is None:
        return []
    for item in data.get("data", {}).get("items", []):
        parsed_data = {}
        parsed_data["text"] = item.get("content", "")
        parsed_data["time"] = item.get("time", 0) / 1000
        parsed_data["position"] = "right"
        parsed_data["color"] = "#FFFFFF"
        parsed_data["size"] = "25px"
        # parsed_data["border"] = False
        # parsed_data["style"] = {}
        barrage_list.append(parsed_data)
    return barrage_list


async def fetch_single_barrage(client: requests.AsyncSession, param: str) -> list[dict]:
    res = await client.get(param)
    return parse_data(res.json())


async def read_barrage(client: requests.AsyncSession, params: list[str]) -> list[dict]:
    tasks = [fetch_single_barrage(client, param) for param in params]
    results = await asyncio.gather(*tasks)
    barrage_list = []
    for res in results:
        if res:
            barrage_list.extend(res)
    return barrage_list


async def get_mgtv_danmu(url: str) -> list[dict]:
    danmu_list = []
    if "mgtv.com" in url:
        async with requests.AsyncSession() as client:
            urls = await get_link(client, url)
            danmu_list = await read_barrage(client, urls)
    return danmu_list


async def get_mgtv_episode_url(
    url: str, url_dict: Optional[dict] = None, page: int = 1
) -> dict[str, str]:
    if "mgtv.com" not in url:
        if url_dict is None:
            url_dict = {}
        video_id = url.split(".")[-2].split("/")[-1]
        _data_url = f"https://pcweb.api.mgtv.com/episode/list?version=5.5.35&video_id={video_id}&page={page}&size=50"
        async with requests.AsyncSession() as session:
            res = await session.get(_data_url, impersonate="chrome124")
            for item in res.json().get("data", {}).get("list", []):
                if item.get("t1") not in url_dict.keys():
                    url_dict[item.get("t1")] = "https://www.mgtv.com" + item.get("url")
            if len(url_dict.keys()) < res.json().get("data", {}).get(
                "total", len(url_dict.keys())
            ):
                page += 1
                return await get_mgtv_episode_url(url, url_dict, page)
            return url_dict
    return {}


if __name__ == "__main__":
    url = (
        "https://www.mgtv.com/b/755976/23118095.html?fpa=1261&fpos=&lastp=ch_tv&cpid=4"
    )
    asyncio.run(get_mgtv_danmu(url))

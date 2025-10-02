from typing import List
from curl_cffi import requests
import re
import parsel
from urllib.parse import urljoin
import asyncio
import json


async def get_link(url, client: requests.AsyncSession = None) -> List[str]:
    api_danmaku_base = "https://dm.video.qq.com/barrage/base/"
    api_danmaku_segment = "https://dm.video.qq.com/barrage/segment/"
    res = await client.get(url)
    sel = parsel.Selector(res.text)
    title = sel.xpath("//title/text()").get().split("_")[0]
    vid = re.findall(f'"title":"{title}","vid":"(.*?)"', res.text)
    if vid:
        vid = vid[-1]
    if not vid:
        vid = re.search(r"/([a-zA-Z0-9]+)\.html", url)
        if vid:
            vid = vid.group(1)
    if not vid:
        print("parse vid failed, check url")
        return []
    res = await client.get(urljoin(api_danmaku_base, vid))
    if res.status_code != 200:
        print("fetch barrage failed")
        return []
    segment_indices = list(res.json().get("segment_index", {}).values())
    links = [
        urljoin(api_danmaku_segment, vid + "/" + item.get("segment_name", "/"))
        for item in segment_indices
    ]
    return links


def parse_data(data: dict) -> List[dict]:
    barrage_list = []
    for item in data.get("barrage_list", []):
        parsed_data = {}
        parsed_data["text"] = item.get("content", "")
        parsed_data["time"] = float(item.get("time_offset", 0)) / 1000
        parsed_data["position"] = "right"
        parsed_data["color"] = "#ffffff"
        parsed_data["size"] = "25px"
        # parsed_data["border"] = False
        # parsed_data["style"] = {}
        if item.get("content_style") != "":
            content_style = json.loads(item.get("content_style"))
            parsed_data["color"] = content_style.get("color", "#ffffff")
        barrage_list.append(parsed_data)
    return barrage_list


async def fetch_single_barrage(client: requests.AsyncSession, url: str) -> List[dict]:
    """异步获取单个URL的弹幕数据"""
    try:
        res = await client.get(url)
        return parse_data(res.json())
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []


async def read_barrage(
    urls: List[str], client: requests.AsyncSession = None
) -> List[dict]:
    """异步并发获取所有URL的弹幕数据"""
    barrage_list = []

    tasks = [fetch_single_barrage(client, url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, list):
            barrage_list.extend(result)
        else:
            print(f"Error in task: {result}")
    return barrage_list


async def get_tencent_danmu(url: str) -> list[dict]:
    danmu_list = []
    if "v.qq.com" in url:
        async with requests.AsyncSession() as client:
            urls = await get_link(url, client=client)
            danmu_list = await read_barrage(urls, client=client)
    return danmu_list


async def get_tencent_episode_url(url: str) -> dict[str, str]:
    if "v.qq.com" in url:
        async with requests.AsyncSession() as client:
            res = await client.get(url)
            sel = parsel.Selector(res.text)
            title = sel.xpath("//title/text()").get().split("_")[0]
            vid = re.findall(f'"title":"{title}","vid":"(.*?)"', res.text)
            if vid:
                vid = vid[-1]
            if not vid:
                vid = re.search(r"/([a-zA-Z0-9]+)\.html", url)
                if vid:
                    vid = vid.group(1)
            cid = re.findall('"cid":"(.*?)"', res.text)[0]
            if not vid:
                print("解析vid失败, 请检查链接是否正确")
                return {}

            url = "https://pbaccess.video.qq.com/trpc.universal_backend_service.page_server_rpc.PageServer/GetPageData"
            data = {
                "page_params": {
                    "req_from": "web_vsite",
                    "page_id": "vsite_episode_list",
                    "page_type": "detail_operation",
                    "id_type": "1",
                    "page_size": "",
                    "cid": cid,
                    "vid": vid,
                    "lid": "",
                    "page_num": "",
                    "page_context": "episode_begin=1&episode_end=100&episode_step=1&page_num=0&page_size=100",
                    "detail_page_type": "1",
                },
                "has_cache": 1,
            }
            res = await client.post(
                url,
                json=data,
                headers={
                    "referer": "https://v.qq.com/",
                    "Cookie": "video_platform=2; vversion_name=8.2.95",
                },
            )
            json_data = res.json().get("data", {})
            data_list = (
                json_data.get("module_list_datas", [{}])[0]
                .get("module_datas", [{}])[0]
                .get("item_data_lists", {})
                .get("item_datas", [])
            )
            url_dict = {}
            for item in data_list:
                item_params = item.get("item_params")
                url_dict[f"{item_params.get('title')}"] = (
                    f"https://v.qq.com/x/cover/{item_params.get('cid')}/{item_params.get('vid')}.html"
                )
            return url_dict
    return {}


if __name__ == "__main__":
    url = "https://v.qq.com/x/cover/mzc00200iyue5he/k4101w92tew.html"
    asyncio.run(get_tencent_danmu(url))

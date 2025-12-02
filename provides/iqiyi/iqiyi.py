from typing import List
from curl_cffi import requests
import re
import hashlib
import brotlicffi as brotli
from ..utils import resolve_url_query
from jsonpath_ng import parse as jsonpath_parse

# import .iqiyidm_pb2 as Iqiyidm_pb2
from . import iqiyidm_pb2 as Iqiyidm_pb2

# import iqiyidm_pb2 as Iqiyidm_pb2
import asyncio
import time


base_headers = {"Accept-Encoding": "gzip,deflate,compress"}


def get_md5(str: str) -> str:
    md5 = hashlib.md5()
    md5.update(str.encode("utf-8"))
    return md5.hexdigest()


async def get_link(url, client: requests.AsyncSession) -> List[str]:
    url_list = []
    res = await client.get(url, headers=base_headers, impersonate="chrome124")
    js_url = re.findall(
        r'<script src="(.*?)" referrerpolicy="no-referrer-when-downgrade">',
        res.text,
    )
    if len(js_url) == 0:
        js_url = "//mesh.if.iqiyi.com/player/lw/lwplay/accelerator.js?apiVer=3"
    else:
        js_url = js_url[0]
    res = await client.get(
        f"https:{js_url}", headers={"referer": url}, impersonate="chrome124"
    )
    tv_id = re.findall('"tvId":([0-9]+)', res.text)[0]
    video_duration = int(re.findall('"videoDuration":([0-9]+)', res.text)[0])
    step_length = 60
    max_index = int(video_duration / step_length) + 1
    for index in range(1, max_index + 1):
        i = f"{tv_id}_{step_length}_{index}cbzuw1259a"
        s = get_md5(i)[-8:]
        o = f"{tv_id}_{step_length}_{index}_{s}.br"
        url_list.append(
            f"https://cmts.iqiyi.com/bullet/{tv_id[-4:-2]}/{tv_id[-2:]}/{o}"
        )
    return url_list


def parse_data(data: list) -> list[dict]:
    barrage_list = []
    for entry in data:
        for item in entry.bulletInfo:
            parsed_data = {}
            parsed_data.setdefault("text", item.content)
            parsed_data.setdefault("time", float(item.showTime))
            parsed_data.setdefault("color", f"#{item.a8}")
            parsed_data.setdefault("size", "25px")
            parsed_data["position"] = "right"
            # parsed_data["border"] = False
            barrage_list.append(parsed_data)
    return barrage_list


def decompress_data(content: bytes) -> list:
    out = brotli.decompress(content)
    danmu = Iqiyidm_pb2.Danmu()
    danmu.ParseFromString(out)
    return danmu.entry


async def fetch_single_barrage(client: requests.AsyncSession, url: str) -> list[dict]:
    try:
        res = await client.get(url, headers=base_headers, impersonate="chrome124")
        return parse_data(decompress_data(res.content))
    except Exception as e:
        print(f"获取弹幕失败 {url}: {e}")
        return []


async def read_barrage(urls: List[str], client: requests.AsyncSession) -> List[dict]:
    barrage_list = []
    tasks = [fetch_single_barrage(client, url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            print(f"任务执行出错: {result}")
        else:
            barrage_list.extend(result)
    return barrage_list


async def get_iqiyi_danmu(url: str) -> list[dict]:
    danmu_list = []
    if "iqiyi.com" in url:
        async with requests.AsyncSession() as client:
            urls = await get_link(url, client=client)
            danmu_list = await read_barrage(urls, client=client)
    return danmu_list


async def get_iqiyi_episode_url(url: str) -> dict[str, str]:
    if "iqiyi.com" in url:
        async with requests.AsyncSession() as client:
            try:
                query = resolve_url_query(url)
                if query.get("tvid"):
                    tv_id = query.get("tvid")[0]
                else:
                    res = await client.get(
                        url, headers=base_headers, impersonate="chrome124"
                    )
                    js_url_matches = re.findall(
                        r'"[^"]*accelerator\.js[^"]*"',
                        res.text,
                    )
                    if not js_url_matches:
                        return {}
                    js_url = js_url_matches[0]
                    js_url = "https:" + js_url.replace('"', "")
                    res = await client.get(
                        js_url,
                        headers={"referer": url},
                        impersonate="chrome124",
                    )
                    tv_id_matches = re.findall(r'"tvId":(\d+)', res.text)
                    if not tv_id_matches:
                        return {}
                    tv_id = tv_id_matches[0]
                params = f"entity_id={tv_id}&src=pca_tvg&timestamp={int(time.time())}&secret_key=howcuteitis"
                url = f"https://mesh.if.iqiyi.com/tvg/v2/lw/base_info?{params}&sign={get_md5(params).upper()}"
                res = await client.get(
                    url, headers={"referer": url}, impersonate="chrome124"
                )
                jsonpath_expr = jsonpath_parse("$..bk_title")
                matches = [match for match in jsonpath_expr.find(res.json())]
                result_objs = [
                    match.context.value for match in matches if match.value == "选集"
                ]
                url_dict = {}
                for result_obj in result_objs:
                    d = (
                        result_obj.get("data", {})
                        .get("data", [{}])[0]
                        .get("videos", {})
                    )
                    if isinstance(d, str):
                        _res = await client.get(d)
                        d = _res.json().get("data", {}).get("videos", {})
                    d = d.get("feature_paged", {})
                    for k in list(d.keys()):
                        for item in d[k]:
                            if item.get("page_url"):
                                url_dict[f"{item.get('album_order')}"] = item.get(
                                    "page_url"
                                )
                return url_dict
            except Exception:
                return {}
    return {}


if __name__ == "__main__":
    url = "https://www.iqiyi.com/v_26ecr2p42o0.html?vfm=m_331_dbdy&fv=4904d94982104144a1548dd9040df241&amp;subtype=9&amp;type=online-video&amp;link2key=52541a56ed"
    # asyncio.run(get_iqiyi_danmu(url))
    # res = asyncio.run(get_iqiyi_danmu(url))
    res = asyncio.run(get_iqiyi_episode_url(url))
    print(res)

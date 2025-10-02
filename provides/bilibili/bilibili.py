from typing import List
import re
from curl_cffi import requests
import urllib.parse
import time
from hashlib import md5
from functools import reduce
import asyncio
import provides.bilibili.bilibilidm_pb2 as Danmaku
from provides.utils import int_to_hex_color
from typing import Dict, Any
# import bilibilidm_pb2 as Danmaku

mixinKeyEncTab = [
    46,
    47,
    18,
    2,
    53,
    8,
    23,
    32,
    15,
    50,
    10,
    31,
    58,
    3,
    45,
    35,
    27,
    43,
    5,
    49,
    33,
    9,
    42,
    19,
    29,
    28,
    14,
    39,
    12,
    38,
    41,
    13,
    37,
    48,
    7,
    16,
    24,
    55,
    40,
    61,
    26,
    17,
    0,
    1,
    60,
    51,
    30,
    4,
    22,
    25,
    54,
    21,
    56,
    59,
    6,
    63,
    57,
    62,
    11,
    36,
    20,
    34,
    44,
    52,
]


async def getWbiKeys() -> tuple[str, str]:
    "获取最新的 img_key 和 sub_key"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Referer": "https://www.bilibili.com/",
    }
    async with requests.AsyncSession() as client:
        resp = await client.get(
            "https://api.bilibili.com/x/web-interface/nav", headers=headers
        )
        resp.raise_for_status()
        json_content = resp.json()
        img_url: str = json_content["data"]["wbi_img"]["img_url"]
        sub_url: str = json_content["data"]["wbi_img"]["sub_url"]
        img_key = img_url.rsplit("/", 1)[1].split(".")[0]
        sub_key = sub_url.rsplit("/", 1)[1].split(".")[0]
        return img_key, sub_key


def getMixinKey(orig: str) -> str:
    "对 imgKey 和 subKey 进行字符顺序打乱编码"
    return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, "")[:32]


def encWbi(params: dict, img_key: str, sub_key: str) -> Dict[str, Any]:
    "为请求参数进行 wbi 签名"
    mixin_key = getMixinKey(img_key + sub_key)
    curr_time = round(time.time())
    params["wts"] = curr_time  # 添加 wts 字段
    params = dict(sorted(params.items()))  # 按照 key 重排参数
    # 过滤 value 中的 "!'()*" 字符
    params = {
        k: "".join(filter(lambda chr: chr not in "!'()*", str(v)))
        for k, v in params.items()
    }
    query = urllib.parse.urlencode(params)  # 序列化参数
    wbi_sign = md5((query + mixin_key).encode()).hexdigest()  # 计算 w_rid
    params["w_rid"] = wbi_sign
    return params


async def get_link(url: str, client: requests.AsyncSession = None) -> List[str]:
    api_epid_cid = "https://api.bilibili.com/pgc/view/web/season"
    img_key, sub_key = await getWbiKeys()
    if url.find("bangumi/") != -1 and url.find("ep") != -1:
        epid_matches = re.findall(r"ep(\d+)", url)
        if not epid_matches:
            print("无法从URL中提取epid")
            return []
        epid = epid_matches[0]
        params = {"ep_id": epid}

        res = await client.get(api_epid_cid, params=params, impersonate="chrome110")
        res_json = res.json()
        if res_json.get("code") != 0:
            print("获取番剧信息失败")
            return []
        target_episode = None
        for episode in res_json.get("result", {}).get("episodes", []):
            if episode.get("id", 0) == int(epid):
                target_episode = episode
                break
        if target_episode:
            ret_data = []
            for i in range(1, 20):
                params = {
                    "type": 1,
                    "oid": target_episode.get("cid"),
                    "segment_index": i,
                }
                signed_params = encWbi(params=params, img_key=img_key, sub_key=sub_key)
                ret_data.append(
                    "https://api.bilibili.com/x/v2/dm/wbi/web/seg.so?"
                    + urllib.parse.urlencode(signed_params)
                )
            return ret_data
        return []


def parse_data(data) -> List[Dict[str, Any]]:
    barrage_list = []
    for elem in data.elems:
        parsed_data = {}
        parsed_data.setdefault("text", elem.content)
        parsed_data.setdefault("time", float(elem.progress / 1000))
        parsed_data.setdefault("color", int_to_hex_color(int(elem.color)))
        parsed_data.setdefault("size", f"{elem.fontsize}px")
        # parsed_data.setdefault("id", elem.idStr)
        mode = 0
        match elem.mode:
            case 1 | 2 | 3:
                mode = "right"
            case 4:
                mode = "bottom"
            case 5:
                mode = "top"
        parsed_data.setdefault("position", mode)
        # parsed_data["border"] = False
        barrage_list.append(parsed_data)
    return barrage_list


def decompress_data(content):
    danmaku_seg = Danmaku.DmSegMobileReply()
    danmaku_seg.ParseFromString(content)
    return danmaku_seg


async def fetch_single_barrage(
    url: str, client: requests.AsyncSession
) -> List[dict[str, Any]]:
    res = await client.get(url, impersonate="chrome110")
    return parse_data(decompress_data(res.content))


async def read_barrage(
    urls: List[str], client: requests.AsyncSession = None
) -> List[dict[str, Any]]:
    tasks = [fetch_single_barrage(url, client=client) for url in urls]
    results = await asyncio.gather(*tasks)
    barrage_list = []
    for result in results:
        barrage_list.extend(result)
    return barrage_list


async def get_bilibili_danmu(url: str) -> List[Dict[str, Any]]:
    danmu_list = []
    if "bilibili.com" in url:
        async with requests.AsyncSession() as client:
            urls = await get_link(url, client=client)
            danmu_list = await read_barrage(urls, client=client)
    return danmu_list


async def get_bilibili_episode_url(url: str) -> Dict[str, str]:
    url_dict = {}
    if "bilibili.com" in url:
        api_epid_cid = "https://api.bilibili.com/pgc/view/web/season"
        async with requests.AsyncSession() as client:
            if url.find("bangumi/") != -1 and url.find("ep") != -1:
                epid_matches = re.findall(r"ep(\d+)", url)
                if not epid_matches:
                    return url_dict
                epid = epid_matches[0]
                params = {"ep_id": epid}
                res = await client.get(
                    url=api_epid_cid, params=params, impersonate="chrome110"
                )
                res_json = res.json()
                for item in res_json.get("result", {}).get("episodes", []):
                    if item.get("section_type") == 0:
                        url_dict[str(item.get("title"))] = item.get("share_url")
    return url_dict


if __name__ == "__main__":
    url = "https://www.bilibili.com/bangumi/play/ep1231553?spm_id_from=333.337.0.0&from_spmid=666.25.episode.0"
    # asyncio.run(get_bilibili_danmu(url))
    res = asyncio.run(get_bilibili_danmu(url))
    print(res)

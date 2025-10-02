import re
from typing import List, Optional
from curl_cffi import requests
import time
import base64
import json
import hashlib
import asyncio  # 新增


async def get_cna(client: requests.AsyncSession) -> None:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }
    url = "https://log.mmstat.com/eg.js"
    await client.get(url, headers=headers)


async def get_tk_enc(client: requests.AsyncSession) -> bool:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }
    res = await client.get(
        url="https://acs.youku.com/h5/mtop.com.youku.aplatform.weakget/1.0/?jsv=2.5.1&appKey=24679788",
        headers=headers,
    )
    if "_m_h5_tk" in res.cookies.keys() and "_m_h5_tk_enc" in res.cookies.keys():
        return True
    return False


async def create_client() -> requests.AsyncSession:
    client = requests.AsyncSession()
    client.headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }
    await get_cna(client)
    await get_tk_enc(client)
    return client


async def get_vinfos_by_video_id(client: requests.AsyncSession, video_id: str) -> float:
    url = "https://openapi.youku.com/v2/videos/show.json"
    params = {
        "client_id": "53e6cc67237fc59a",
        "video_id": video_id,
        "package": "com.huawei.hwvplayer.youku",
        "ext": "show",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }

    res = await client.get(url, params=params, headers=headers)
    return res.json().get("duration")


def get_msg_sign(msg_base64: str) -> str:
    secret_key = "MkmC9SoIw6xCkSKHhJ7b5D2r51kBiREr"
    combined_msg = msg_base64 + secret_key
    hash_object = hashlib.md5(combined_msg.encode())
    return hash_object.hexdigest()


def yk_t_sign(token: str, t: str, appkey: str, data: str) -> str:
    text = "&".join([token, t, appkey, data])
    md5_hash = hashlib.md5(text.encode())
    return md5_hash.hexdigest()


async def get_vid_list(client: requests.AsyncSession, url: str) -> List[dict[str, str]]:
    if "vid=" in url:
        # 从URL参数中提取vid
        vid_match = re.search(r"vid=([^&=]+)", url)
        if vid_match:
            # 处理可能的URL编码
            video_id = vid_match.group(1).replace("%3D", "=").replace("=", "")
            print(f"从URL参数提取vid: {video_id}")
        else:
            print("无法从URL参数中提取vid")
            return []
    else:
        # 原来的提取逻辑
        video_id = url.split("?")[0].split("/")[-1].replace("id_", "").split(".html")[0]
    max_mat = await get_vinfos_by_video_id(client, video_id)
    try:
        segments = int(float(max_mat) / 60) + 1
    except (ValueError, TypeError):
        segments = 10  # 默认10个分段

    # 创建所有时间段的参数列表
    all_params = []
    for mat in range(segments):
        all_params.append({"vid": video_id, "mat": mat})
    return all_params


def parse_data(data: dict) -> list[dict]:
    barrage_list = []
    result = json.loads(data.get("data", {}).get("result", {}))
    if result.get("code", "-1") == "-1":
        return []
    danmus = result.get("data", {}).get("result", [])
    for danmu in danmus:
        parsed_data = {}
        parsed_data["text"] = danmu.get("content", "")
        parsed_data["time"] = danmu.get("playat") / 1000
        parsed_data["position"] = "right"
        tmp_color = json.loads(danmu.get("propertis", "{}")).get("color", "#ffffff")
        tmp_color = (
            str(tmp_color)
            if isinstance(tmp_color, str) and tmp_color.startswith("#")
            else f"#{int(tmp_color):06X}"
        )
        parsed_data["color"] = tmp_color
        parsed_data["size"] = "25px"
        # parsed_data["border"] = False
        # parsed_data["style"] = {}
        barrage_list.append(parsed_data)
    return barrage_list


async def fetch_single_barrage(
    client: requests.AsyncSession, params: dict[str, str]
) -> Optional[dict]:
    """获取单个时间段的弹幕"""
    try:
        video_id = params.get("vid")
        mat = params.get("mat")

        url = "https://acs.youku.com/h5/mopen.youku.danmu.list/1.0/"
        msg = {
            "ctime": int(time.time() * 1000),
            "ctype": 10004,
            "cver": "v1.0",
            "guid": client.cookies.get("cna", ""),
            "mat": mat,
            "mcount": 1,
            "pid": 0,
            "sver": "3.1.0",
            "type": 1,
            "vid": video_id,
        }

        msg["msg"] = base64.b64encode(
            json.dumps(msg).replace(" ", "").encode("utf-8")
        ).decode("utf-8")
        msg["sign"] = get_msg_sign(msg["msg"])
        t = int(time.time() * 1000)

        # 检查token是否存在
        token = client.cookies.get("_m_h5_tk", "")
        if not token:
            print("优酷token不存在, 重新获取")
            await get_tk_enc(client)
            token = client.cookies.get("_m_h5_tk", "")
            if not token:
                print("无法获取优酷token")
                return None

        params_req = {
            "jsv": "2.5.6",
            "appKey": "24679788",
            "t": t,
            "sign": yk_t_sign(
                token[:32], str(t), "24679788", json.dumps(msg).replace(" ", "")
            ),
            "api": "mopen.youku.danmu.list",
            "v": "1.0",
            "type": "originaljson",
            "dataType": "jsonp",
            "timeout": "20000",
            "jsonpIncPrefix": "utility",
        }

        headers = client.headers.copy()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        headers["Referer"] = "https://v.youku.com"

        res = await client.post(
            url,
            data={"data": json.dumps(msg).replace(" ", "")},
            headers=headers,
            params=params_req,
        )

        if res and hasattr(res, "json"):
            return res.json()
        return None
    except Exception as e:
        print(f"获取优酷弹幕分段失败(mat={params.get('mat')}): {e}")
        return None


async def read_barrage(
    client: requests.AsyncSession, params: list[dict[str, str]]
) -> list[dict]:
    barrage_list = []

    # 并发获取所有分段弹幕
    tasks = [fetch_single_barrage(client, p) for p in params]
    results = await asyncio.gather(*tasks)
    for res in results:
        if res:
            barrage_list.extend(parse_data(res))
    return barrage_list


async def get_youku_danmu(url: str) -> list[dict]:
    danmu_list = []
    if "youku.com" in url:
        async with requests.AsyncSession() as client:
            client.headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            }
            await get_cna(client)
            await get_tk_enc(client)
            urls = await get_vid_list(client, url)
            danmu_list = await read_barrage(client, urls)
    return danmu_list


async def get_youku_episode_url(url: str) -> dict[str, str]:
    if "youku.com" in url:
        async with requests.AsyncSession() as client:
            res = await client.get(url)
            url_dict = {}
            data = re.search(
                r"window\.__INITIAL_DATA__\s*=\s*({[\s\S]*?});", res.text
            ).group(1)
            json_data = json.loads(data)
            for item in json_data.get("moduleList", [{}])[0].get("components", []):
                if item.get("type") == 10013:
                    for d in item.get("itemList", []):
                        rank = d.get("stage")
                        url = f"https://v.youku.com/v_show/id_{d.get('action_value')}.html"
                        url_dict[rank] = url
            return url_dict
    return {}


if __name__ == "__main__":
    url = "https://v.youku.com/v_show/id_XNjQ4MzU2NDAzMg==.html?refer=esfhz_operation.xuka.xj_00003036_000000_FNZfau_19010900&amp%3Bsubtype=3&amp%3Btype=online-video&amp%3Blink2key=7c84f7aae0&s=bdfb0949ae4c4ac39168"
    danmu = asyncio.run(get_youku_danmu(url))
    print(danmu)

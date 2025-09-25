from curl_cffi import requests
from typing import Optional
import re

API_URL = "http://caiji.dyttzyapi.com/api.php/provide/vod/from/dyttm3u8/at/josn/"


async def search_vod_names(vod_name: str) -> Optional[list[str]]:
    params = {
        "ac": "detail",
        "wd": vod_name,
    }
    media_info_list = []
    async with requests.AsyncSession() as client:
        res = await client.get(API_URL, params=params, impersonate="chrome124")
        if res.status_code != 200 or not res.json()["list"]:
            return None
        data = res.json()["list"]
        for item in data:
            if item["vod_douban_id"] != 0:
                media_info_list.append(
                    {
                        "vod_id": str(item["vod_id"]),
                        "vod_name": item["vod_name"],
                        "vod_class": item["vod_class"],
                        "vod_remarks": item["vod_remarks"],
                        "vod_pic": item["vod_pic"],
                    }
                )
    return media_info_list


def correct_episode_str(episode_str: str) -> int:
    if not episode_str:
        return -1

    try:
        episode_numbers = re.findall(r"\d+", episode_str)
        if episode_numbers:
            episode_num = int(episode_numbers[0])
            return episode_num
        else:
            return -1
    except (ValueError, TypeError):
        return -1


def get_vod_details(vod_id: int) -> Optional[dict[str, str]]:
    params = {
        "ac": "detail",
        "ids": vod_id,
    }
    vod_details = {}
    vod_links = {}
    with requests.Session() as client:
        res = client.get(API_URL, params=params, impersonate="chrome124")
        if res.status_code != 200 or not res.json()["list"]:
            return None
        metainfo = res.json()["list"][0]
        urls = res.json()["list"][0]["vod_play_url"].split("$$$")
        sources = res.json()["list"][0]["vod_play_from"].split("$$$")

        for source_name, source_url in zip(sources, urls):
            single_source_links = {}
            if not source_url:
                continue
            episode_links = source_url.split("#")
            vod_type = "tv" if len(episode_links) > 1 else "movie"
            for episode_link in episode_links:
                if not episode_link or "$" not in episode_link:
                    continue
                episode_str, link = episode_link.split("$", 1)  # 只分割第一个$
                episode_index = correct_episode_str(episode_str)
                if episode_index != -1 and link.strip():
                    single_source_links[episode_index] = link.strip()
                else:
                    if vod_type == "movie":
                        single_source_links[1] = link.strip()
            if single_source_links:
                vod_links[source_name] = single_source_links
        vod_details["vod_id"] = metainfo["vod_id"]
        vod_details["vod_name"] = metainfo["vod_name"]
        vod_details["vod_tag"] = metainfo["vod_tag"]
        vod_details["vod_class"] = metainfo["vod_class"]
        vod_details["vod_pic"] = metainfo["vod_pic"]
        vod_details["vod_actor"] = metainfo["vod_actor"]
        vod_details["vod_director"] = metainfo["vod_director"]
        vod_details["vod_description"] = metainfo["vod_blurb"]
        vod_details["vod_pubdate"] = metainfo["vod_pubdate"]
        vod_details["vod_total"] = metainfo["vod_total"]
        vod_details["vod_douban_id"] = metainfo["vod_douban_id"]
        vod_details["list"] = vod_links
    return vod_details

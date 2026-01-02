from ..provides.bilibili.bilibili import get_bilibili_danmu, get_bilibili_episode_url
from ..provides.iqiyi.iqiyi import get_iqiyi_danmu, get_iqiyi_episode_url
from ..provides.mgtv import get_mgtv_danmu, get_mgtv_episode_url
from ..provides.souhu import get_souhu_danmu, get_souhu_episode_url
from ..provides.tencent import get_tencent_danmu, get_tencent_episode_url
from ..provides.youku import get_youku_danmu, get_youku_episode_url
from ..provides.utils import other2http
from ..provides.douban import (
    get_platform_link,
    douban_get_first_url,
    select_by_360,
    douban_select,
)
from typing import List, Dict, Optional, Any
from async_lru import alru_cache


def deduplicate_danmu(danmu_list: List[List[Any]]) -> List[List[Any]]:
    if not danmu_list:
        return danmu_list

    # 使用字典来存储每个text对应的最早弹幕
    seen_texts = {}
    deduplicated = []

    for danmu in danmu_list:
        text = danmu[4]  # text是第5个元素，索引为4
        time = danmu[0]  # time是第1个元素，索引为0

        if text not in seen_texts:
            seen_texts[text] = len(deduplicated)
            deduplicated.append(danmu)
        else:
            # 如果当前弹幕时间更早，替换已存储的弹幕
            existing_idx = seen_texts[text]
            if time < deduplicated[existing_idx][0]:
                deduplicated[existing_idx] = danmu

    # 按时间重新排序（因为可能有替换操作）
    deduplicated.sort(key=lambda x: x[0])

    return deduplicated


### url是官方视频播放链接
async def get_all_danmu(url: str) -> List[List[Any]]:
    print("begin to get danmu from url", url)
    """使用异步并行执行所有平台获取弹幕"""
    if "mgtv" in url:
        results = await get_mgtv_danmu(url)
        print("get danmu from mgtv")
    elif "qq" in url:
        results = await get_tencent_danmu(url)
        print("get danmu from qq")
    elif "youku" in url:
        results = await get_youku_danmu(url)
        print("get danmu from youku")
    elif "iqiyi" in url:
        results = await get_iqiyi_danmu(url)
        print("get danmu from iqiyi")
    elif "bilibili" in url:
        results = await get_bilibili_danmu(url)
        print("get danmu from bilibili")
    elif "sohu" in url:
        results = await get_souhu_danmu(url)
        print("get danmu from sohu")
    else:
        print("no danmu data get from source")
        return []

    all_danmu = [
        [
            item["time"],
            item["position"],
            item["color"],
            item["size"],
            item["text"],
        ]
        for item in results
    ]
    print("top 5 danmu", all_danmu[:5])
    return all_danmu


### 这里使用官方链接中的第一个链接，在官方网页中获取该视频的所有链接
### 每个平台都有自己的方法，该方法主要用于根据视频名称查询
async def get_episode_url(platform_url_list: List[str]) -> Dict[str, List[str]]:
    """获取所有剧集链接"""
    url_dict = {}
    for platform_url in platform_url_list:
        if "mgtv" in platform_url:
            results = await get_mgtv_episode_url(platform_url)
        elif "qq" in platform_url:
            results = await get_tencent_episode_url(platform_url)
        elif "youku" in platform_url:
            results = await get_youku_episode_url(platform_url)
        elif "iqiyi" in platform_url:
            results = await get_iqiyi_episode_url(platform_url)
        elif "bilibili" in platform_url:
            results = await get_bilibili_episode_url(platform_url)
        elif "sohu" in platform_url:
            results = await get_souhu_episode_url(platform_url)
        else:
            results = {}
        if results:
            for k, v in results.items():
                if k not in url_dict.keys():
                    url_dict[str(k)] = []
                url_dict[str(k)].append(v)
            # 如果找到链接就不需要找下一个
            break
    return url_dict


@alru_cache(maxsize=32, ttl=7200)
async def get_platform_urls_by_id(douban_id: str) -> Dict[str, List[str]]:
    """获取豆瓣对应的平台链接"""
    platform_urls = await douban_get_first_url(douban_id)
    platform_url_list = other2http(platform_urls)
    url_dict = await get_episode_url(platform_url_list)
    if not url_dict:
        url_dict = await get_platform_link(douban_id)
    return url_dict


@alru_cache(maxsize=32, ttl=7200)
async def get_platform_urls_by_title(
    title: str, season_number: Optional[str], season: bool
) -> Dict[str, List[str]]:
    ### 首选查询 360 网站
    ### title 是视频名称
    ### season_number 是季数
    ### season 是是否是连续剧

    url_dict = {}
    _360data = await select_by_360(title, season_number, season)
    platform_url_list = []
    # 处理 _360data 为空的情况
    if _360data and _360data.get("playlinks"):
        for _, value in _360data.get("playlinks", {}).items():
            platform_url_list.append(value)

    url_dict = await get_episode_url(platform_url_list)

    ### 如果360网站没有查询到，则查询豆瓣
    if not url_dict:
        douban_data = await douban_select(title, season_number)
        # 处理 douban_data 为空的情况
        if douban_data and douban_data.get("target_id"):
            douban_id = douban_data["target_id"]
            url_dict = await get_platform_urls_by_id(douban_id)

    return url_dict


@alru_cache(maxsize=5, ttl=300)
async def get_danmu_by_url(url: str) -> List[List[Any]]:
    danmu_data = await get_all_danmu(url)
    # Sort and deduplicate if we have data
    if danmu_data:
        danmu_data.sort(key=lambda x: x[0])
        danmu_data = deduplicate_danmu(danmu_data)
        print("top 5 danmu after deduplicate", danmu_data[:5])
        return danmu_data
    else:
        print("no danmu data")
        return []


async def get_danmu_by_id(id: str, episode_number: str) -> List[List[Any]]:
    """
    Args:
        id: 豆瓣ID
        episode_number: 集数

    Returns:
        List[List[Any]]: 弹幕列表
    """
    urls = await get_platform_urls_by_id(id)
    if not urls:
        return []
    if episode_number in urls:
        url = urls[episode_number]
    elif len(urls) == 1:  ## 可能是电影, 获取第一个即可
        url = list(urls.values())[0]
    else:
        return []  ## 没找到剧集，返回空
    single_url = url[0] if url else None  ## 这里返回的url是列表，只取第一个
    print("single_url", single_url)
    if single_url:
        all_danmu = await get_danmu_by_url(single_url)
        return all_danmu
    else:
        return []


async def get_danmu_by_title(
    title: str, season_number: Optional[str], season: bool, episode_number: str
) -> List[List[Any]]:
    urls = await get_platform_urls_by_title(title, season_number, season)
    if not urls:
        return []
    if episode_number in urls:
        url = urls[episode_number]
    elif len(urls) == 1:  ## 可能是电影, 获取第一个即可
        url = list(urls.values())[0]
    else:
        return []  ## 没找到剧集，返回空
    single_url = url[0] if url else None  ## 这里返回的url是列表，只取第一个
    if single_url:
        all_danmu = await get_danmu_by_url(single_url)
        return all_danmu
    else:
        return []

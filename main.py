from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from urllib.parse import urlparse, parse_qs
import aiohttp
from dataclasses import dataclass
from typing import Annotated, List, Dict, Optional, Any
import re
import json
from async_lru import alru_cache
import asyncio
from enum import Enum

############################################################################
###############################影视数据结构###############################
############################################################################
keywords = (
    r"(特别|惊喜|纳凉)?企划|合伙人手记|超前(营业|vlog)?|速览|vlog|reaction|纯享|加更(版|篇)?|抢先(看|版|集|篇)?|"
    r"抢鲜|预告|花絮(独家)?|特辑|彩蛋|专访|幕后(故事|花絮|独家)?|直播(陪看|回顾)?|未播(片段)?|衍生|番外|"
    r"会员(专享|加长|尊享|专属|版)?|片花|精华|看点|速看|解读|影评|解说|吐槽|盘点|拍摄花絮|制作花絮|"
    r"幕后花絮|未播花絮|独家花絮|花絮特辑|先导预告|终极预告|正式预告|官方预告|彩蛋片段|删减片段|"
    r"未播片段|番外彩蛋|精彩片段|精彩看点|精彩回顾|精彩集锦|看点解析|看点预告|NG镜头|NG花絮|番外篇|"
    r"番外特辑|制作特辑|拍摄特辑|幕后特辑|导演特辑|演员特辑|片尾曲|插曲|高光回顾|背景音乐|OST|"
    r"音乐MV|歌曲MV|前季回顾|剧情回顾|往期回顾|内容总结|剧情盘点|精选合集|剪辑合集|混剪视频|"
    r"独家专访|演员访谈|导演访谈|主创访谈|媒体采访|发布会采访|采访|陪看(记)?|试看版|短剧|精编|"
    r"Plus|独家版|特别版|短片|发布会|解忧局|走心局|火锅局|巅峰时刻|坞里都知道|福持目标坞民|"
    r"观察室|上班那点事儿|周top|赛段|直拍|REACTION|VLOG|全纪录|开播|先导|总宣|展演|集锦|"
    r"旅行日记|精彩分享|剧情揭秘"
)
FILTER_REGEX = re.compile(keywords, re.IGNORECASE)


def is_extra_content(regex: re.Pattern, title: str) -> bool:
    return bool(regex.search(title))


@dataclass
class Episode:
    title: str
    episode_id: str
    url: str


## 判断两个anime是否相同的依据是两个anime的episode.url是否存在交集
@dataclass
class Anime:
    title: str
    source: str
    types: str
    douban_id: str
    episodes: List[Episode]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Anime):
            return False
        link1 = {self._process_url(ep.url) for ep in self.episodes if ep.url}
        link2 = {self._process_url(ep.url) for ep in other.episodes if ep.url}
        return len(link1 & link2) > 0

    def _extract_url_identifier(self, url: str, domain: str, pattern: str) -> Optional[str]:
        """Extract identifier from URL using given pattern"""
        if domain in url:
            match = re.findall(pattern, url)
            return match[0] if match else None
        return None

    def _process_url(self, url: str) -> str:
        patterns = {
            "iqiyi": r"v_[^.]+(?=\.html)",
            "youku": r"id_[^.]+(?=\.html)",
            "bilibili": r"(?<=bangumi/play/)[^?\s]+",
            "qq": r"(?<=cover/)[^/]+(?=/)",
        }
        for domain, pattern in patterns.items():
            identifier = self._extract_url_identifier(url, domain, pattern)
            if identifier is not None:
                return identifier
        return url


SOURCE_NAME_MAP = {
    "腾讯": "qq",
    "爱奇艺": "qiyi",
    "优酷": "youku",
    "哔哩哔哩": "bilibili",
}


def get_eng_source(source: str) -> str:
    for chinese_name, eng_name in SOURCE_NAME_MAP.items():
        if chinese_name in source:
            return eng_name
    return source


type_map = {"电视剧": "tv", "电影": "movie", "动漫": "tv", "少儿": "tv"}

CAIJI_API_URL = "https://gctf.tfdh.top/api.php/provide/vod"

############################################################################
###############################弹幕数据结构###############################
############################################################################


@dataclass
class DanmukuResponse:
    code: int
    name: str
    danum: int
    danmuku: List[List[Any]]

    @classmethod
    def empty(cls, message: str) -> "DanmukuResponse":
        """Create an empty response with an error message"""
        return cls(code=1, name=message, danum=0, danmuku=[])


class VideoType(str, Enum):
    tv = "tv"
    movie = "movie"


def parse_episode_string(ep_str: str, index: int) -> Optional[Episode]:
    """Parse a single episode string into an Episode object"""
    ep_str = ep_str.strip()
    if not ep_str:
        return None

    episode_data = ep_str.split("$")
    if len(episode_data) >= 2:
        ep_title = episode_data[0]
        ep_url = episode_data[1]
    else:
        ep_title = f"第{index + 1}集"
        ep_url = episode_data[0] if episode_data else ""

    if ep_url and not is_extra_content(FILTER_REGEX, ep_title):
        return Episode(title=ep_title, episode_id=str(index + 1), url=ep_url)
    return None


def parse_video_data(video: dict) -> List[Anime]:
    """Parse video data from caiji API into Anime objects"""
    animes = []
    title = video.get("vod_name", "")
    types = video.get("type_name", "")
    douban_id = str(video.get("vod_douban_id", ""))
    play_from = video.get("vod_play_from", "")
    play_url = video.get("vod_play_url", "")

    if not (play_from and play_url):
        return animes

    sources = play_from.split("$$$")
    urls = play_url.split("$$$")

    for i, source in enumerate(sources):
        if i >= len(urls):
            break

        platform_episodes = urls[i].split("#")
        episodes = []

        for j, ep_str in enumerate(platform_episodes):
            episode = parse_episode_string(ep_str, j)
            if episode:
                episodes.append(episode)

        if episodes:
            animes.append(
                Anime(
                    title=title,
                    source=source.strip(),
                    types=types,
                    douban_id=douban_id,
                    episodes=episodes,
                )
            )

    return animes


async def fetch_videos_from_caiji(search_title: str) -> List[Anime]:
    """Fetch and parse videos from caiji API"""
    animes = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                CAIJI_API_URL,
                params={"ac": "detail", "wd": search_title},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    print(f"Failed to get data from caiji: status {resp.status}")
                    return animes

                text = await resp.text()
                data = json.loads(text)

                if not data or data.get("code") != 1:
                    print("Failed to get data from caiji: invalid response")
                    return animes

                for video in data.get("list", []):
                    animes.extend(parse_video_data(video))

    except asyncio.TimeoutError:
        print("Timeout while fetching caiji data")
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
    except Exception as e:
        print(f"Error in fetch_videos_from_caiji: {e}")

    return animes


############################################################################
###############################主函数功能###################################
############################################################################
class DoubanSource:
    def __init__(self, douban_id: str, video_type: str = "tv") -> None:
        self.douban_id = douban_id
        self.video_type = video_type
        self.animes_from_douban = []
        self.animes_from_caiji = []
        self.vendors = []
        self.title = ""
        self.types = []

    async def _init(self):
        """初始化：获取豆瓣数据"""
        url = f"https://frodo.douban.com/api/v2/{self.video_type}/{self.douban_id}?apiKey=0ac44ae016490db2204ce0a042db2916"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090c33)XWEB/11581",
            "xweb_xhr": "1",
            "content-type": "application/json",
            "sec-fetch-site": "cross-site",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": "https://servicewechat.com/wx2f9b06c1de1ccfca/99/page-frame.html",
            "accept-language": "zh-CN,zh;q=0.9",
        }
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        print(f"Failed to get data from douban: status {resp.status}")
                        return

                    data = await resp.json()
                    if not data:
                        print("No data found from douban")
                        return

                    self.title = data.get("title", "")
                    self.types = data.get("type", [])
                    self.vendors = data.get("vendors", [])

                    if not self.vendors:
                        print("No vendors found")
        except asyncio.TimeoutError:
            print(f"Timeout while fetching douban data for {self.douban_id}")
        except Exception as e:
            print(f"Error fetching douban data: {e}")

    @classmethod
    async def create(cls, douban_id: str, video_type: str = "tv"):
        """工厂方法：创建并初始化实例"""
        instance = cls(douban_id, video_type)
        await instance._init()

        if instance.vendors:
            # 并发执行两个任务
            await asyncio.gather(
                instance.search_videos(),
                instance.get_first_link(),
                return_exceptions=True,  # 不让一个任务的异常影响另一个
            )

        return instance

    def _resolve_url_query(self, url: str) -> Dict[str, list[str]]:
        """解析URL查询参数"""
        try:
            parsed = urlparse(url)
            return parse_qs(parsed.query)
        except Exception as e:
            print(f"Error parsing URL {url}: {e}")
            return {}

    def _normalize_bilibili_url(self, url: str) -> str:
        """标准化B站URL"""
        try:
            parsed = urlparse(url)
            # 保留path，但使用标准域名
            # 注意：这里可能丢失了重要的query参数（如p=分P）
            return f"https://www.bilibili.com{parsed.path}"
        except Exception as e:
            print(f"Error normalizing bilibili URL {url}: {e}")
            return url

    async def _fetch_with_retry(self, url: str, max_retries: int = 2) -> Optional[str]:
        """带重试的HTTP请求"""
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            return await resp.text()
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"Failed to fetch {url} after {max_retries} attempts: {e}")
                await asyncio.sleep(0.5 * (attempt + 1))  # 指数退避
        return None

    async def _get_youku_url(self, url: str) -> str:
        """获取优酷真实URL"""
        data = await self._fetch_with_retry(url)
        if not data:
            return ""

        pattern = r"(?:https:)?//v\.youku\.com/+v_show/id_[^/]+\.html"
        match = re.search(pattern, data)

        if match:
            true_url = match.group(0)
            if not true_url.startswith("https:"):
                true_url = "https:" + true_url
            # 修复可能的双斜杠问题
            true_url = re.sub(r"//v_show", "/v_show", true_url)
            true_url = true_url.replace("http://", "https://")
            return true_url

        return ""

    async def _get_tencent_url(self, cid: str) -> str:
        """获取腾讯视频真实URL"""
        url = f"https://v.qq.com/x/cover/{cid}.html"
        data = await self._fetch_with_retry(url)

        if not data:
            return ""

        pattern = rf"(?:https:)?//v\.qq\.com/x/cover/{cid}/[^/?]+\.html"
        match = re.search(pattern, data)

        if match:
            true_url = match.group(0)
            if not true_url.startswith("https:"):
                true_url = "https:" + true_url
            return true_url

        return ""

    async def _process_iqiyi(self, vendor: dict) -> Optional[Anime]:
        """处理爱奇艺"""
        url = vendor.get("url", "").split("?")[0]
        if not url:
            return None
        if url.startswith("http://"):
            url = url.replace("http://", "https://")

        return Anime(
            title=self.title,
            source=vendor.get("title", "爱奇艺"),
            types=self.types,
            douban_id=self.douban_id,
            episodes=[Episode(title="第1集", episode_id="1", url=url)],
        )

    async def _process_youku(self, vendor: dict) -> Optional[Anime]:
        """处理优酷"""
        params = self._resolve_url_query(vendor.get("uri", ""))
        showid = params.get("showid", [""])[0]
        refer = params.get("refer", [""])[0]

        if not showid:
            return None

        original_url = f"https://v.youku.com/video?s={showid}&refer={refer}"
        url = await self._get_youku_url(original_url)

        if not url:
            return None

        return Anime(
            title=self.title,
            source=vendor.get("title", "优酷"),
            types=self.types,
            douban_id=self.douban_id,
            episodes=[Episode(title="第1集", episode_id="1", url=url)],
        )

    async def _process_tencent(self, vendor: dict) -> Optional[Anime]:
        """处理腾讯视频"""
        params = self._resolve_url_query(vendor.get("uri", ""))
        cid = params.get("cid", [""])[0]
        vid = params.get("vid", [""])[0]

        if not cid:
            return None

        if vid:
            url = f"https://v.qq.com/x/cover/{cid}/{vid}.html"
        else:
            url = await self._get_tencent_url(cid)

        if not url:
            return None

        return Anime(
            title=self.title,
            source=vendor.get("title", "腾讯视频"),
            types=self.types,
            douban_id=self.douban_id,
            episodes=[Episode(title="第1集", episode_id="1", url=url)],
        )

    async def _process_bilibili(self, vendor: dict) -> Optional[Anime]:
        """处理B站"""
        url = self._normalize_bilibili_url(vendor.get("url", ""))
        if not url or url == "https://www.bilibili.com":
            return None

        return Anime(
            title=self.title,
            source=vendor.get("title", "哔哩哔哩"),
            types=self.types,
            douban_id=self.douban_id,
            episodes=[Episode(title="第1集", episode_id="1", url=url)],
        )

    async def get_first_link(self):
        """获取各平台的第一集链接 - 并发处理"""
        tasks = []

        for vendor in self.vendors:
            app_uri = vendor.get("app_uri", "")

            if app_uri.startswith("iqiyi"):
                tasks.append(self._process_iqiyi(vendor))
            elif app_uri.startswith("youku"):
                tasks.append(self._process_youku(vendor))
            elif app_uri.startswith("txvideo"):
                tasks.append(self._process_tencent(vendor))
            elif app_uri.startswith("bilibili"):
                tasks.append(self._process_bilibili(vendor))
            else:
                print(f"Unknown source: {vendor.get('title', 'unknown')}")

        # 并发处理所有平台
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Anime):
                    self.animes_from_douban.append(result)
                elif isinstance(result, Exception):
                    print(f"Error processing vendor: {result}")

    async def search_videos(self):
        """从采集接口搜索视频"""
        self.animes_from_caiji = await fetch_videos_from_caiji(self.title)


class CaijiSource:
    def __init__(self, title: str) -> None:
        self.title = title
        self.animes_from_caiji = []

    @classmethod
    async def create(cls, title: str):
        instance = cls(title)
        await instance.search_videos()
        return instance

    async def search_videos(self):
        """从采集接口搜索视频"""
        self.animes_from_caiji = await fetch_videos_from_caiji(self.title)


def extract_episode_number_from_title(episode_title: str) -> Optional[str]:
    """
    从剧集标题中提取集数（返回字符串格式，去除前导零）

    Args:
        episode_title: 剧集标题字符串

    Returns:
        集数（字符串），如果无法提取则返回 None

    匹配规则（按优先级）：
    1. "第X集" 格式（支持空格）
    2. "EPX" 或 "EX" 格式（支持空格）
    3. 纯数字（必须在开头，不能有前导空格）
    """
    if not episode_title:
        return None

    # 匹配格式：第1集、第01集、第 01 集、第001集等（支持空格）
    chinese_match = re.search(r"第\s*(\d+)\s*集", episode_title)
    if chinese_match:
        return str(int(chinese_match.group(1)))

    # 匹配格式：EP01、EP1、E01、E1、EP 01等（支持空格）
    ep_match = re.search(r"[Ee][Pp]?\s*(\d+)", episode_title)
    if ep_match:
        return str(int(ep_match.group(1)))

    # 匹配格式：01、1、001（纯数字，必须在开头，后面可跟空格或结尾）
    # 注意：这里去掉了开头的空格匹配，只匹配以数字开头的情况
    number_match = re.search(r"^(\d+)(?:\s|$)", episode_title)
    if number_match:
        return str(int(number_match.group(1)))

    return None


def find_episode_by_number(episodes: List[Episode], target: str) -> Optional[Episode]:
    """Find episode by extracted number from title, falling back to episode_id"""
    # First try matching by extracted episode number from title
    for episode in episodes:
        extracted = extract_episode_number_from_title(episode.title)
        print(f"Extracted number: {extracted}")
        print(f"original number: {episode.title}")
        if extracted == target:
            return episode

    # Fall back to matching by episode_id
    for episode in episodes:
        if episode.episode_id == target:
            return episode

    return None


@alru_cache(maxsize=32, ttl=60)
async def get_final_animes(douban_id: str, video_type: str) -> List[Anime]:
    # 创建实例
    source = await DoubanSource.create(douban_id, video_type)
    print(f"Title: {source.title}")
    print(f"Found {len(source.animes_from_douban)} animes from douban")
    print(f"Found {len(source.animes_from_caiji)} animes from caiji")
    # 存储最终匹配的采集源anime列表
    final_animes = []

    # 查找匹配的anime
    for douban_anime in source.animes_from_douban:
        for caiji_anime in source.animes_from_caiji:
            if get_eng_source(douban_anime.source) != caiji_anime.source:
                print(
                    f"Source not match, {douban_anime.source} != {caiji_anime.source}"
                )
                continue
            if type_map.get(caiji_anime.types) != douban_anime.types:
                print(f"Type not match, {caiji_anime.types} != {douban_anime.types}")
                continue
            if douban_anime == caiji_anime:
                # 创建新的Anime对象，使用caiji的数据但douban_id来自douban
                matched_anime = Anime(
                    title=caiji_anime.title,
                    source=caiji_anime.source,
                    types=caiji_anime.types,
                    douban_id=douban_anime.douban_id,  # 使用douban的douban_id
                    episodes=caiji_anime.episodes,  # 保留caiji的所有episodes
                )
                final_animes.append(matched_anime)

    return final_animes


@alru_cache(maxsize=32, ttl=60)
async def get_final_animes_by_title(title: str, video_type: str) -> Anime | None:
    source = await CaijiSource.create(title)
    print(f"Title: {source.title}")
    print(f"Found {len(source.animes_from_caiji)} animes from caiji")

    for caiji_anime in source.animes_from_caiji:
        if type_map.get(caiji_anime.types) != video_type:
            continue
        # Exact match takes priority
        if caiji_anime.title == title:
            return caiji_anime
        # Partial match as fallback
        if title in caiji_anime.title or caiji_anime.title in title:
            return caiji_anime

    return None


@alru_cache(maxsize=5, ttl=60)
async def get_danmuku(url: str) -> DanmukuResponse:
    danmuku_url = f"https://dmku.hls.one/?ac=dm&url={url}"
    print(f"Fetching danmuku from {danmuku_url}")
    async with aiohttp.ClientSession() as session:
        async with session.get(danmuku_url) as response:
            if response.status == 200:
                danmuku_data = await response.json()
                return DanmukuResponse(**danmuku_data)
            print(f"dmku return no data: {response.status}")
            return DanmukuResponse.empty("Failed to fetch danmuku from dmku.hls.one")


async def get_danmu_by_douban_id(
    douban_id: str, video_type: str, episode_number: str
) -> DanmukuResponse:
    final_animes = await get_final_animes(douban_id, video_type)
    if not final_animes:
        print(f"No final animes found for {douban_id}")
        return DanmukuResponse.empty("No final animes found")

    anime = final_animes[0]
    print(f"only use the first anime: {anime.source}")
    episode = find_episode_by_number(anime.episodes, episode_number)
    if not episode:
        print(f"No episode found for {episode_number}")
        return DanmukuResponse.empty("No episode found")

    return await get_danmuku(episode.url)


async def get_danmu_by_title(
    title: str, video_type: str, episode_number: str
) -> DanmukuResponse:
    final_anime = await get_final_animes_by_title(title, video_type)
    if not final_anime:
        print(f"No final anime found for {title}")
        return DanmukuResponse.empty("No final anime found")

    episode = find_episode_by_number(final_anime.episodes, episode_number)
    if not episode:
        print(f"No episode found for {episode_number}")
        return DanmukuResponse.empty("No episode found")

    return await get_danmuku(episode.url)


############################################################################
###############################FastAPI###################################
############################################################################

app = FastAPI(
    title="免费弹幕抓取",
    description="This is a free danmuku server.",
    version="2.0.0",
    contact={
        "name": "API Support",
        "url": "https://github.com/SeqCrafter/fetch_danmu",
        "email": "sdupan2015@gmail.com",
    },
    default_response_class=ORJSONResponse,
)
# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/web", StaticFiles(directory="front", html=True), name="static")


@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse("/web")


@app.get("/api/comment", response_model=DanmukuResponse)
async def danmu_by_url(
    url: Annotated[str, Query(description="视频URL")],
):
    all_danmu = await get_danmuku(url)
    return all_danmu


@app.get("/api/douban", response_model=DanmukuResponse)
async def danmu_by_douban_id(
    douban_id: Annotated[int, Query(description="豆瓣ID")],
    episode_number: Annotated[int, Query(description="集数")],
    video_type: Annotated[VideoType, Query(description="视频类型")] = VideoType.tv,
):
    all_danmu = await get_danmu_by_douban_id(
        str(douban_id), video_type.value, str(episode_number)
    )
    return all_danmu


@app.get("/api/title", response_model=DanmukuResponse)
async def danmu_by_title(
    title: Annotated[str, Query(description="标题")],
    episode_number: Annotated[int, Query(description="集数")],
    video_type: Annotated[VideoType, Query(description="视频类型")] = VideoType.tv,
):
    all_danmu = await get_danmu_by_title(title, video_type.value, str(episode_number))
    return all_danmu

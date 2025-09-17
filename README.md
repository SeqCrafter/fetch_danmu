# 弹幕获取 API (Danmu Fetch API)

一个基于 [Fastapi](https://github.com/tiangolo/fastapi) 的异步弹幕聚合服务，支持从多个主流视频平台获取弹幕数据，具体支持的平台请看`provides`文件目录，返回用于[weizhenye/Danmaku](https://github.com/weizhenye/Danmaku)的弹幕数据。

## 功能特性

- 🌐 **UI 界面**: 支持通过 UI 界面获取弹幕数据，基于[reflex](https://github.com/reflex-dev/reflex)实现
- 🚀 **异步并行处理**: 使用 asyncio 并行获取多平台弹幕，提高响应速度
- 🔍 **多种获取方式**: 支持豆瓣 ID、标题搜索和直接 URL 三种弹幕获取方式
- 🎯 **平台聚合**: 一次请求获取所有支持平台的弹幕数据
- 📊 **标准化输出**: 统一的弹幕数据格式，便于后续处理
- 🛡️ **异常容错**: 单个平台失败不影响其他平台数据获取
- 📖 **完整文档**: 内置 Swagger UI 文档

## UI 界面演示：

<img src="https://tncache1-f1.v3mh.com/image/2025/09/14/5ef321af4f2d63b5fc702860014e00c2.png" alt="弹幕播放器" style="max-width:600px">

<details>
  <summary>点击查看更多截图</summary>
  <img src="https://tncache1-f1.v3mh.com/image/2025/09/14/f8bec9a052404604a8dbe266a3c9e29b.png" alt="主页" style="max-width:600px">
  <img src="https://tncache1-f1.v3mh.com/image/2025/09/14/33579f0353ea588db93e297cb8c18291.png" alt="搜索页" style="max-width:600px">
  <img src="https://tncache1-f1.v3mh.com/image/2025/09/14/9dd918f1b909856caf9605ed72cd6d04.png" alt="详情页" style="max-width:600px">
  <img src="https://tncache1-f1.v3mh.com/image/2025/09/14/5ef321af4f2d63b5fc702860014e00c2.png" alt="播放页" style="max-width:600px">
</details>

## 快速开始

### Docker 运行

```bash
docker run -d -p 8080:8080 --name fetch-danmu ghcr.io/seqcrafter/fetch-danmu:2.4.0
```

服务将在 `http://127.0.0.1:8080` 启动。

> 注意：由于由于 Reflex 的限制，通过我构建的 Docker 镜像，只能本地访问或者使用 https 访问，无法通过 http 远程访问，因为会提示无法找到后端 API.如果你想通过 http 远程访问，需要构建你自己的 Docker 镜像，参考[Dockerfile](Dockerfile), 修改 REFLEX_API_URL 为你的后端 API 地址。

### API 文档

点击导航栏的`API文档`，即可访问 API 文档。
或者访问`http://127.0.0.1:8080/docpage`。

## API 接口

### 1. 通过豆瓣 ID 获取弹幕

```
GET /douban_id
```

**参数:**

- `douban_id` (必需): 豆瓣电影/剧集 ID
- `episode_number` (可选): 指定集数

**示例:**

```bash
## 子夜归第一集弹幕
curl "http://127.0.0.1:8080/douban_id?douban_id=36481469&episode_number=1"
```

### 2. 通过标题搜索获取弹幕

**新增一个测试接口用来为魔改版 zyplayer 提供弹幕数据**

```
GET /test/title
```

**参数:**

- `title` (必需): 视频标题
- `season_number` (可选): 季数，默认为 1
- `season` (可选): 是否是连续剧，默认为 True，电视剧选 True，电影选 False
- `episode_number` (可选): 集数

**示例:**

```bash
curl "http://127.0.0.1:8080/test/title?title=子夜归&season_number=1&episode_number=1&season=true"
```

```
GET /title
```

**参数:**

- `title` (必需): 视频标题
- `season_number` (可选): 季数，默认为 1
- `season` (可选): 是否是连续剧，默认为 True，电视剧选 True，电影选 False
- `episode_number` (可选): 集数

**示例:**

```bash
curl "http://127.0.0.1:8080/title?title=子夜归&season_number=1&episode_number=1&season=true"
```

### 3. 通过 URL 直接获取弹幕

```
GET /url
```

**参数:**

- `url` (必需): 视频页面 URL

**示例:**

```bash
curl "http://127.0.0.1:8080/url?url=https://v.qq.com/x/cover/mzc002009y0nzq8/z4101m43ng6.html"
```

## 响应格式

### 成功响应

```json
{
  "code": 0,
  "name": "36172040",
  "danmu_data": 13223,
  "danmuku": [
    [0.0, "right", "#FFFFFF", "25px", "恭迎师祖出山"],
    [0.0, "right", "#FFFFFF", "25px", "来支持献鱼啦"]
  ]
}
```

### 错误响应

```json
{ "error": "douban_id is required" }
```

## 许可证

本项目基于 MIT 许可证开源。详见 [LICENSE](LICENSE) 文件。

## 贡献

所有弹幕获取和豆瓣搜索的代码都是从[thshu/fnos-tv](https://github.com/thshu/fnos-tv)仓库中 1:1 复制的，感谢作者的贡献。
本仓库由于使用了 fastapi, 所以将原本所有的同步代码全部修改为异步类型。
同时本仓库将弹幕接口解耦，并适配了[weizhenye/Danmaku](https://github.com/weizhenye/Danmaku)的格式。

## 注意事项

- 本项目仅用于学习和研究目的
- 请遵守相关平台的使用条款
- 弹幕数据版权归原平台所有

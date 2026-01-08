# 弹幕获取 API (Danmu Fetch API)

因为弹幕服务一般部署在国外服务器上，因此对项目重构，目前只负责从豆瓣网抓取链接，然后直接调用弹幕接口返回弹幕

目前调用的弹幕接口为：[公益弹幕库](https://dmku.hls.one/)

---

因为 Reflex 的 API 更新频繁，所以基于 reflex 的前端版本删除了，只保留了后端 API 的仓库。最近测试发现，本地可以获取正确的弹幕，但是部署到远端就得到随机的错误弹幕，原因是当前对爱奇艺的抓取方法在有些服务器(国外 ip)上会获取错误的 tvId!从而导致抓取到错误弹幕。

推荐 Fork 修改的另一个仓库[danmu_api](https://github.com/SeqCrafter/danmu_api), 具有相似的 API.

## 功能特性

- 🚀 **异步并行处理**: 使用 asyncio 并行获取多平台弹幕，提高响应速度
- 🔍 **多种获取方式**: 支持豆瓣 ID、标题搜索和直接 URL 三种弹幕获取方式
- 🎯 **平台聚合**: 一次请求获取所有支持平台的弹幕数据
- 📊 **标准化输出**: 统一的弹幕数据格式，便于后续处理
- 🛡️ **异常容错**: 单个平台失败不影响其他平台数据获取
- 📖 **完整文档**: 内置 Swagger UI 文档

## 快速开始

### 在[leapcell](https://leapcell.io)上部署(爱奇艺的抓取是错误结果)

1. fork 本仓库
2. 在[leapcell](https://leapcell.io)上创建一个新项目,使用 fork 后的仓库
3. 部署 fastapi 应用
4. build command: `pip install -r requirements.txt`
5. run command: `fastapi run main.py --port 8080`

### 使用 Docker 部署

```bash
docker run -d --name fetch_danmu --restart unless-stopped -p 8080:8080 ghcr.io/seqcrafter/fetch_danmu:latest
```

服务将在 8080 端口启动。

### API 文档

启动服务后，可通过以下地址(我们用 localhost 作为示例)访问 API 文档页面：

- Swagger UI: `http://localhost:8080/docs`

## API 接口

### 1. 通过豆瓣 ID 获取弹幕

```
GET /douban
```

**参数:**

- `douban_id` (必需): 豆瓣电影/剧集 ID
- `episode_number` (可选): 指定集数
- `video_type` (可选): 视频类型，可选值为 `tv`、`movie`

**示例:**

```bash
## 子夜归第一集弹幕
curl "http://127.0.0.1:8080/douban?douban_id=36481469&episode_number=1"
```

### 2. 通过标题搜索获取弹幕

```
GET /title
```

**参数:**

- `title` (必需): 标题
- `episode_number` (可选): 指定集数
- `video_type` (可选): 视频类型，可选值为 `tv`、`movie`

**示例:**

```bash
## 子夜归第一集弹幕
curl "http://127.0.0.1:8080/title?title=子夜归&episode_number=1"
```

### 3. 通过 URL 获取弹幕

绕过了 `CORS`，可以前端直接调用接口

```
GET /comment
```

**参数:**

- `url` (必需): 豆瓣电影/剧集 ID

**示例:**

```bash
## 子夜归第一集弹幕
curl "http://127.0.0.1:8080/comment?url=https://v.youku.com/v_show/id_XNjQ4MzU2NDAzMg==.html"
```

## 响应格式

### 成功响应

```json
{
  "code": 23,
  "name": "36172040",
  "danmu_data": 13223,
  "danmuku": [
    [0.0, "right", "#FFFFFF", "25px", "恭迎师祖出山"],
    [0.0, "right", "#FFFFFF", "25px", "来支持献鱼啦"]
  ]
}
```

## 许可证

本项目基于 MIT 许可证开源。详见 [LICENSE](LICENSE) 文件。

## 注意事项

- 本项目仅用于学习和研究目的
- 请遵守相关平台的使用条款
- 弹幕数据版权归原平台所有

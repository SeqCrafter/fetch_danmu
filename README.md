# 弹幕获取 API (Danmu Fetch API)

一个基于 fastapi 的异步弹幕聚合服务，支持从多个主流视频平台获取弹幕数据，具体支持的平台请看`provides`文件目录，返回用于[weizhenye/Danmaku](https://github.com/weizhenye/Danmaku)的弹幕数据。

## 功能特性

- 🚀 **异步并行处理**: 使用 asyncio 并行获取多平台弹幕，提高响应速度
- 🔍 **多种获取方式**: 支持豆瓣 ID、标题搜索和直接 URL 三种弹幕获取方式
- 🎯 **平台聚合**: 一次请求获取所有支持平台的弹幕数据
- 📊 **标准化输出**: 统一的弹幕数据格式，便于后续处理
- 🛡️ **异常容错**: 单个平台失败不影响其他平台数据获取
- 📖 **完整文档**: 内置 Swagger UI 文档

## 快速开始

### 在[leapcell](https://leapcell.io)上部署

1. fork 本仓库
2. 在[leapcell](https://leapcell.io)上创建一个新项目,使用 fork 后的仓库
3. 部署 fastapi 应用
4. build command: `pip install -r requirements.txt`
5. run command: `granian --interface asgi --host 0.0.0.0 --port 8080 --workers 4 main:app`
6. environment variables: `POSTGRES_USER` and `POSTGRES_PASSWORD` 设置为你的数据库用户名和密码，`POSTGRES_LINK` 设置为你的数据库链接

**你可以使用 supabase 来创建数据库，并设置环境变量。也可以使用其他数据库，并设置环境变量。**

服务将在 提供的链接 启动。

### API 文档

启动服务后，可通过以下地址(我们用 localhost 作为示例)访问 API 文档页面：

- Swagger UI: `http://localhost:8080/docs`

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

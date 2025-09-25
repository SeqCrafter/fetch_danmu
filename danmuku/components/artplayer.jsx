import React, { useEffect, useRef } from "react";
import Artplayer from "artplayer";
import artplayerPluginDanmuku from "artplayer-plugin-danmuku";
import Hls from "hls.js";

const ArtPlayerWithDanmaku = ({
  url,
  danmakuUrl,
  danmakuOptions = {},
  onDanmakuLoaded,
  onDanmakuError,
  ...rest
}) => {
  const artRef = useRef();
  const artPlayerRef = useRef(null);

  // 转换弹幕数据格式
  const convertDanmakuData = (apiData) => {
    if (!apiData || !apiData.danmuku || !Array.isArray(apiData.danmuku)) {
      return [];
    }

    return apiData.danmuku.map(([time, mode, color, fontSize, text]) => ({
      text: text,
      time: time,
      color: color || "#FFFFFF",
      mode:
        mode === "right" ? 0 : mode === "top" ? 1 : mode === "bottom" ? 2 : 0,
      fontSize: fontSize ? parseInt(fontSize) : 25,
    }));
  };

  // 异步加载弹幕数据
  const loadDanmakuData = () => {
    return new Promise((resolve, reject) => {
      if (!danmakuUrl) {
        resolve([]);
        return;
      }

      fetch(danmakuUrl)
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          return response.json();
        })
        .then((data) => {
          if (data.code === 0) {
            const convertedData = convertDanmakuData(data);
            console.log("弹幕数据加载成功:", convertedData.length, "条");
            if (onDanmakuLoaded) {
              onDanmakuLoaded(convertedData, data);
            }
            resolve(convertedData);
          } else {
            throw new Error(`API error! code: ${data.code}`);
          }
        })
        .catch((error) => {
          console.error("弹幕加载失败:", error);
          if (onDanmakuError) {
            onDanmakuError(error);
          }
          resolve([]); // 即使失败也返回空数组，让播放器正常工作
        });
    });
  };
  const cleanupPlayer = () => {
    if (artPlayerRef.current) {
      try {
        // 销毁 HLS 实例
        if (artPlayerRef.current.video && artPlayerRef.current.video.hls) {
          artPlayerRef.current.video.hls.destroy();
        }

        // 销毁 ArtPlayer 实例
        artPlayerRef.current.destroy();
        artPlayerRef.current = null;

        console.log("播放器资源已清理");
      } catch (err) {
        console.warn("清理播放器资源时出错:", err);
        artPlayerRef.current = null;
      }
    }
  };

  function playVideo(video, url, art) {
    if (url.includes(".m3u8")) {
      if (Hls.isSupported()) {
        if (art.hls) art.hls.destroy();
        const hls = new Hls();
        hls.loadSource(url);
        hls.attachMedia(video);
        art.hls = hls;
        art.on("destroy", () => hls.destroy());
      } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
        video.src = url;
      } else {
        art.notice.show = "Unsupported playback format: m3u8";
      }
    } else {
      video.src = url;
    }
  }
  useEffect(() => {
    if (!artRef.current || !url) return;

    if (artPlayerRef.current) {
      cleanupPlayer();
    }
    // 默认弹幕配置
    const defaultDanmakuOptions = {
      danmuku: loadDanmakuData, // 使用异步函数加载弹幕
      speed: 7.5, // 弹幕持续时间，范围在[1 ~ 10]
      margin: [10, "50%"], // 弹幕上下边距，支持像素数字和百分比
      opacity: 1, // 弹幕透明度，范围在[0 ~ 1]
      color: "#FFFFFF", // 默认弹幕颜色
      mode: 0, // 默认弹幕模式: 0: 滚动，1: 顶部，2: 底部
      modes: [0, 1, 2], // 弹幕可见的模式
      fontSize: 23, // 弹幕字体大小
      antiOverlap: true, // 弹幕是否防重叠
      synchronousPlayback: true, // 是否同步播放速度
      heatmap: false, // 是否开启热力图
      width: 512, // 当播放器宽度小于此值时，弹幕发射器置于播放器底部
      filter: () => true, // 弹幕载入前的过滤器
      beforeEmit: () => true, // 弹幕发送前的过滤器
      beforeVisible: () => true, // 弹幕显示前的过滤器
      visible: true, // 弹幕层是否可见
      emitter: false, // 是否开启弹幕发射器
      maxLength: 200, // 弹幕输入框最大长度
      lockTime: 5, // 输入框锁定时间
      theme: "dark", // 弹幕主题
      ...danmakuOptions,
    };

    Artplayer.PLAYBACK_RATE = [0.5, 0.75, 1, 1.25, 1.5, 2, 3];
    Artplayer.USE_RAF = true;

    console.log("🔵 创建新的播放器实例");
    // 创建播放器实例
    artPlayerRef.current = new Artplayer({
      container: artRef.current,
      url: url,
      volume: 0.7,
      isLive: false,
      muted: false,
      autoplay: true,
      pip: true,
      autoSize: false,
      autoMini: false,
      screenshot: false,
      setting: true,
      loop: false,
      flip: false,
      playbackRate: true,
      aspectRatio: false,
      fullscreen: true,
      fullscreenWeb: true,
      subtitleOffset: false,
      miniProgressBar: false,
      mutex: true,
      playsInline: true,
      autoPlayback: false,
      airplay: true,
      theme: "#22c55e",
      lang: "zh-cn",
      hotkey: true,
      fastForward: true,
      autoOrientation: true,
      lock: true,
      moreVideoAttr: {
        crossOrigin: "anonymous",
      },
      // HLS 支持配置
      customType: {
        m3u8: playVideo,
        mp4: playVideo,
      },
      plugins: [
        // 添加弹幕插件
        artplayerPluginDanmuku(defaultDanmakuOptions),
      ],
    });
    artPlayerRef.current.on("artplayerPluginDanmuku:error", (error) => {
      artPlayerRef.current.notice.show =
        "弹幕加载失败,可能服务器被豆瓣封锁,请稍候尝试";
    });
    return () => {
      cleanupPlayer();
    };
  }, []);

  return <div ref={artRef} {...rest}></div>;
};

ArtPlayerWithDanmaku.displayName = "ArtPlayerWithDanmaku";

export default ArtPlayerWithDanmaku;

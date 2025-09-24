import React, { useState } from "react";

const DoubanRecommendCards = ({ doubanData, onCardClick }) => {
  const [currentPage, setCurrentPage] = useState(0);

  // 创建代理图片URL的辅助函数
  const getProxyImageUrl = (originalUrl) => {
    if (!originalUrl) return null;
    // 对原始URL进行编码，然后通过我们的代理端点访问
    //return `${doubanProxy}?url=${encodeURIComponent(originalUrl)}`;
    return originalUrl.replace(
      /img\d+\.doubanio\.com/g,
      "img.doubanio.cmliussss.net"
    );
  };

  // 如果没有数据，返回空
  if (!doubanData || !doubanData.movies || doubanData.movies.length === 0) {
    return <div>加载豆瓣数据中……</div>;
  }

  const movies = doubanData.movies;
  const itemsPerPage = 10; // 2行5列 = 10个项目
  const totalPages = Math.ceil(movies.length / itemsPerPage);

  // 处理卡片点击
  const handleCardClick = (movie) => {
    if (onCardClick) {
      onCardClick(movie.title);
    }
  };

  // 处理分页导航
  const goToPrevious = () => {
    if (currentPage > 0) {
      setCurrentPage(currentPage - 1);
    }
  };

  const goToNext = () => {
    if (currentPage < totalPages - 1) {
      setCurrentPage(currentPage + 1);
    }
  };

  // 格式化评分
  const formatRating = (rating) => {
    if (!rating || rating.value === 0) return null;
    return (rating.value / 10).toFixed(1);
  };

  // 获取评分颜色
  const getRatingColor = (rating) => {
    if (!rating || rating.value === 0) return "text-gray-400";
    const score = rating.value / 10;
    if (score >= 8.0) return "text-green-500";
    if (score >= 7.0) return "text-yellow-500";
    if (score >= 6.0) return "text-orange-500";
    return "text-red-500";
  };

  // 获取当前页的电影数据
  const getCurrentPageMovies = () => {
    const startIndex = currentPage * itemsPerPage;
    return movies.slice(startIndex, startIndex + itemsPerPage);
  };

  return (
    <div className="w-full bg-white">
      {/* 标题区域 */}
      <div className="px-6 py-4">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          {doubanData.description?.subtitle || "推荐内容"}
        </h2>

        {/* 内容区域 */}
        <div className="relative">
          {/* 左右导航按钮 */}
          {totalPages > 1 && (
            <>
              <button
                onClick={goToPrevious}
                disabled={currentPage === 0}
                className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-10 h-10 bg-white/90 hover:bg-white rounded-full shadow-lg border border-gray-200 flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 -ml-5"
              >
                <svg
                  className="w-5 h-5 text-gray-700"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 19l-7-7 7-7"
                  />
                </svg>
              </button>

              <button
                onClick={goToNext}
                disabled={currentPage === totalPages - 1}
                className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-10 h-10 bg-white/90 hover:bg-white rounded-full shadow-lg border border-gray-200 flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 -mr-5"
              >
                <svg
                  className="w-5 h-5 text-gray-700"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </button>
            </>
          )}

          {/* 2行5列网格布局 */}
          <div className="grid grid-cols-5 gap-4 px-4">
            {getCurrentPageMovies().map((movie, index) => (
              <div
                key={movie.id || index}
                onClick={() => handleCardClick(movie)}
                className="cursor-pointer group"
              >
                {/* 海报容器 */}
                <div className="relative aspect-[3/4] mb-3 overflow-hidden rounded-lg bg-gray-100 shadow-md">
                  <img
                    src={getProxyImageUrl(
                      movie.pic?.normal || movie.pic?.large
                    )}
                    alt={movie.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    loading="lazy"
                    onError={(e) => {
                      e.target.style.display = "none";
                      e.target.parentNode.classList.add("bg-gray-200");
                    }}
                  />

                  {/* 集数信息 */}
                  {movie.episodes_info && (
                    <div className="absolute top-2 left-2 bg-black/80 text-white text-xs px-2 py-1 rounded font-medium">
                      {movie.episodes_info}
                    </div>
                  )}

                  {/* 新剧标签 */}
                  {movie.honor_infos && movie.honor_infos.length > 0 && (
                    <div className="absolute top-2 right-2">
                      <span className="inline-block bg-green-500 text-white text-xs px-2 py-1 rounded font-medium">
                        新
                      </span>
                    </div>
                  )}

                  {/* 悬浮遮罩 */}
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors duration-300" />
                </div>

                {/* 标题和评分紧贴居中显示 */}
                <div className="text-center mt-2">
                  <div className="inline-flex items-center gap-1">
                    <h3 className="font-medium text-sm text-gray-900 group-hover:text-blue-600 transition-colors leading-tight">
                      {movie.title}
                    </h3>

                    {formatRating(movie.rating) ? (
                      <span
                        className={`text-sm font-bold ${getRatingColor(
                          movie.rating
                        )}`}
                      >
                        {formatRating(movie.rating)}
                      </span>
                    ) : (
                      <span className="text-xs text-gray-400">暂无评分</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 分页指示器 */}
        {totalPages > 1 && (
          <div className="flex justify-center mt-6 space-x-2">
            {Array.from({ length: totalPages }, (_, index) => (
              <button
                key={index}
                onClick={() => setCurrentPage(index)}
                className={`w-3 h-3 rounded-full transition-all duration-200 ${
                  index === currentPage
                    ? "bg-blue-500 w-8"
                    : "bg-gray-300 hover:bg-gray-400"
                }`}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DoubanRecommendCards;

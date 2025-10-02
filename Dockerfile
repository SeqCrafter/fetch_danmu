# 使用多阶段构建 - 构建阶段
FROM python:3.13-slim as builder

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制requirements文件并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# 生产阶段
FROM python:3.13-slim as production

# 安装运行时依赖（如果需要的话）
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 创建用户（for huggingface spaces）
RUN useradd -m -u 1000 user
USER user

# 设置环境变量
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 设置工作目录
WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder --chown=user:user /opt/venv /opt/venv

# 复制应用代码
COPY --chown=user:user . .

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["python3", "-m", "robyn", "app.py", "--fast", "--log-level", "INFO"]

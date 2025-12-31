# 1. 使用官方 Python 轻量级镜像
FROM python:3.12-slim-bullseye

# 2. 设置工作目录
WORKDIR /app

# 3. 设置环境变量 (防止 Python 生成 .pyc 文件，设置时区为上海)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai

# 4. 安装系统依赖 (PDF处理和字体管理可能需要)
# libgl1-mesa-glx 是 matplotlib 有时需要的
# fontconfig 是字体管理工具
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# 5. 复制并安装 Python 依赖 (利用 Docker 缓存层)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. 处理中文字体 (解决 matplotlib 中文乱码)
# 将本地的 SimHei.ttf 复制到容器字体目录
COPY fonts/SimHei.ttf /usr/share/fonts/truetype/custom/SimHei.ttf
# 刷新字体缓存
RUN fc-cache -fv

# 7. 配置 Matplotlib 缓存目录 (防止权限问题)
ENV MPLCONFIGDIR=/tmp/matplotlib_cache
RUN mkdir -p /tmp/matplotlib_cache && chmod 777 /tmp/matplotlib_cache

# 8. 复制项目所有代码到容器
COPY . .

# 9. 暴露端口
EXPOSE 5000

# 10. 启动命令
CMD ["python", "app.py"]
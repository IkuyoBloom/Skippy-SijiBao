# 四季宝农技大脑（Skippy Agri AI Assistant）

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

面向中国农户的智能农业问答助手，支持**文字 / 图片 / 语音**多模态输入，结合实时气象数据为农户提供精准、可执行的农技建议。

> 项目获 **2026 中国大学生计算机设计大赛 西北赛区 三等奖**

## 功能特性

- **AI 农技问答**：基于通义千问（Qwen）流式对话，支持思考过程展示，专业回答农业栽培、病虫害防治、土壤肥料等问题
- **多模态输入**：支持上传作物图片进行病虫害识别，支持语音提问（讯飞语音识别，自动转文字）
- **气象农事决策**：接入和风天气 API，自动获取当前/未来 3 天/7 天天气，作为农事安排的参考依据
- **流式响应**：基于 SSE（Server-Sent Events）实现打字机式实时输出
- **会话状态管理**：识别用户姓名、种植作物、备注信息，进行个性化回答
- **HTTPS 支持**：提供 SSL 证书生成脚本与自动托管

## 技术栈

- **后端**：Python、FastAPI、Uvicorn、SSE-Starlette
- **大模型**：阿里云百炼 DashScope（通义千问，OpenAI 兼容接口）
- **语音识别**：讯飞开放平台（WebSocket、HMAC-SHA256 鉴权）
- **天气服务**：和风天气 API
- **多媒体**：FFmpeg、pydub（音频转 16kHz PCM）
- **前端**：原生 HTML / CSS / JavaScript

## 目录结构

```
SJB/
├── backend/
│   ├── main.py            # FastAPI 入口：SSE 流式接口、多模态文件处理、HTTPS
│   ├── ai_engine.py       # AI 引擎：模型调用、语音识别、气象获取、提示词编排
│   ├── generate_ssl.py    # 本地生成 SSL 证书脚本
│   └── bin/               # ffmpeg/ffprobe（体积大，请自行下载放入，不入库）
├── frontend/
│   └── index.html         # 前端页面
├── .env.example           # 环境变量示例（复制为 .env 并填入密钥）
└── requirements.txt
```

## 快速开始

1. **安装依赖**

   ```bash
   pip install -r requirements.txt
   ```

2. **下载并放置 FFmpeg**

   语音识别依赖 `ffmpeg`/`ffprobe`，请将 Windows 版可执行文件放入 `backend/bin/` 目录。

3. **配置密钥**

   ```bash
   cp .env.example .env
   ```

   在 `.env` 中填入：
   - `DASHSCOPE_API_KEY`：阿里云百炼 DashScope
   - `QWEATHER_KEY`：和风天气
   - `XFYUN_APP_ID` / `XFYUN_API_KEY` / `XFYUN_API_SECRET`：讯飞开放平台

4. **运行**

   ```bash
   cd backend
   python main.py
   # 有 SSL 证书时自动以 HTTPS 启动，否则以 HTTP 启动
   # 默认访问 http://127.0.0.1:8000
   ```

## 安全说明

`.env` 中的真实密钥已通过 `.gitignore` 排除，不会提交到仓库。请自行妥善保管密钥，切勿泄露。

## 开源协议

本项目基于 [MIT License](LICENSE) 开源，Copyright (c) 2026 IkuyoBloom。

任何人都可以自由使用、修改、分发本项目代码，包括用于商业目的，只需在副本或衍生作品中保留原始版权声明与许可声明。软件按「原样」提供，不附带任何形式的担保。

## 第三方服务声明

项目接入的第三方服务（阿里云百炼、和风天气、讯飞开放平台）不属于本项目，使用它们须遵守各自的服务条款，API 密钥的申请、保管与由此产生的费用由使用者自行负责。

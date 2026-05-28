# MiMo TTS Demo

基于小米 MiMo-V2.5-TTS API 的语音合成演示。

## 快速开始

### 1. 获取 API Key

前往 [Xiaomi MiMo 开放平台](https://platform.xiaomimimo.com) 注册并获取 API Key。

### 2. 安装依赖

```bash
cd ~/Her工作间/mimo-tts-demo
pip install -r requirements.txt
```

### 3. 配置 API Key

复制 `.env.example` 为 `.env`，填入你的 API Key：

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 MIMO_API_KEY
```

或者直接创建 `.env` 文件：

```
MIMO_API_KEY=你的API密钥
```

### 4. 启动服务

```bash
python app.py
```

访问 http://localhost:5001 即可使用。

## 功能

- 文本转语音（8 种预置音色）
- 风格控制（温柔、开心、悲伤、东北话等）
- 自定义风格描述（自然语言控制）
- 声音克隆（上传 5-15 秒音频）
- 苹果风格 UI
- 快捷键 Cmd/Ctrl + Enter 生成

## 技术栈

- 后端：Python Flask
- API：MiMo-V2.5-TTS（OpenAI 兼容格式）
- 前端：原生 HTML/CSS/JS

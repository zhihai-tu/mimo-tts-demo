# MiMo TTS Demo

基于小米 MiMo-V2.5-TTS API 的语音合成 Web 应用，支持预置音色、风格控制和声音克隆。

## 功能

- **8 种预置音色** — 中文/英文各 4 种，开箱即用
- **风格控制** — 音频标签（如磁性、温柔、东北话）+ 自然语言描述，可混用
- **声音克隆** — 上传 5-15 秒参考音频，复刻任意音色
- **下载音频** — 生成后可一键下载 WAV 文件
- **日志记录** — 自动按天分割，记录每次请求的输入、输出和耗时

## 快速开始

### 1. 获取 API Key

前往 [Xiaomi MiMo 开放平台](https://platform.xiaomimimo.com) 注册并获取 API Key。

### 2. 安装依赖

```bash
git clone https://github.com/zhihai-tu/mimo-tts-demo.git
cd mimo-tts-demo
pip install -r requirements.txt
```

### 3. 配置 API Key

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 API Key：

```
MIMO_API_KEY=你的API密钥
```

### 4. 启动服务

```bash
python app.py
```

访问 http://localhost:5001 即可使用。

## 预置音色

| 音色 | 语言 | 性别 |
|------|------|------|
| 冰糖 | 中文 | 女性 |
| 茉莉 | 中文 | 女性 |
| 苏打 | 中文 | 男性 |
| 白桦 | 中文 | 男性 |
| Mia | 英文 | 女性 |
| Chloe | 英文 | 女性 |
| Milo | 英文 | 男性 |
| Dean | 英文 | 男性 |

## 风格控制

支持两种方式，可独立使用也可组合：

**音频标签** — 在文本开头加 `(标签)`，支持多标签叠加：

```
(磁性 温柔)夜已经深了，城市还在呼吸。
```

**自然语言** — 用一句话描述想要的风格：

```
用轻快上扬的语调，语速稍快，声音明亮有活力
```

更多用法参见 [MiMo TTS 官方文档](https://platform.xiaomimimo.com/docs/zh-CN/usage-guide/speech-synthesis-v2.5)。

## 声音克隆

上传一段 **5-15 秒** 的纯人声音频（WAV/MP3，≤10MB），即可复刻该音色。

> 声音克隆需要分析参考音频特征，耗时较长（约 30-60 秒），属于正常现象。

## API 直接调用

如果不使用本项目，也可以直接调用 MiMo API。`demo/` 目录下有 curl 调用示例。

## 项目结构

```
mimo-tts-demo/
├── app.py              # Flask 后端，API 路由与 TTS 调用
├── requirements.txt    # Python 依赖
├── .env.example        # 配置模板
├── static/
│   └── index.html      # 前端页面（苹果风格 UI）
├── demo/
│   └── curl-examples.md  # curl 调用示例
├── outputs/            # 生成的音频文件（自动创建）
└── logs/               # 日志文件，按天分割（自动创建）
```

## 技术栈

- **后端**：Python Flask
- **API**：[MiMo-V2.5-TTS](https://platform.xiaomimimo.com)（OpenAI 兼容格式）
- **前端**：原生 HTML/CSS/JS

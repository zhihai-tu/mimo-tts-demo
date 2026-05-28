# MiMo TTS curl 调用示例

## 非流式调用（推荐）

返回 base64 编码的音频，直接解码保存为 wav 文件。

```bash
curl --location --request POST 'https://token-plan-cn.xiaomimimo.com/v1/chat/completions' \
--header "api-key: $MIMO_API_KEY" \
--header 'Content-Type: application/json' \
--data-raw '{
    "model": "mimo-v2.5-tts",
    "messages": [
        {
            "role": "user",
            "content": "用轻快上扬的语调，声音明亮有活力"
        },
        {
            "role": "assistant",
            "content": "你好，今天天气真不错！"
        }
    ],
    "audio": {
        "format": "wav",
        "voice": "冰糖"
    }
}' | python3 -c "
import sys, json, base64
resp = json.load(sys.stdin)
b64 = resp['choices'][0]['message']['audio']['data']
with open('output.wav', 'wb') as f:
    f.write(base64.b64decode(b64))
print('saved')
"
```

## 一行命令版

```bash
curl ... | python3 -c "import sys,json,base64; r=json.load(sys.stdin); open('out.wav','wb').write(base64.b64decode(r['choices'][0]['message']['audio']['data']))"
```

## 参数说明

| 参数 | 说明 |
|------|------|
| `model` | `mimo-v2.5-tts`（预置音色）/ `mimo-v2.5-tts-voicedesign`（文本设计音色）/ `mimo-v2.5-tts-voiceclone`（音色克隆） |
| `messages[0].role=user` | 风格控制指令（可选），如"温柔"、"东北话"、"开心"等 |
| `messages[1].role=assistant` | 要合成的文本内容（必填） |
| `audio.format` | `wav`（非流式）/ `pcm16`（流式） |
| `audio.voice` | 音色 ID：冰糖、茉莉、苏打、白桦、Mia、Chloe、Milo、Dean |

## 预置音色

| 音色 | Voice ID | 语言 | 性别 |
|------|----------|------|------|
| 冰糖 | 冰糖 | 中文 | 女性 |
| 茉莉 | 茉莉 | 中文 | 女性 |
| 苏打 | 苏打 | 中文 | 男性 |
| 白桦 | 白桦 | 中文 | 男性 |
| Mia | Mia | 英文 | 女性 |
| Chloe | Chloe | 英文 | 女性 |
| Milo | Milo | 英文 | 男性 |
| Dean | Dean | 英文 | 男性 |

## 风格控制示例

```bash
# 自然语言控制（放在 user message 中）
"content": "用轻快上扬的语调，语速稍快，声音明亮有活力"

# 音频标签控制（放在 assistant message 文本开头）
"content": "(磁性)夜已经深了，城市还在呼吸。我是今晚陪你的人。"
```

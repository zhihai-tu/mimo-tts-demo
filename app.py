import os
import base64
import json
import logging
import time
import uuid
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv

# 加载 .env 配置文件
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__, static_folder="static")
CORS(app)

LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("tts")
logger.setLevel(logging.INFO)
handler = TimedRotatingFileHandler(
    os.path.join(LOG_DIR, "tts.log"),
    when="midnight",
    backupCount=30,
    encoding="utf-8",
)
handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
logger.addHandler(handler)

MIMO_API_KEY = os.environ.get("MIMO_API_KEY", "")

if not MIMO_API_KEY:
    raise ValueError("请在 .env 文件中配置 MIMO_API_KEY")

client = OpenAI(
    api_key=MIMO_API_KEY,
    base_url="https://token-plan-cn.xiaomimimo.com/v1",
)

VOICE_OPTIONS = [
    {"id": "冰糖", "name": "冰糖", "lang": "中文", "gender": "女性"},
    {"id": "茉莉", "name": "茉莉", "lang": "中文", "gender": "女性"},
    {"id": "苏打", "name": "苏打", "lang": "中文", "gender": "男性"},
    {"id": "白桦", "name": "白桦", "lang": "中文", "gender": "男性"},
    {"id": "Mia", "name": "Mia", "lang": "英文", "gender": "女性"},
    {"id": "Chloe", "name": "Chloe", "lang": "英文", "gender": "女性"},
    {"id": "Milo", "name": "Milo", "lang": "英文", "gender": "男性"},
    {"id": "Dean", "name": "Dean", "lang": "英文", "gender": "男性"},
]


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/voices")
def voices():
    return jsonify(VOICE_OPTIONS)


@app.route("/api/tts", methods=["POST"])
def tts():
    if not MIMO_API_KEY:
        return jsonify({"error": "未配置 MIMO_API_KEY 环境变量"}), 400

    data = request.json
    text = data.get("text", "").strip()
    voice = data.get("voice", "冰糖")
    tags = data.get("tags", "").strip()
    natural = data.get("natural", "").strip()
    voice_mode = data.get("voice_mode", "preset")  # preset / clone
    clone_audio_b64 = data.get("clone_audio", "").strip()  # base64 with data: prefix

    if not text:
        return jsonify({"error": "请输入文本内容"}), 400

    if voice_mode == "clone" and not clone_audio_b64:
        return jsonify({"error": "请上传参考音频"}), 400

    messages = []

    # 自然语言控制 → user message
    if natural:
        messages.append({"role": "user", "content": natural})

    # 音频标签控制 → 拼到 assistant content 开头
    assistant_content = f"({tags}){text}" if tags else text
    messages.append({"role": "assistant", "content": assistant_content})

    # 选择模型和 voice 参数
    if voice_mode == "clone":
        model = "mimo-v2.5-tts-voiceclone"
        audio_body = {"format": "wav", "voice": clone_audio_b64}
    else:
        model = "mimo-v2.5-tts"
        audio_body = {"format": "wav", "voice": voice}

    log_voice = f"clone" if voice_mode == "clone" else voice
    logger.info(f"REQUEST | model={model} | voice={log_voice} | tags={tags} | natural={natural[:100]}")
    logger.info(f"REQUEST | messages=\n{json.dumps(messages, ensure_ascii=False, indent=2)}")

    t0 = time.time()
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            extra_body={"audio": audio_body},
        )

        message = completion.choices[0].message
        audio_obj = message.audio
        if isinstance(audio_obj, dict):
            audio_b64 = audio_obj.get("data", "")
        else:
            audio_bytes = base64.b64decode(audio_obj.data)
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        elapsed = round(time.time() - t0, 2)
        logger.info(f"RESPONSE | ok | audio_size={len(audio_b64)} chars | elapsed={elapsed}s")

        audio_bytes = base64.b64decode(audio_b64)
        filename = f"tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.wav"
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(audio_bytes)
        logger.info(f"SAVED | {filepath}")

        return jsonify({"audio": audio_b64, "format": "wav", "file": filename})

    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        logger.info(f"RESPONSE | error | {e} | elapsed={elapsed}s")
        return jsonify({"error": str(e)}), 500


@app.route("/api/download/<filename>")
def download(filename):
    filepath = os.path.join(OUTPUT_DIR, filename)
    if not os.path.isfile(filepath):
        return jsonify({"error": "文件不存在"}), 404
    return send_file(filepath, as_attachment=True, download_name=filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

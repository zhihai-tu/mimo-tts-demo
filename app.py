import base64
import json
import logging
import os
import sqlite3
import time
import uuid
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
from openai import OpenAI

# 加载 .env 配置文件
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
CLONES_DIR = os.path.join(OUTPUT_DIR, "clones")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CLONES_DIR, exist_ok=True)

DB_PATH = os.path.join(BASE_DIR, "voices.db")

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
MIMO_BASE_URL = os.environ.get("MIMO_BASE_URL", "")

if not MIMO_API_KEY:
    raise ValueError("请在 .env 文件中配置 MIMO_API_KEY")
if not MIMO_BASE_URL:
    raise ValueError("请在 .env 文件中配置 MIMO_BASE_URL")

client = OpenAI(
    api_key=MIMO_API_KEY,
    base_url=MIMO_BASE_URL,
)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS saved_voices (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            filename TEXT NOT NULL,
            duration_sec REAL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


init_db()

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
    try:
        return _tts_inner()
    except Exception as e:
        logger.info(f"RESPONSE | error | {e}")
        return jsonify({"error": str(e)}), 500


def _tts_inner():
    if not MIMO_API_KEY:
        return jsonify({"error": "未配置 MIMO_API_KEY 环境变量"}), 400

    data = request.json
    text = data.get("text", "").strip()
    voice = data.get("voice", "冰糖")
    tags = data.get("tags", "").strip()
    natural = data.get("natural", "").strip()
    voice_mode = data.get("voice_mode", "preset")  # preset / clone
    clone_audio_b64 = data.get("clone_audio", "").strip()  # base64 with data: prefix
    clone_voice_id = data.get("clone_voice_id", "").strip()  # saved voice id

    if not text:
        return jsonify({"error": "请输入文本内容"}), 400

    if voice_mode == "clone" and not clone_audio_b64 and not clone_voice_id:
        return jsonify({"error": "请上传或选择参考音频"}), 400

    # If using saved voice, load from disk
    if voice_mode == "clone" and clone_voice_id:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM saved_voices WHERE id = ?", (clone_voice_id,)
        ).fetchone()
        conn.close()
        if not row:
            return jsonify({"error": "所选音色不存在"}), 404
        filepath = os.path.join(CLONES_DIR, row["filename"])
        if not os.path.isfile(filepath):
            return jsonify({"error": "音色文件丢失"}), 404
        with open(filepath, "rb") as f:
            audio_bytes = f.read()
        ext = row["filename"].rsplit(".", 1)[-1]
        mime = "audio/wav" if ext == "wav" else "audio/mpeg"
        clone_audio_b64 = (
            f"data:{mime};base64," + base64.b64encode(audio_bytes).decode()
        )

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
    logger.info(
        f"REQUEST | model={model} | voice={log_voice} | tags={tags} | natural={natural[:100]}"
    )
    logger.info(
        f"REQUEST | messages=\n{json.dumps(messages, ensure_ascii=False, indent=2)}"
    )

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
        logger.info(
            f"RESPONSE | ok | audio_size={len(audio_b64)} chars | elapsed={elapsed}s"
        )

        audio_bytes = base64.b64decode(audio_b64)
        filename = (
            f"tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.wav"
        )
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(audio_bytes)
        logger.info(f"SAVED | {filepath}")

        return jsonify({"audio": audio_b64, "format": "wav", "file": filename})

    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        logger.info(f"RESPONSE | error | {e} | elapsed={elapsed}s")
        return jsonify({"error": str(e)}), 500


@app.route("/api/voices/saved", methods=["GET"])
def list_saved_voices():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM saved_voices ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/voices/saved", methods=["POST"])
def save_voice():
    data = request.json
    name = data.get("name", "").strip()
    audio_b64 = data.get("audio", "").strip()  # data:audio/...;base64,...

    if not name:
        return jsonify({"error": "请输入音色名称"}), 400
    if not audio_b64:
        return jsonify({"error": "请提供音频数据"}), 400

    voice_id = uuid.uuid4().hex[:12]
    ext = "wav"
    if "audio/mpeg" in audio_b64 or "audio/mp3" in audio_b64:
        ext = "mp3"
    filename = f"{voice_id}.{ext}"
    filepath = os.path.join(CLONES_DIR, filename)

    # Decode and save
    header, b64data = audio_b64.split(",", 1)
    audio_bytes = base64.b64decode(b64data)
    with open(filepath, "wb") as f:
        f.write(audio_bytes)

    created_at = datetime.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO saved_voices (id, name, filename, created_at) VALUES (?, ?, ?, ?)",
        (voice_id, name, filename, created_at),
    )
    conn.commit()
    conn.close()

    logger.info(f"VOICE_SAVED | id={voice_id} | name={name} | file={filename}")
    return jsonify(
        {"id": voice_id, "name": name, "filename": filename, "created_at": created_at}
    )


@app.route("/api/voices/saved/<voice_id>", methods=["DELETE"])
def delete_saved_voice(voice_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM saved_voices WHERE id = ?", (voice_id,)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "音色不存在"}), 404

    filepath = os.path.join(CLONES_DIR, row["filename"])
    if os.path.isfile(filepath):
        os.remove(filepath)

    conn.execute("DELETE FROM saved_voices WHERE id = ?", (voice_id,))
    conn.commit()
    conn.close()

    logger.info(f"VOICE_DELETED | id={voice_id}")
    return jsonify({"ok": True})


@app.route("/api/voices/saved/<voice_id>/rename", methods=["POST"])
def rename_saved_voice(voice_id):
    data = request.json
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "名称不能为空"}), 400

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM saved_voices WHERE id = ?", (voice_id,)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "音色不存在"}), 404

    conn.execute("UPDATE saved_voices SET name = ? WHERE id = ?", (name, voice_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "name": name})


@app.route("/api/download/<filename>")
def download(filename):
    filepath = os.path.join(OUTPUT_DIR, filename)
    if not os.path.isfile(filepath):
        return jsonify({"error": "文件不存在"}), 404
    return send_file(filepath, as_attachment=True, download_name=filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

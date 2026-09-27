import os
import json
import sqlite3
from datetime import datetime

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB

UPLOAD_FOLDER = "data/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE = "data/voicenote.db"
TRANSCRIPTION_MODEL = "whisper-large-v3-turbo"
SUMMARY_MODEL = "openai/gpt-oss-20b"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            transcript TEXT NOT NULL,
            summary TEXT,
            highlights TEXT,
            action_items TEXT,
            questions TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def get_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Create a .env file and add your Groq API key."
        )
    return Groq(api_key=api_key)


def generate_ai_summary(transcript):
    client = get_client()

    system_prompt = """
You are VoiceNote AI, an assistant that converts meeting/class/lecture
transcripts into useful structured notes.

Analyze ONLY the transcript provided by the user. Do not invent facts.

Return a JSON object with exactly these fields:
{
  "summary": "A concise paragraph of 3-6 sentences.",
  "highlights": ["3-8 important points"],
  "action_items": ["specific tasks mentioned or clearly implied by the transcript"],
  "questions": ["important unanswered questions or follow-up questions"]
}

Rules:
- Keep the summary factual and concise.
- Highlights must contain the most important information.
- Action items should be empty if no actions are present.
- Questions should be empty if there are no meaningful follow-up questions.
- Do not add information that is not supported by the transcript.
"""

    user_prompt = f"Transcript:\n\n{transcript}"

    response = client.chat.completions.create(
        model=SUMMARY_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_completion_tokens=1500,
        include_reasoning=False,
    )

    content = response.choices[0].message.content
    data = json.loads(content)

    return {
        "summary": data.get("summary", ""),
        "highlights": data.get("highlights", []),
        "action_items": data.get("action_items", []),
        "questions": data.get("questions", []),
    }


def transcribe_audio(file_path):
    client = get_client()

    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model=TRANSCRIPTION_MODEL,
            response_format="text",
            temperature=0.0,
        )

    return transcription.text if hasattr(transcription, "text") else str(transcription)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/process", methods=["POST"])
def process_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file was uploaded."}), 400

    audio = request.files["audio"]

    if not audio.filename:
        return jsonify({"error": "Please select or record an audio file."}), 400

    allowed_extensions = {
        ".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".ogg", ".wav", ".webm", ".flac"
    }
    extension = os.path.splitext(audio.filename)[1].lower()

    if extension not in allowed_extensions:
        return jsonify({
            "error": "Unsupported audio format. Use MP3, WAV, M4A, OGG, WebM, FLAC or MP4."
        }), 400

    safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{extension}"
    file_path = os.path.join(UPLOAD_FOLDER, safe_name)
    audio.save(file_path)

    try:
        transcript = transcribe_audio(file_path)

        if not transcript.strip():
            return jsonify({"error": "No speech could be detected in the audio."}), 400

        ai_result = generate_ai_summary(transcript)

        conn = get_db()
        conn.execute(
            """
            INSERT INTO notes
            (filename, transcript, summary, highlights, action_items, questions, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audio.filename,
                transcript,
                ai_result["summary"],
                json.dumps(ai_result["highlights"]),
                json.dumps(ai_result["action_items"]),
                json.dumps(ai_result["questions"]),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
        note_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()

        return jsonify({
            "success": True,
            "id": note_id,
            "filename": audio.filename,
            "transcript": transcript,
            **ai_result,
        })

    except Exception as e:
        return jsonify({
            "error": f"Processing failed: {str(e)}"
        }), 500

    finally:
        try:
            os.remove(file_path)
        except OSError:
            pass


@app.route("/api/notes", methods=["GET"])
def get_notes():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT id, filename, summary, created_at
        FROM notes
        ORDER BY id DESC
        LIMIT 20
        """
    ).fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])


@app.route("/api/notes/<int:note_id>", methods=["GET"])
def get_note(note_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM notes WHERE id = ?", (note_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return jsonify({"error": "Note not found."}), 404

    result = dict(row)
    result["highlights"] = json.loads(result["highlights"] or "[]")
    result["action_items"] = json.loads(result["action_items"] or "[]")
    result["questions"] = json.loads(result["questions"] or "[]")

    return jsonify(result)


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "The uploaded file is too large. Maximum size is 100 MB."}), 413


init_db()

if __name__ == "__main__":
    app.run(debug=True)

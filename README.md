# VoiceNote AI

VoiceNote AI is a Generative AI application that converts recorded or uploaded audio into text and then generates structured AI notes.

## Features

- Browser microphone recording
- Audio file upload
- Speech-to-text using Groq Whisper Large V3 Turbo
- AI-generated summary
- Key highlights
- Action items
- Follow-up questions
- Transcript display
- SQLite storage
- Copy-all notes button
- Flask backend
- Deployment-ready for Render

## Technology Stack

- Python
- Flask
- Groq API
- Whisper Large V3 Turbo
- OpenAI GPT-OSS 20B through Groq
- SQLite
- HTML/CSS/JavaScript

## Run locally

1. Install Python 3.11 or newer.
2. Open a terminal in this project folder.
3. Create a virtual environment:

   Windows:
   `python -m venv venv`

4. Activate it:

   Windows PowerShell:
   `venv\Scripts\Activate.ps1`

   Windows Command Prompt:
   `venv\Scripts\activate`

5. Install packages:

   `pip install -r requirements.txt`

6. Create a file named `.env` and add:

   `GROQ_API_KEY=your_key_here`

7. Run:

   `python app.py`

8. Open:

   `http://127.0.0.1:5000`

## Important

Never upload your `.env` file or Groq API key to GitHub. The `.gitignore` file already excludes `.env`.

## Project Flow

Audio -> Whisper Speech Recognition -> Transcript -> Prompt -> GPT-OSS 20B -> Structured AI Notes -> SQLite

## Deployment

For Render:
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`
- Environment Variable: `GROQ_API_KEY`

The deployed application needs the GROQ_API_KEY configured in Render.

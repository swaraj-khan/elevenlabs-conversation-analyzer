import os
import ast
from dotenv import load_dotenv
from fastapi import FastAPI
from supabase import create_client
from google import genai

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
TABLE_NAME = os.getenv("SUPABASE_TABLE")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

client = genai.Client()
app = FastAPI()

def load_system_prompt():
    with open("prompts/intention-finder.md", "r") as f:
        return f.read()


def fetch_latest_call(phone: str):
    formatted_phone = f"+91{phone}"

    response = (
        supabase
        .table(TABLE_NAME)
        .select("call_id, caller, recording_path, transcript, created_at")
        .eq("caller", formatted_phone)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    calls = response.data

    if not calls:
        return None

    return calls[0]


def clean_transcript(transcript):
    if isinstance(transcript, str):
        transcript = ast.literal_eval(transcript)
    cleaned = []
    for item in transcript:
        message = item.get("message")
        role = item.get("role")
        if message:
            cleaned.append({
                "role": role,
                "message": message
            })
    return cleaned


def summarize_conversation(transcript):

    system_prompt = load_system_prompt()

    conversation_text = "\n".join(
        f"{msg['role']}: {msg['message']}"
        for msg in transcript
    )

    prompt = f"""
        {system_prompt}

        Conversation:
        {conversation_text}
        """

    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL"),
        contents=prompt
    )
    return response.text.strip()


@app.get("/calls/{phone}/summary")
def get_call_summary(phone: str):
    call = fetch_latest_call(phone)

    if not call:
        return {"message": "No calls found"}

    transcript = clean_transcript(call["transcript"])
    summary = summarize_conversation(transcript)

    return {
        "call_id": call["call_id"],
        "caller": call["caller"],
        "recording_path": call["recording_path"],
        "summary": summary
    }


@app.get("/calls/{phone}/transcript")
def get_call_transcript(phone: str):
    call = fetch_latest_call(phone)

    if not call:
        return {"message": "No calls found"}

    transcript = clean_transcript(call["transcript"])

    return {
        "call_id": call["call_id"],
        "caller": call["caller"],
        "recording_path": call["recording_path"],
        "transcript": transcript
    }
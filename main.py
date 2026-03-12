import os
import ast
import re
from dotenv import load_dotenv
from fastapi import FastAPI
from supabase import create_client
from google import genai
from mangum import Mangum
from pymongo import MongoClient
from bson import ObjectId

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
TABLE_NAME = os.getenv("SUPABASE_TABLE")
MONGO_URI = os.getenv("MONGO_URI")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

mongo_client = MongoClient(MONGO_URI)
read_db = mongo_client["kovon-nurse-preprod"]

genai_client = genai.Client(api_key=GOOGLE_API_KEY)

app = FastAPI()
handler = Mangum(app)


def normalize_phone(num: str) -> str:
    num = re.sub(r"[^0-9+]", "", num)
    if num.startswith("+91") and len(num) == 13:
        return num
    if len(num) == 10:
        return f"+91{num}"
    if len(num) == 12 and num.startswith("91"):
        return f"+{num}"
    return num


def serialize(doc):
    if isinstance(doc, list):
        return [serialize(d) for d in doc]
    if isinstance(doc, dict):
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                doc[k] = str(v)
            elif isinstance(v, (dict, list)):
                doc[k] = serialize(v)
    return doc


def load_system_prompt():
    with open("prompts/intention-finder.md", "r") as f:
        return f.read()


def fetch_latest_call(phone: str):
    response = (
        supabase
        .table(TABLE_NAME)
        .select("call_id, caller, recording_path, transcript, created_at")
        .eq("caller", phone)
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
    response = genai_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )
    return response.text.strip()


@app.get("/calls/{phone}/summary")
def get_summary(phone: str):
    normalized_phone = normalize_phone(phone)
    user = read_db.users.find_one({"phoneNumber": normalized_phone})
    user_data = serialize(user) if user else None
    call = fetch_latest_call(normalized_phone)

    if not call:
        return {
            "success": True,
            "normalized": normalized_phone,
            "user": user_data,
            "call": None
        }

    transcript = clean_transcript(call["transcript"])
    summary = summarize_conversation(transcript)

    return {
        "success": True,
        "normalized": normalized_phone,
        "user": user_data,
        "call": {
            "call_id": call["call_id"],
            "caller": call["caller"],
            "recording_path": call["recording_path"],
            "summary": summary
        }
    }


@app.get("/calls/{phone}/transcript")
def get_transcript(phone: str):
    normalized_phone = normalize_phone(phone)
    call = fetch_latest_call(normalized_phone)

    if not call:
        return {
            "success": True,
            "phone": normalized_phone,
            "transcript": None
        }

    transcript = clean_transcript(call["transcript"])

    return {
        "success": True,
        "phone": normalized_phone,
        "transcript": transcript
    }
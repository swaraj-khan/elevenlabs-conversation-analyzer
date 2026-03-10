import os
import ast
from dotenv import load_dotenv
from fastapi import FastAPI
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()


@app.get("/calls/{phone}")
def get_calls(phone: str):
    formatted_phone = f"+91{phone}"
    response = (
        supabase
        .table("voice_calls")
        .select("call_id, caller, recording_path, transcript, created_at")
        .eq("caller", formatted_phone)
        .order("created_at", desc=True)
        .execute()
    )
    calls = response.data
    if not calls:
        return {"message": "No calls found for this number"}
    results = []
    for call in calls:
        transcript = call.get("transcript")
        if isinstance(transcript, str):
            transcript = ast.literal_eval(transcript)
        cleaned_transcript = []
        for item in transcript:
            message = item.get("message")
            role = item.get("role")
            if message:
                cleaned_transcript.append({
                    "role": role,
                    "message": message
                })
        results.append({
            "call_id": call["call_id"],
            "caller": call["caller"],
            "recording_path": call["recording_path"],
            "transcript": cleaned_transcript
        })
    return {
        "total_calls": len(results),
        "calls": results
    }
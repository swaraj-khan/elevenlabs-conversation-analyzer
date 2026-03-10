import os
import json
import ast
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
response = (
    supabase
    .table("voice_calls")
    .select("caller, recording_path, transcript")
    .order("created_at", desc=True)
    .limit(1)
    .execute()
)
data = response.data
if not data:
    print("No records found")
else:
    call = data[0]
    print("\nCaller:")
    print(call.get("caller"))
    print("\nRecording Path:")
    print(call.get("recording_path"))
    print("\nTranscript Preview:\n")
    transcript = call.get("transcript")
    if isinstance(transcript, str):
        transcript = ast.literal_eval(transcript)
    for item in transcript:
        role = item.get("role")
        message = item.get("message")
        if message:
            print(f"{role}: {message}")
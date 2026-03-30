import os
import ast
import re
from fastapi import FastAPI, Query
from supabase import create_client
from mangum import Mangum
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
TABLE_NAME = os.getenv("SUPABASE_TABLE")
MONGO_URI = os.getenv("MONGO_URI")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

mongo_client = MongoClient(
    MONGO_URI,
    maxPoolSize=10,
    serverSelectionTimeoutMS=2000
)

read_db = mongo_client["kovon-nurse-preprod"]
write_db = mongo_client["AI-BOT"]

app = FastAPI()
handler = Mangum(app)


class SaveProfileRequest(BaseModel):
    phoneNumber: str
    fullName: str
    primarySkill: str
    targetCountry: str
    secondarySkill: Optional[str] = None
    secondaryCountry: Optional[str] = None
    experienceType: Optional[str] = None
    internationalExperience: Optional[bool] = None


class ApplyJobRequest(BaseModel):
    job_id: str
    user_id: Optional[str] = None


class RaiseQueryRequest(BaseModel):
    userId: str
    title: str
    description: str


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


def fetch_latest_call(phone: str):

    response = (
        supabase
        .table(TABLE_NAME)
        .select("call_id, caller, recording_path, transcript, summary, created_at")
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


@app.get("/calls/{phone}/summary")
def get_summary(phone: str):

    normalized_phone = normalize_phone(phone)

    user = read_db.users.find_one({"phoneNumber": normalized_phone})
    user_data = serialize(user) if user else None

    call = fetch_latest_call(normalized_phone)

    if not call:
        return None

    return {
        "success": True,
        "normalized": normalized_phone,
        "user": user_data,
        "call": {
            "call_id": call.get("call_id"),
            "caller": call.get("caller"),
            "recording_path": call.get("recording_path"),
            "summary": call.get("summary")
        }
    }


@app.get("/calls/{phone}/transcript")
def get_transcript(phone: str):

    normalized_phone = normalize_phone(phone)

    call = fetch_latest_call(normalized_phone)

    if not call:
        return None

    transcript = clean_transcript(call["transcript"]) if call.get("transcript") else None

    return {
        "success": True,
        "phone": normalized_phone,
        "transcript": transcript
    }

@app.post("/save-profile")
def save_profile(data: SaveProfileRequest):

    normalized = normalize_phone(data.phoneNumber)

    update_data = {
        "fullName": data.fullName,
        "targetJobRole": {"name": data.primarySkill},
        "secondaryJobRoles": [{"name": data.secondarySkill}] if data.secondarySkill else [],
        "targetCountry": {"name": data.targetCountry},
        "secondaryCountries": [{"name": data.secondaryCountry}] if data.secondaryCountry else [],
        "experienceType": data.experienceType,
        "internationalExperience": data.internationalExperience,
        "isProfileCompleted": True,
        "updatedAt": datetime.utcnow()
    }

    write_db.users.update_one(
        {"phoneNumber": normalized},
        {
            "$set": update_data,
            "$setOnInsert": {
                "phoneNumber": normalized,
                "createdAt": datetime.utcnow()
            }
        },
        upsert=True
    )

    return {
        "success": True,
        "phoneNumber": normalized
    }


@app.get("/jobs")
def list_jobs(country: str = Query(None), role: str = Query(None)):

    match = {
        "isActive": True,
        "status": "PUBLISHED"
    }

    if country:
        match["location.country"] = {"$regex": country, "$options": "i"}

    if role:
        match["jobRole.name"] = {"$regex": role, "$options": "i"}

    jobs = list(
        read_db.jobs.find(
            match,
            {
                "title": 1,
                "location.country": 1,
                "salary.dataForCandidate": 1,
                "salary.frequency": 1,
                "company.name": 1
            }
        ).limit(20)
    )

    result = [
        {
            "id": str(j["_id"]),
            "title": j.get("title"),
            "country": j.get("location", {}).get("country"),
            "salary": j.get("salary", {}).get("dataForCandidate", {}),
            "frequency": j.get("salary", {}).get("frequency"),
            "company": j.get("company", {}).get("name")
        }
        for j in jobs
    ]

    return {
        "success": True,
        "jobs": result
    }


@app.get("/applications/{user_id}")
def get_applications(user_id: str):

    apps = list(
        read_db.appliedjobs.find(
            {"userId": ObjectId(user_id)},
            {
                "jobSnapshot.title": 1,
                "applicationStatus": 1
            }
        )
    )

    result = [
        {
            "title": a.get("jobSnapshot", {}).get("title"),
            "status": a.get("applicationStatus")
        }
        for a in apps
    ]

    return {
        "success": True,
        "applications": result
    }


@app.post("/applyJob")
def apply_job(data: ApplyJobRequest):

    result = write_db.job_applications.insert_one({
        "userId": ObjectId(data.user_id) if data.user_id else None,
        "jobId": ObjectId(data.job_id),
        "appliedAt": datetime.utcnow(),
        "status": "APPLIED"
    })

    return {
        "success": True,
        "applicationId": str(result.inserted_id)
    }


@app.post("/raise-query")
def raise_query(data: RaiseQueryRequest):

    write_db.queries.insert_one({
        "userId": ObjectId(data.userId),
        "requestTitle": data.title,
        "description": data.description,
        "createdAt": datetime.utcnow()
    })

    return {
        "success": True
    }
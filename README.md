# ElevenLabs Conversation Analyzer

A FastAPI-based backend service that analyzes voice call transcripts and generates concise, structured summaries. The system retrieves conversation data from Supabase, processes transcripts using Google Gemini AI, and produces structured insights from the latest conversation.

The service is designed to run serverlessly on **AWS Lambda using the Serverless Framework**, enabling scalable deployment without managing servers.

## Purpose (For my specific use case)

This tool extracts actionable intelligence from conversational data between recruitment agents and job seekers by:

- Parsing raw transcript data from voice calls
- Identifying the user’s intent, job role preference, and country preference
- Capturing key actions taken during the call (job selection, applications, information requests, etc.)
- Extracting follow-up instructions such as callbacks or next steps
- Converting long conversations into structured summaries that can power automated recruitment workflows

## Deployment Architecture

The service runs as a **FastAPI application deployed to AWS Lambda** using **Mangum** as the ASGI adapter.

Components involved:

- FastAPI — API framework
- AWS Lambda — serverless compute runtime
- API Gateway (HTTP API) — exposes the endpoints
- Supabase — stores call transcripts and metadata
- MongoDB — stores user profile information
- Google Gemini — generates conversation summaries
- Serverless Framework — deployment and infrastructure management

## API Endpoints

### Get Call Summary

Endpoint

```
GET /calls/{phone}/summary
```

Example Request

```
https://gclrxxxx.execute-api.ap-south-1.amazonaws.com/calls/+919999999999/summary
```

Example Response

```json
{
  "success": true,
  "normalized": "+919999999999",
  "user": {
    "_id": "6971bb5c37689459eb51b7fa",
    "phoneNumber": "+918618893815",
    "userType": "NURSE_CANDIDATE",
    "isProfileCompleted": true,
    "skills": [
      "Software Engineer",
      "Teamwork",
      "Communication"
    ],
    "language": {
      "motherTongue": "Telugu",
      "other": [
        "English",
        "Hindi"
      ]
    },
    "fullName": "Jimmy",
    "targetCountry": {
      "name": "United Arab Emirates",
      "id": "68cba3b774343689c6c174ec"
    },
    "targetJobRole": {
      "id": "692d47d56cb8ef66cdc7e092",
      "name": "Carpenter"
    }
  },
  "call": {
    "call_id": "conv_3101kkgd6q9mec9a1spry5mhsbyx",
    "caller": "+918618893815",
    "recording_path": "conv_3101kkgd6q9mec9a1spry5mhsbyx.mp3",
    "summary": "User Intent: Confirm interest in overseas job opportunities.\nJob Role: Carpenter\nCountry Preference: United Arab Emirates\nAction Taken: Interest confirmed\nNext Step / Request: Agent to find relevant job opportunities\nCallback Time:"
  }
}
```

### Get Full Transcript

Endpoint

```
GET /calls/{phone}/transcript
```

Example Request

```
https://gclrxxxx.execute-api.ap-south-1.amazonaws.com/calls/+919999999999/transcript
```

Example Response

```json
{
  "success": true,
  "phone": "+919999999999",
  "transcript": [
    {
      "role": "agent",
      "message": "नमस्कार, मैं कोवन से नेहा बोल रही हूँ। हम विदेशों में सत्यापित नौकरी के अवसर उपलब्ध कराते हैं। क्या आप इस बातचीत को आगे जारी रखना चाहेंगे?"
    },
    {
      "role": "user",
      "message": "हाँ जी।"
    },
    {
      "role": "agent",
      "message": "नमस्ते Jimmy, मैं देख रही हूँ कि आप United Arab Emirates में Carpenter की jobs explore कर रहे थे। क्या आप अभी भी वहाँ opportunities देख रहे हैं?"
    },
    {
      "role": "user",
      "message": "..."
    }
  ]
}
```

## Summary Output Structure

The summary returned by the AI follows a strict structure:

```
User Intent: <user's primary goal>
Job Role: <job role discussed or selected>
Country Preference: <country mentioned>
Action Taken: <what occurred during the call>
Next Step / Request: <user's requested next action>
Callback Time: <specific callback datetime if requested, otherwise blank>
```

## Environment Variables

Create a `.env` file in the project root.

```
SUPABASE_TABLE=voice_calls
SUPABASE_URL=xxxx
SUPABASE_ANON_KEY=xxxx
GOOGLE_API_KEY=xxxx
GEMINI_MODEL=gemini-2.5-flash
MONGO_URI=xxxx
```

## Database Schema

The service reads call data from the `voice_calls` table in Supabase.

```
create table public.<table_name> (
  id uuid not null default gen_random_uuid (),
  call_id text not null,
  caller text null,
  callee text null,
  status text null,
  duration integer null,
  transcript text null,
  recording_path text null,
  cost numeric null,
  metadata jsonb null,
  raw_payload jsonb null,
  created_at timestamp with time zone null default now(),
  constraint <table_name>_pkey primary key (id),
  constraint <table_name>_id_key unique (call_id)
);
```

## Local & Prod

Install dependencies into the `python` folder (required for Lambda packaging).

```
pip install -r requirements.txt -t python
```

Run the API locally using Serverless Offline.

```
npx serverless offline
```

Example local request

```
http://localhost:3000/calls/8618893815/summary
```

### Deployment

Make sure **Docker is running** because the Serverless Python requirements plugin uses Docker to build Lambda-compatible packages.

Deploy the service to AWS Lambda.

```
serverless deploy
```

This command will:

- Package the FastAPI application
- Install Python dependencies
- Deploy the Lambda function
- Configure API Gateway routes

After deployment, the API will be accessible through the generated API Gateway endpoint.

## Architecture Flow

1. Calls are stored in Supabase in the `<table_name>` table.
2. The API receives a phone number request.
3. The latest call for that phone number is retrieved.
4. The transcript is cleaned and formatted.
5. Google Gemini processes the conversation using the prompt defined in `prompts/intention-finder.md`.
6. A structured summary is generated.
7. The API returns the summary along with the user profile from MongoDB.
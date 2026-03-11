# ElevenLabs Conversation Analyzer

A FastAPI-based backend service that analyzes voice call transcripts and generates concise, structured summaries. The system retrieves conversation data from Supabase, processes transcripts using Google Gemini AI, and produces structured insights from the latest conversation. It is designed as a general-purpose conversation summarization tool that can be integrated into various applications requiring automated analysis of call transcripts.

## Purpose (For my specific usecase)

This tool extracts actionable intelligence from conversational data between recruitment agents and job seekers by:

- Parsing raw transcript data from voice calls
- Identifying the user’s intent, job role preference, and country preference
- Capturing key actions taken during the call (job selection, applications, information requests, etc.)
- Extracting follow-up instructions such as callbacks or next steps
- Converting long conversations into structured summaries that can power automated recruitment workflows
## API Endpoints

### Get Call Summary

**Endpoint:** `GET /calls/{phone}/summary`

Returns a structured summary of the most recent call for the given phone number.

**Response:**
```json
{
  "call_id": "conv_3301kjcqj0p5f1j8nrkxxxxx",
  "caller": "+9186xxxxxxxx",
  "recording_path": "conv_3301kjcqj0p5f1j8nrkxxxxx.mp3",
  "summary": "User Intent: To apply for an overseas job opportunity.\nJob Role: Shuttering Carpenter\nCountry Preference: United Arab Emirates\nAction Taken: User selected 'Shuttering Carpenter, Abu Travel Service' job; SMS link sent.\nNext Step / Request: User to apply for the job via the sent SMS link.\nCallback Time:"
}
```

### Get Full Transcript

**Endpoint:** `GET /calls/{phone}/transcript`

Returns the complete transcript of the most recent call.

**Response:**
```json
{
  "call_id": "conv_3301kjcqj0p5f1j8nrkxxxxx",
  "caller": "+9186xxxxxxxx",
  "recording_path": "conv_3301kjcqj0p5f1j8nrk9r3je066g.mp3",
  "transcript": [
    {"role": "agent", "message": "नमस्कार, मैं XXX से XXX बोल रही हूँ।"},
    {"role": "user", "message": "यस प्लीज।"}
  ]
}
```

## Summary Output Structure

The summary field follows a strict six-line format for consistent parsing:

```
User Intent: <user's primary goal>
Job Role: <job role discussed or selected>
Country Preference: <country mentioned>
Action Taken: <what occurred during the call>
Next Step / Request: <user's requested next action>
Callback Time: <specific callback datetime if requested, otherwise blank>
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SUPABASE_TABLE` | Supabase table name |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anonymous key |
| `GOOGLE_API_KEY` | Google Gemini API key |
| `GEMINI_MODEL` | Gemini model identifier (e.g., `gemini-2.5-flash`) |

## Database Schema

The application queries the `voice_calls` table in Supabase:

```sql
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
) TABLESPACE pg_default;
```

## Architecture

1. **Data Source**: Calls are stored in Supabase `voice_calls` table with fields: `call_id`, `caller`, `recording_path`, `transcript`, `created_at`
2. **Processing**: Transcript is cleaned (empty messages removed) and formatted
3. **Analysis**: Google Gemini AI generates structured summaries using the prompt defined in `prompts/intention-finder.md`
4. **Output**: REST API serves JSON responses for integration with other systems


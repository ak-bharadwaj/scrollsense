# Google Gemini AI Studio Configuration Guide

ScrollSense integrates natively with Google's **Gemini Developer API** using the **Google AI Studio Free Tier** (no Google Cloud Billing, credit cards, or Cloud Run dependencies required).

---

## 1. Quick Setup

### Step 1: Obtain a Free API Key
1. Visit [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Click **"Get API key"** and create an API key for free.

### Step 2: Set Environment Variables
In your local terminal or `.env` file:

```bash
# Set your Google AI Studio Free Tier API key
export GEMINI_API_KEY="your-api-key-here"

# (Optional) Choose the target Gemini model (default: gemini-1.5-flash)
export GEMINI_MODEL="gemini-1.5-flash"

# (Optional) Request timeout in seconds (default: 15.0)
export SCROLLSENSE_LLM_TIMEOUT="15.0"
```

On Windows PowerShell:
```powershell
$env:GEMINI_API_KEY="your-api-key-here"
$env:GEMINI_MODEL="gemini-1.5-flash"
```

---

## 2. Architecture & Execution Flow

```
+---------------------+        GEMINI_API_KEY Present?
|   Incoming Reel     | ───────────────────────────────────────────+
+---------------------+                                            |
           |                                                       |
           v                                                       v
  [YES: Production / Demo Path]                           [NO: Fallback & Test Mode]
+------------------------------------+                  +--------------------------------+
|    LLMStructuredSignalExtractor    |                  |  DeterministicSignalExtractor  |
+------------------------------------+                  +--------------------------------+
           |                                                           |
           | Calls Google AI Studio REST Endpoint                      | Strict rule-based
           | with response_schema enforcement                          | multi-feature heuristic
           v                                                           v
+------------------------------------+                  +--------------------------------+
|  Gemini 1.5 Flash Structured JSON  |                  |     Canonical ReelSignal       |
+------------------------------------+                  +--------------------------------+
           │                                                           │
           └───────────────────────────────┬───────────────────────────┘
                                           ▼
                       +---------------------------------------+
                       | PersonaInferencer & Multi-Objective   |
                       |       Recommendation Engine           |
                       +---------------------------------------+
```

---

## 3. Key Invariants & Security
- **No Hardcoded Credentials**: Keys are read strictly at runtime from `GEMINI_API_KEY` (or `GOOGLE_API_KEY`).
- **Free Tier Compatible**: Uses standard Gemini Developer endpoints (`https://generativelanguage.googleapis.com/v1beta/models/...`).
- **Zero Cloud Billing Requirement**: Does not require GCP projects or billing accounts.
- **Deterministic Offline Fallback**: In automated testing or offline environments where `GEMINI_API_KEY` is omitted, `DeterministicSignalExtractor` runs deterministically with 100% test coverage.

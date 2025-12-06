Here is the **Backend Master Prompt**. Paste this into a new chat with an AI coding assistant (like Cursor, GitHub Copilot, or ChatGPT) to start generating your backend infrastructure immediately.

---

# SpotyFire - Backend Master Prompt & Hackathon Guidelines

## 1\. Project Overview

**Name:** SpotyFire (Backend)
**Context:** 48h Hackathon - "Disaster Responses & Resilience"
**Goal:** A high-speed FastAPI backend that processes satellite imagery (Sentinel-1 SAR) to detect floods/fires, estimates financial loss, and generates valid insurance claim PDFs using AI.
**Core Functionality:**

1.  **Satellite Analysis:** Fetch "Before" vs "After" radar images to calculate damage percentage.
2.  **AI Adjuster:** An LLM agent that interprets the satellite data and drafts a legal "Notice of Loss."
3.  **Report Generation:** Create a downloadable PDF for the insurance company.

## 2\. Tech Stack (Python)

- **Framework:** `FastAPI` (for speed and auto-docs).
- **Server:** `Uvicorn`.
- **Satellite Data:**`earthengine-api`.
- **Image Processing:** `rasterio`(for calculating difference masks).
- **AI/LLM:** `google-generativeai` (Gemini-1.5-flash).
- **PDF Generation:** `fpdf2` or `reportlab`.
- **Environment:** `python-dotenv` for API keys.

## 3\. Architecture & Principles

### A. The "Demo Mode" Strategy (CRITICAL)

- **Rule:** We cannot risk the Satellite API timing out during the live pitch.
- **Implementation:** Create a global constant `DEMO_MODE = True`.
- **Logic:**
  - If `DEMO_MODE` is True: The `/analyze` endpoint ignores the specific coordinates and returns a **pre-calculated** perfect JSON response for the Galați/Vaslui flood event.
  - If `DEMO_MODE` is False: It actually tries to call the Sentinel Hub API.
- **Rule**: Do not write any comments

### B. Directory Structure

```text
backend/
├── app/
│   ├── main.py            # FastAPI entry point & CORS
│   ├── models.py          # Pydantic models (Request/Response schemas)
│   ├── services/
│   │   ├── satellite.py   # logic for fetching & diffing images
│   │   ├── ai_agent.py    # OpenAI prompt engineering
│   │   └── pdf_maker.py   # FPDF logic to generate the claim
│   └── data/
│       └── mocks.py       # The hardcoded "Perfect Demo" data
├── static/                # Store generated overlay images here
├── requirements.txt
└── .env
```

## 4\. Key Endpoints & Logic

### 1\. `POST /api/analyze`

- **Input:** `{ lat: float, lng: float, crop_type: string, value_per_ha: float }`
- **Process:**
  1.  Check `DEMO_MODE`. If True, return mock data.
  2.  If False: Fetch Sentinel-1 image (2 weeks ago) and Sentinel-1 image (yesterday).
  3.  Calculate pixel difference (change detection).
  4.  Determine `damaged_area_ha` and `financial_loss`.
- **Output:** JSON with damage stats and a URL to the "Flood Mask" image.

### 2\. `POST /api/chat`

- **Input:** `{ message: string, context: dict }`
- **Process:**
  - System Prompt: _"You are an expert Agricultural Claims Adjuster named SpotyBot. You have access to satellite forensic data showing {damage_percent}% damage. Be empathetic but professional. Help the farmer draft their claim."_
  - Use RAG (Retrieval Augmented Generation) to answer questions about the specific damage.

### 3\. `POST /api/generate-report`

- **Input:** `{ claim_id: string, user_details: dict }`
- **Process:**
  - Generate a formal PDF named `Claim_{ID}.pdf`.
  - Include: Map screenshot (placeholder), damage stats, estimated payout, time of disaster.
- **Output:** Download URL.

## 5\. Specific Service Instructions

### Satellite Service (`satellite.py`)

- Focus on **Sentinel-1 GRD** (Ground Range Detected).
- Logic: Water looks _dark_ in radar (low backscatter). If a pixel was bright (land) and is now dark (water), it is flooded.
- **Hackathon Shortcut:** If real processing is too hard, just return a static image of a red blob on a transparent background.

### AI Agent (`ai_agent.py`)

- Do not just stream text. Structure the output.
- If the user asks "How much money will I get?", the AI should calculate: `damaged_ha * value_per_ha`.

## 6\. Response Format

- **Modular Code:** Give me one file at a time.
- **Mock First:** Start by writing `app/data/mocks.py` so we have data to test immediately.
- **Pydantic Models:** Define the data structure in `app/models.py` before writing the logic.
- **FastAPI Boilerplate:** Write the `main.py` last, connecting the services.

---

**MASTER PROMPT END**

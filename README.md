# AI Productivity Hub

AI Productivity Hub is a Streamlit application that bundles several practical AI workflows into one interface:

- YouTube Summarizer
- Resume Parser
- Web Research Agent
- PDF Chat
- Study Assistant
- Meeting Notes Agent
- Email Generator
- Project Generator

## Stack

- Python
- Streamlit
- OpenAI, Gemini, or Groq
- YouTube Transcript API
- DuckDuckGo search
- PyPDF2 and pdfplumber

## Quick Start

1. Create and activate a virtual environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and add at least one API key.
4. Start the app:

```powershell
python -m streamlit run app.py
```

Using a dedicated virtual environment is recommended. Installing into a shared global Python can create dependency conflicts with unrelated tools already installed on the machine.

## Configuration

The app reads configuration from environment variables. The default provider is Groq.

- `LLM_PROVIDER`: `openai`, `gemini`, or `groq`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `SERPAPI_API_KEY` (optional, reserved for future search expansion)

If no provider is configured, the UI still loads and shows actionable guidance instead of failing.

## Project Structure

```text
app.py
src/ai_productivity_hub/
  config.py
  views.py
  services/
    ai_client.py
    document_tools.py
    research_tools.py
    youtube_tools.py
```

## Notes

- PDF chat uses lightweight retrieval over extracted text chunks.
- Resume parsing uses document extraction plus heuristic field detection and optional AI analysis.
- Web research uses DuckDuckGo results and synthesizes a structured report.

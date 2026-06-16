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

## Demo Examples

Use these samples to test each workflow in the app.

### 1. Meeting Notes Agent
- Open the **Meeting Notes Agent** page.
- Paste the transcript into the **Meeting Transcript** field.

Sample transcript:

```text
Alex: Good morning everyone. Let's start with updates on the mobile app release.

Priya: The Android version is ready for QA, but the iOS version still has two critical bugs. One is related to login sessions expiring unexpectedly, and the other affects push notifications.

Alex: How long do you think those fixes will take?

Priya: About three days for development and another two days for testing.

David: From the marketing side, we've already scheduled social media campaigns to begin on September 15. If the release slips beyond that date, we'll need to reschedule.

Sarah: Customer support also needs at least one week of training before launch. We haven't received the final feature documentation yet.

Alex: Who owns the documentation?

Priya: Engineering does. I'll work with Kevin to complete it by Friday.

Kevin: That's fine. I'll review the documentation and send it to Sarah once it's finalized.

David: We should also decide whether we're including the referral program in this release.

Alex: What's the status of that feature?

Priya: Development is complete, but analytics tracking hasn't been verified yet.

Kevin: Analytics verification can be completed by next Wednesday.

Alex: Let's postpone the referral program if analytics isn't verified by then. We don't want inaccurate tracking data.

Sarah: Agreed. It would create unnecessary support tickets.

David: One more thing. We've allocated a marketing budget of $20,000 for the launch campaign. Finance approved it yesterday.

Alex: Great. Let's keep the tentative launch date of September 20, assuming the iOS issues are resolved next week.

Priya: I'll provide a progress update on Monday.

Alex: Perfect. Any other concerns?

Sarah: None from support.

David: Nothing from marketing.

Kevin: All good.

Alex: Thanks everyone. Meeting adjourned.
```

Shorter meeting transcript:

```text
Maya: We need to finalize the onboarding flow by Friday.

Chris: The UI is almost done; I am waiting for copy from product.

Jordan: I'll sync with product after this call and send a draft by noon.

Maya: Great. Once the copy is ready, we can finish user testing and push the build.
```

### 2. YouTube Summarizer
- Open the **YouTube Summarizer** page.
- Paste a video URL into the **YouTube URL** field.

Demo URLs:

- `https://youtu.be/q0mgKXlZbc8?si=5AeP_iAqCcyiLigz`
- `https://youtu.be/dQw4w9WgXcQ`

> If a transcript is unavailable, choose another public video with captions enabled.

### 3. Resume Parser
- Open the **Resume Parser** page.
- Upload a resume PDF.
- Paste the following job description into the **Job Description** field.

```text
Data Analyst Intern

We are looking for a motivated intern with:
- Proficiency in Python, SQL, and Excel
- Experience with data visualization (Power BI or Tableau)
- Strong communication and problem-solving skills
- Ability to prepare reports and dashboards for stakeholders
```

### 4. PDF Chat
- Open the **PDF Chat** page.
- Upload any PDF file.
- Ask a question like:

```text
Explain the main conclusion of this document.
```

Or:

```text
What are the next steps listed for product rollout?
```

### 5. Email Generator
- Open the **Email Generator** page.
- Choose `Professional` as Email Type.
- Choose `Polite` as Tone.
- Use this context:

```text
Write a follow-up email to a hiring manager after an interview for a software engineering role. Mention my strong interest and request the next steps.
```

### 6. Project Generator
- Open the **Project Generator** page.
- Enter this idea:

```text
Online tutoring platform for high school STEM subjects
```

- Choose `MVP` or `Production App`.

### 7. Dashboard Quick Command
- Open the **Dashboard** page.
- Enter a quick command such as:

```text
Create meeting notes from a product team discussion
```

or:

```text
Summarize the uploaded PDF into key action items
```

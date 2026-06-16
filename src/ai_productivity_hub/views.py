from __future__ import annotations

from textwrap import dedent

import streamlit as st

from ai_productivity_hub.config import AppConfig
from ai_productivity_hub.services.ai_client import AIClient, structured_report_prompt
from ai_productivity_hub.services.document_tools import (
    JDMatchResult,
    ScoreComponent,
    best_matching_chunks,
    chunk_text,
    extract_pdf_text,
    match_resume_to_jd,
    parse_resume,
    summarize_text_stats,
)
from ai_productivity_hub.services.youtube_tools import fetch_transcript, important_timestamps, transcript_to_text


MENU_OPTIONS = [
    "Dashboard",
    "YouTube Summarizer",
    "Resume Parser",
    "PDF Chat",
    "Meeting Notes Agent",
    "Email Generator",
    "Project Generator",
]

WORKFLOW_NOTES = {
    "Dashboard": "Workspace overview",
    "YouTube Summarizer": "Transcript to summary",
    "Resume Parser": "JD match scoring",
    "PDF Chat": "Ask uploaded PDFs",
    "Meeting Notes Agent": "Decisions and tasks",
    "Email Generator": "Ready drafts",
    "Project Generator": "Plans and scope",
}

ACTION_LABELS = {
    "youtube": "Generate Video Brief",
    "resume": "Analyze Resume Fit",
    "pdf": "Ask Document AI",
    "meeting": "Extract Meeting Notes",
    "email": "Draft Email",
    "project": "Generate Build Plan",
}

NAV_ICONS = {
    "Dashboard": "Overview",
    "YouTube Summarizer": "Video",
    "Resume Parser": "Resume",
    "PDF Chat": "PDF",
    "Meeting Notes Agent": "Meeting",
    "Email Generator": "Email",
    "Project Generator": "Project",
}


def render_app(config: AppConfig) -> None:
    _inject_styles()
    _ensure_session_state()

    client = AIClient(config)
    menu = _render_sidebar(config)

    routes = {
        "Dashboard": lambda: render_dashboard(config),
        "YouTube Summarizer": lambda: render_youtube_page(client),
        "Resume Parser": lambda: render_resume_page(client),
        "PDF Chat": lambda: render_pdf_chat_page(client),
        "Meeting Notes Agent": lambda: render_meeting_notes_page(client),
        "Email Generator": lambda: render_email_page(client),
        "Project Generator": lambda: render_project_page(client),
    }
    routes[menu]()


def render_dashboard(config: AppConfig) -> None:
    _page_header("AI Productivity Hub", "A premium AI workspace for documents, videos, resumes, and drafting workflows.")
    _status_strip(config)

    metrics = st.session_state.metrics
    st.markdown("<div class='section-title'>Workspace Snapshot</div>", unsafe_allow_html=True)
    cols = st.columns(3)
    cards = [
        ("Documents", metrics["documents"], "PDF and resume files"),
        ("Videos", metrics["videos"], "Transcript summaries"),
        ("Resumes", metrics["resumes"], "Parsed profiles"),
    ]
    for col, (label, value, caption) in zip(cols, cards):
        with col:
            _metric_card(label, value, caption)

    _activity_feed()
    _popular_prompts()

    with st.form("dashboard-command-form"):
        command_cols = st.columns([5, 1])
        with command_cols[0]:
            dashboard_prompt = st.text_input(
                "Quick command",
                placeholder="e.g., Summarize a PDF, create meeting notes, or plan a student project",
                label_visibility="collapsed",
            )
        with command_cols[1]:
            command_submitted = st.form_submit_button("Route", use_container_width=True)
    if command_submitted and dashboard_prompt:
        st.info(f"Open the matching workflow from the sidebar to run: {dashboard_prompt}")

    st.markdown("<div class='section-title'>Workflow Desk</div>", unsafe_allow_html=True)
    module_cols = st.columns(2)
    modules = [
        ("YouTube Summarizer", "Extract transcript summaries, key points, action items, timestamps, and quizzes."),
        ("Resume Parser", "Match resumes against a job description with labeled scoring and skill gap analysis."),
        ("PDF Chat", "Ask targeted questions against relevant chunks from an uploaded PDF."),
        ("Meeting Notes Agent", "Turn transcripts into decisions, deadlines, and action items."),
        ("Email Generator", "Draft polished professional messages for common intents."),
        ("Project Generator", "Create requirements, architecture, feature scope, stack, and timelines."),
    ]
    for idx, (title, body) in enumerate(modules):
        module_cols[idx % 2].markdown(
            f"""
            <div class='tool-row'>
                <div>
                    <strong>{title}</strong>
                    <span>{body}</span>
                </div>
                <small>Ready</small>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_youtube_page(client: AIClient) -> None:
    _page_header("YouTube Summarizer", "Convert a transcript into a structured video brief.")

    with st.form("youtube-form"):
        url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
        submitted = st.form_submit_button(ACTION_LABELS["youtube"], use_container_width=True)

    if submitted:
        if not url.strip():
            st.error("Enter a YouTube URL.")
            return
        try:
            with st.spinner("Fetching transcript and building the summary..."):
                transcript = fetch_transcript(url)
                transcript_text = transcript_to_text(transcript)
                system_prompt, user_prompt = structured_report_prompt(
                    "Summarize the YouTube transcript into sections for Video Summary, Key Points, Action Items, Important Timestamps, Mind Map, and Quiz.",
                    transcript_text,
                )
                fallback = dedent(
                    f"""
                    ## Video Summary
                    Transcript retrieved successfully.

                    ## Key Points
                    - Transcript length: {len(transcript)} segments

                    ## Action Items
                    - Configure an API key to enable AI summarization.

                    ## Important Timestamps
                    {chr(10).join(f'- {item}' for item in important_timestamps(transcript))}
                    """
                ).strip()
                output = client.try_generate(system_prompt, user_prompt, fallback)
            st.session_state.metrics["videos"] += 1
            _result_panel(output)
        except Exception as exc:
            st.error(str(exc))


def render_resume_page(client: AIClient) -> None:
    _page_header("Resume Parser", "Match a resume against a job description with labeled scoring and gap analysis.")

    with st.form("resume-form"):
        uploaded_file = st.file_uploader("Resume PDF", type=["pdf"])
        job_description = st.text_area(
            "Job Description",
            placeholder=dedent(
                """
                Data Analyst Intern

                We are looking for a motivated intern with:
                - Proficiency in Python, SQL, and Excel
                - Experience with data visualization (Power BI or Tableau)
                - Strong communication and problem-solving skills
                """
            ).strip(),
            height=220,
        )
        submitted = st.form_submit_button(ACTION_LABELS["resume"], use_container_width=True)

    if submitted:
        if not uploaded_file:
            st.error("Upload a PDF resume first.")
            return
        if not job_description.strip():
            st.error("Paste the job description to match against.")
            return
        with st.spinner("Parsing resume and scoring against job description..."):
            text = extract_pdf_text(uploaded_file.getvalue())
            resume = parse_resume(text)
            match = match_resume_to_jd(resume, job_description)
            analysis_task = dedent(
                f"""
                Compare this resume against the following job description for '{match.jd_title}'.
                Provide:
                - Strengths (what aligns well with the JD)
                - Gaps (what is missing vs the JD)
                - Resume Improvements (actionable edits)
                - Interview Talking Points

                Job Description:
                {job_description}
                """
            ).strip()
            system_prompt, user_prompt = structured_report_prompt(analysis_task, resume.raw_text)
            fallback = _jd_analysis_fallback(match)
            analysis = client.try_generate(system_prompt, user_prompt, fallback)

        st.session_state.metrics["resumes"] += 1
        st.session_state.metrics["documents"] += 1

        match_tab, profile_tab, feedback_tab = st.tabs(["JD Match Score", "Resume Profile", "AI Feedback"])
        with match_tab:
            _render_jd_match_panel(match)
        with profile_tab:
            _render_resume_profile(resume)
        with feedback_tab:
            _result_panel(analysis)


def render_pdf_chat_page(client: AIClient) -> None:
    _page_header("PDF Chat", "Ask questions against the most relevant extracted PDF chunks.")

    with st.form("pdf-chat-form"):
        uploaded_file = st.file_uploader("PDF", type=["pdf"], key="pdf-chat")
        question = st.text_area("Question", placeholder="Explain chapter 4", height=120)
        submitted = st.form_submit_button(ACTION_LABELS["pdf"], use_container_width=True)

    if submitted:
        if not uploaded_file or not question.strip():
            st.error("Upload a PDF and enter a question.")
            return
        with st.spinner("Extracting text and matching relevant sections..."):
            text = extract_pdf_text(uploaded_file.getvalue())
            chunks = chunk_text(text)
            context = "\n\n".join(best_matching_chunks(chunks, question))
            system_prompt, user_prompt = structured_report_prompt(
                f"Answer the PDF question: {question}",
                context,
            )
            fallback = f"I found relevant sections in the PDF, but AI generation is unavailable. Matching context:\n\n{context[:1800]}"
            answer = client.try_generate(system_prompt, user_prompt, fallback)

        st.session_state.metrics["documents"] += 1
        _result_panel(answer)
        with st.expander("Document Stats"):
            st.json(summarize_text_stats(text))


def render_meeting_notes_page(client: AIClient) -> None:
    _page_header("Meeting Notes Agent", "Turn raw discussion into decisions, owners, and deadlines.")

    with st.form("meeting-form"):
        transcript = st.text_area("Meeting Transcript", height=260, placeholder="Paste transcript here")
        submitted = st.form_submit_button(ACTION_LABELS["meeting"], use_container_width=True)

    if submitted:
        if not transcript.strip():
            st.error("Paste or type a transcript.")
            return
        system_prompt, user_prompt = structured_report_prompt(
            "Convert the transcript into Summary, Decisions, Action Items, Owners, Risks, and Deadlines.",
            transcript,
        )
        fallback = dedent(
            """
            ## Summary
            Transcript captured.

            ## Decisions
            - Review manually if AI access is not configured.

            ## Action Items
            - Add provider credentials to enable structured extraction.
            """
        ).strip()
        _result_panel(client.try_generate(system_prompt, user_prompt, fallback))


def render_email_page(client: AIClient) -> None:
    _page_header("Email Generator", "Draft concise professional emails with a clear subject and close.")

    with st.form("email-form"):
        cols = st.columns(2)
        with cols[0]:
            email_type = st.selectbox(
                "Email Type",
                ["Professional", "Leave Request", "Job Application", "Cold Email", "Follow Up"],
            )
        with cols[1]:
            tone = st.selectbox("Tone", ["Polite", "Confident", "Warm", "Formal"])
        prompt = st.text_area("Context", placeholder="Write internship application email", height=150)
        submitted = st.form_submit_button(ACTION_LABELS["email"], use_container_width=True)

    if submitted:
        if not prompt.strip():
            st.error("Describe the email you want.")
            return
        system_prompt, user_prompt = structured_report_prompt(
            f"Write a ready-to-send {email_type} email in a {tone.lower()} tone.",
            prompt,
        )
        fallback = dedent(
            f"""
            Subject: {email_type} Request

            Dear Recipient,

            {prompt}

            Regards,
            Your Name
            """
        ).strip()
        _result_panel(client.try_generate(system_prompt, user_prompt, fallback))


def render_project_page(client: AIClient) -> None:
    _page_header("Project Generator", "Shape an idea into requirements, architecture, and delivery steps.")

    with st.form("project-form"):
        prompt = st.text_input("Project Idea", placeholder="Library Management System")
        scale = st.selectbox("Scale", ["Student Project", "MVP", "Production App"])
        submitted = st.form_submit_button(ACTION_LABELS["project"], use_container_width=True)

    if submitted:
        if not prompt.strip():
            st.error("Enter a project idea.")
            return
        system_prompt, user_prompt = structured_report_prompt(
            f"Generate Requirements, Database Design, Architecture, Features, Tech Stack, Risks, and Timeline for a {scale.lower()}.",
            prompt,
        )
        fallback = dedent(
            f"""
            ## Requirements
            - Define core users, workflows, and reports for {prompt}.

            ## Architecture
            - Frontend, backend, database, and deployment layers.

            ## Timeline
            - Week 1: requirements
            - Week 2: design
            - Week 3-4: implementation
            """
        ).strip()
        _result_panel(client.try_generate(system_prompt, user_prompt, fallback))


def _render_sidebar(config: AppConfig) -> str:
    st.sidebar.markdown(
        f"""
        <div class='brand-card'>
            <div class='brand-mark'>AI</div>
            <div>
                <div class='brand'>Productivity Hub</div>
                <span>Multi workflow desk</span>
            </div>
            <div class='brand-tags'>
                <small>{config.llm_provider.title()}</small>
                <small>AI Powered</small>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("<div class='side-heading'>Workspace Menu</div>", unsafe_allow_html=True)
    for item in MENU_OPTIONS:
        selected = st.session_state.selected_menu == item
        if selected:
            st.sidebar.markdown(
                f"""
                <div class='nav-item active'>
                    <span class='nav-kicker'>{NAV_ICONS[item]}</span>
                    <strong>{item}</strong>
                    <small>{WORKFLOW_NOTES[item]}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )
            continue
        label = f"{NAV_ICONS[item]}\n{item}"
        if st.sidebar.button(label, key=f"nav-{item}", use_container_width=True, type="secondary"):
            st.session_state.selected_menu = item
    st.sidebar.divider()
    _sidebar_health(config)
    st.sidebar.divider()
    _sidebar_snapshot()
    st.sidebar.divider()
    st.sidebar.markdown(
        "<div class='tip-card'><strong>Tips</strong><span>Use Ready Prompts for one-click ideas, then open the right workflow.</span></div>",
        unsafe_allow_html=True,
    )
    return st.session_state.selected_menu


def _ensure_session_state() -> None:
    if "metrics" not in st.session_state:
        st.session_state.metrics = {
            "documents": 0,
            "videos": 0,
            "resumes": 0,
        }
    if "selected_menu" not in st.session_state:
        st.session_state.selected_menu = "Dashboard"


def _page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class='page-header'>
            <div class='page-header-top'>
                <span class='page-chip'>AI Workspace</span>
                <span class='page-chip subtle'>Modern Dashboard</span>
            </div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _provider_banner(config: AppConfig) -> None:
    if config.has_active_api_key:
        st.success(f"{config.llm_provider.title()} is configured with {config.active_model}.")
    else:
        st.warning("No API key is configured for the active provider. Workflows still show fallback output where possible.")


def _status_strip(config: AppConfig) -> None:
    provider_state = "Ready" if config.has_active_api_key else "Missing key"
    provider_class = "good" if config.has_active_api_key else "warn"
    st.markdown(
        f"""
        <div class='status-strip'>
            <div><span class='{provider_class}'></span><strong>AI Status:</strong> {provider_state}</div>
            <div><strong>Provider:</strong> {config.llm_provider.title()}</div>
            <div><strong>Model:</strong> {config.active_model}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _activity_feed() -> None:
    st.markdown("<div class='section-title'>Recent Activity</div>", unsafe_allow_html=True)
    rows = [
        ("Video summaries", "Generate timestamped video briefs from YouTube transcripts.", "Live"),
        ("Document AI", "Upload PDFs and ask questions against matching sections.", "Ready"),
        ("Resume matching", "Score resumes against job descriptions with labeled skill gaps.", "Ready"),
    ]
    for title, body, label in rows:
        st.markdown(
            f"""
            <div class='feed-row'>
                <div>
                    <span>{label}</span>
                    <strong>{title}</strong>
                </div>
                <p>{body}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _popular_prompts() -> None:
    st.markdown("<div class='section-title'>Ready Prompts</div>", unsafe_allow_html=True)
    cols = st.columns(4)
    prompts = [
        "Summarize This Video",
        "Improve My Resume",
        "Draft Professional Email",
        "Plan My Project",
    ]
    for col, prompt in zip(cols, prompts):
        with col:
            st.button(prompt, use_container_width=True)


def _sidebar_health(config: AppConfig) -> None:
    api_status = "Connected" if config.has_active_api_key else "Needs API key"
    rows = [
        ("LLM Provider", f"{config.llm_provider.title()} - {api_status}"),
        ("Workspace", "Streamlit ready"),
    ]
    for title, body in rows:
        st.sidebar.markdown(
            f"<div class='side-status'><span></span><strong>{title}</strong><small>{body}</small></div>",
            unsafe_allow_html=True,
        )


def _sidebar_snapshot() -> None:
    metrics = st.session_state.metrics
    st.sidebar.markdown("<div class='side-heading'>Live Snapshot</div>", unsafe_allow_html=True)
    st.sidebar.markdown(
        f"""
        <div class='side-grid'>
            <div><small>Documents</small><strong>{metrics["documents"]}</strong></div>
            <div><small>Videos</small><strong>{metrics["videos"]}</strong></div>
            <div><small>Resumes</small><strong>{metrics["resumes"]}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _metric_card(label: str, value: int, caption: str) -> None:
    st.markdown(
        f"""
        <div class='metric-card'>
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{caption}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _tag_list(items: list[str], variant: str = "default") -> None:
    tags = "".join(f"<span class='tag tag-{variant}'>{item}</span>" for item in items)
    st.markdown(f"<div class='tag-list'>{tags}</div>", unsafe_allow_html=True)


def _render_jd_match_panel(match: JDMatchResult) -> None:
    header_cols = st.columns([1.4, 1])
    with header_cols[0]:
        st.markdown(f"#### Role: {match.jd_title}")
        _fit_badge(match.fit_label, match.overall_score)
    with header_cols[1]:
        st.metric("Overall JD Match", f"{match.overall_score}%")

    st.markdown("<div class='section-title'>Score Breakdown</div>", unsafe_allow_html=True)
    for component in match.components:
        _score_row(component)

    st.markdown("<div class='section-title'>Skills vs Job Description</div>", unsafe_allow_html=True)
    skill_cols = st.columns(2)
    with skill_cols[0]:
        st.markdown("**Matched Skills**")
        _tag_list(match.matched_skills or ["None detected"], variant="match")
    with skill_cols[1]:
        st.markdown("**Missing Skills**")
        _tag_list(match.missing_skills or ["No major gaps"], variant="gap")

    with st.expander("Requirements extracted from JD", expanded=False):
        st.markdown("**JD Requirements Detected:**")
        _tag_list(match.jd_skills or ["No specific skills detected"], variant="jd")


def _render_resume_profile(resume) -> None:
    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("#### Candidate Details")
        st.write(f"**Name:** {resume.name}")
        st.write(f"**Email:** {resume.email}")
        st.write("**Skills Found in Resume:**")
        _tag_list(resume.skills or ["No common skills detected"])
    with right:
        st.markdown("#### Resume Sections")
        with st.expander("Experience", expanded=True):
            st.write(resume.experience or ["Not detected"])
        with st.expander("Projects"):
            st.write(resume.projects or ["Not detected"])
        with st.expander("Education"):
            st.write(resume.education or ["Not detected"])


def _fit_badge(label: str, score: int) -> None:
    badge_class = "fit-strong"
    if score < 45:
        badge_class = "fit-weak"
    elif score < 65:
        badge_class = "fit-moderate"
    elif score < 80:
        badge_class = "fit-good"
    st.markdown(
        f"<div class='fit-badge {badge_class}'><strong>{label}</strong><span>{score}% match with JD</span></div>",
        unsafe_allow_html=True,
    )


def _score_row(component: ScoreComponent) -> None:
    pct = 0 if component.max_score == 0 else int((component.score / component.max_score) * 100)
    st.markdown(
        f"""
        <div class='score-row'>
            <div class='score-row-head'>
                <strong>{component.label}</strong>
                <span>{component.score}/{component.max_score}</span>
            </div>
            <div class='score-track'><div class='score-fill' style='width:{pct}%'></div></div>
            <small>{component.detail}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _jd_analysis_fallback(match: JDMatchResult) -> str:
    matched = ", ".join(match.matched_skills[:8]) or "limited overlap"
    missing = ", ".join(match.missing_skills[:8]) or "none identified"
    return dedent(
        f"""
        ## Strengths
        - Resume aligns on: {matched}
        - Overall JD match score: {match.overall_score}% ({match.fit_label})

        ## Gaps
        - Missing or weak areas: {missing}

        ## Resume Improvements
        - Highlight JD keywords naturally in experience bullets.
        - Add measurable outcomes for matched skills.
        - Mirror the job description language where truthful.

        ## Interview Talking Points
        - Prepare examples for each matched skill.
        - Address missing skills with learning plans or adjacent experience.
        """
    ).strip()


def _result_panel(markdown: str) -> None:
    st.markdown("<div class='section-title'>Generated output</div>", unsafe_allow_html=True)
    st.markdown(markdown)
    st.download_button(
        "Download Markdown",
        data=markdown,
        file_name="ai-productivity-output.md",
        mime="text/markdown",
        use_container_width=True,
    )


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
            :root {
                --bg: #07111f;
                --bg-soft: #0d1a2d;
                --panel: rgba(12, 25, 44, 0.74);
                --panel-strong: rgba(15, 30, 52, 0.92);
                --panel-light: rgba(255, 255, 255, 0.07);
                --line: rgba(148, 163, 184, 0.18);
                --line-strong: rgba(125, 211, 252, 0.24);
                --text: #edf5ff;
                --muted: #98a9c4;
                --blue: #4da2ff;
                --blue-dark: #2878ff;
                --cyan: #6ee7f9;
                --mint: #7ef0c3;
                --amber: #f8cf74;
                --danger: #ff7d7d;
                --shadow: 0 28px 70px rgba(2, 8, 23, 0.42);
            }

            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(77, 162, 255, 0.18), transparent 26%),
                    radial-gradient(circle at top right, rgba(126, 240, 195, 0.12), transparent 24%),
                    radial-gradient(circle at bottom left, rgba(248, 207, 116, 0.12), transparent 22%),
                    linear-gradient(180deg, #050d18 0%, #081220 40%, #0b1627 100%);
                color: var(--text);
            }

            .block-container {
                background: linear-gradient(180deg, rgba(5, 13, 24, 0.18), rgba(5, 13, 24, 0.08));
                max-width: 1180px;
                min-height: calc(100vh - 2rem);
                padding: 4.4rem 2.6rem 3.6rem;
            }

            h1 {
                color: var(--text);
                font-size: clamp(1.6rem, 2.7vw, 2.9rem);
                font-weight: 850;
                letter-spacing: -0.03em;
                line-height: 1.1;
                margin: 0.25rem 0 0.75rem;
            }

            h3, h4 {
                color: var(--text);
                letter-spacing: -0.01em;
            }

            p, label, .stMarkdown, .stText, .stCaption {
                color: var(--muted);
            }

            .page-header {
                background:
                    radial-gradient(circle at top right, rgba(110, 231, 249, 0.15), transparent 22%),
                    radial-gradient(circle at bottom left, rgba(248, 207, 116, 0.16), transparent 28%),
                    linear-gradient(135deg, rgba(11, 24, 41, 0.96), rgba(17, 32, 54, 0.9));
                border: 1px solid var(--line-strong);
                border-radius: 24px;
                backdrop-filter: blur(22px);
                box-shadow: var(--shadow);
                margin-bottom: 1.2rem;
                overflow: hidden;
                padding: 1.2rem 1.25rem 1.15rem;
                position: relative;
            }

            .page-header::after {
                background: linear-gradient(90deg, rgba(110, 231, 249, 0.55), rgba(77, 162, 255, 0.02));
                content: "";
                height: 1px;
                left: 1.25rem;
                position: absolute;
                right: 1.25rem;
                top: 3.35rem;
            }

            .page-header-top {
                display: flex;
                gap: 0.55rem;
                margin-bottom: 1rem;
                position: relative;
                z-index: 1;
            }

            .page-chip {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(110, 231, 249, 0.2);
                border-radius: 999px;
                color: var(--text);
                display: inline-flex;
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.08em;
                padding: 0.42rem 0.72rem;
                text-transform: uppercase;
            }

            .page-chip.subtle {
                border-color: rgba(248, 207, 116, 0.18);
                color: #cdd8ea;
            }

            .page-header p {
                color: var(--muted);
                font-size: 0.98rem;
                line-height: 1.7;
                margin: 0;
                max-width: 52rem;
                text-align: left;
            }

            .section-title {
                color: var(--text);
                font-size: 1.02rem;
                font-weight: 850;
                letter-spacing: 0.01em;
                margin: 1.4rem 0 0.8rem;
            }

            .status-strip {
                align-items: center;
                background: linear-gradient(180deg, rgba(14, 28, 48, 0.92), rgba(11, 21, 37, 0.9));
                border: 1px solid var(--line);
                border-radius: 18px;
                box-shadow: 0 18px 40px rgba(2, 8, 23, 0.28);
                display: flex;
                flex-wrap: wrap;
                gap: 1.2rem;
                justify-content: space-between;
                margin: 0.15rem 0 1.2rem;
                padding: 0.95rem 1.05rem;
            }

            .status-strip div {
                color: #d9e7ff;
                font-size: 0.84rem;
            }

            .status-strip span.good,
            .status-strip span.warn {
                border-radius: 999px;
                display: inline-block;
                height: 0.55rem;
                margin-right: 0.45rem;
                width: 0.55rem;
            }

            .status-strip span.good {
                background: var(--mint);
                box-shadow: 0 0 0 6px rgba(126, 240, 195, 0.12);
            }

            .status-strip span.warn {
                background: var(--danger);
                box-shadow: 0 0 0 6px rgba(255, 125, 125, 0.1);
            }

            .brand-card {
                background:
                    radial-gradient(circle at top right, rgba(110, 231, 249, 0.16), transparent 22%),
                    linear-gradient(145deg, #081322 0%, #10233d 58%, #17396c 140%);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 22px;
                box-shadow: 0 20px 48px rgba(2, 8, 23, 0.34);
                display: grid;
                gap: 0.6rem;
                margin: 0.7rem 0 1.2rem;
                padding: 1.1rem;
            }

            .brand-mark {
                align-items: center;
                background: linear-gradient(135deg, #6ee7f9, #4da2ff);
                border-radius: 14px;
                color: #02111f;
                display: flex;
                font-size: 0.9rem;
                font-weight: 900;
                height: 2.7rem;
                justify-content: center;
                width: 2.7rem;
            }

            .brand {
                color: #ffffff;
                font-size: 1.08rem;
                font-weight: 900;
                line-height: 1.1;
                padding: 0;
            }

            .brand-card span {
                color: rgba(255, 255, 255, 0.78);
                font-size: 0.74rem;
                font-weight: 650;
            }

            .brand-tags {
                display: flex;
                gap: 0.45rem;
                margin-top: 0.2rem;
            }

            .brand-tags small {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 999px;
                color: #ffffff;
                font-size: 0.68rem;
                font-weight: 800;
                padding: 0.3rem 0.58rem;
            }

            .metric-card,
            .tool-row,
            .status-row,
            .feed-row {
                background: linear-gradient(180deg, rgba(14, 27, 47, 0.92) 0%, rgba(10, 20, 35, 0.92) 100%);
                border: 1px solid var(--line);
                border-radius: 20px;
                box-shadow: 0 18px 42px rgba(2, 8, 23, 0.22);
            }

            .metric-card {
                min-height: 110px;
                padding: 1rem 1.05rem;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
            }

            .metric-card span,
            .metric-card small,
            .tool-row span,
            .status-row span {
                color: var(--muted);
            }

            .metric-card span,
            .tool-row strong,
            .feed-row div strong {
                color: var(--text);
            }

            .metric-card strong {
                color: #ffffff;
                display: block;
                font-size: 1.75rem;
                font-weight: 900;
                line-height: 1;
            }

            .feed-row {
                align-items: center;
                display: flex;
                gap: 1rem;
                justify-content: space-between;
                margin-bottom: 0.55rem;
                min-height: 4.4rem;
                padding: 0.95rem 1rem;
            }

            .feed-row div {
                display: grid;
                gap: 0.35rem;
            }

            .feed-row div span {
                background: rgba(77, 162, 255, 0.12);
                border: 1px solid rgba(77, 162, 255, 0.22);
                border-radius: 999px;
                color: #b7d7ff;
                font-size: 0.68rem;
                font-weight: 850;
                padding: 0.26rem 0.58rem;
                width: fit-content;
            }

            .feed-row div strong {
                color: var(--text);
                font-size: 0.94rem;
            }

            .feed-row p {
                color: var(--muted);
                font-size: 0.83rem;
                margin: 0;
                text-align: right;
            }

            .tool-row {
                align-items: center;
                display: flex;
                gap: 0.8rem;
                justify-content: space-between;
                margin-bottom: 0.75rem;
                padding: 1rem 1.05rem;
                transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
            }

            .tool-row:hover {
                border-color: rgba(110, 231, 249, 0.34);
                box-shadow: 0 18px 34px rgba(77, 162, 255, 0.12);
                transform: translateY(-2px);
            }

            .tool-row div {
                display: grid;
                gap: 0.25rem;
            }

            .tool-row small {
                background: rgba(126, 240, 195, 0.12);
                border: 1px solid rgba(126, 240, 195, 0.2);
                border-radius: 999px;
                color: #beffe4;
                flex: 0 0 auto;
                font-size: 0.74rem;
                font-weight: 800;
                padding: 0.3rem 0.62rem;
            }

            .status-row {
                align-items: center;
                display: flex;
                justify-content: space-between;
                margin-bottom: 0.6rem;
                padding: 0.9rem 1rem;
            }

            .tag-list {
                display: flex;
                flex-wrap: wrap;
                gap: 0.4rem;
                margin: 0.45rem 0 0.7rem;
            }

            .tag {
                background: rgba(77, 162, 255, 0.12);
                border: 1px solid rgba(77, 162, 255, 0.24);
                border-radius: 999px;
                color: #d7e8ff;
                display: inline-block;
                font-size: 0.82rem;
                font-weight: 750;
                padding: 0.32rem 0.68rem;
            }

            .tag-match {
                background: rgba(126, 240, 195, 0.12);
                border-color: rgba(126, 240, 195, 0.28);
                color: #beffe4;
            }

            .tag-gap {
                background: rgba(255, 125, 125, 0.12);
                border-color: rgba(255, 125, 125, 0.28);
                color: #ffd0d0;
            }

            .tag-jd {
                background: rgba(248, 207, 116, 0.12);
                border-color: rgba(248, 207, 116, 0.28);
                color: #ffe7b0;
            }

            .fit-badge {
                border-radius: 16px;
                display: grid;
                gap: 0.2rem;
                margin-top: 0.35rem;
                padding: 0.75rem 0.9rem;
            }

            .fit-badge strong {
                color: #ffffff;
                font-size: 0.95rem;
            }

            .fit-badge span {
                color: var(--muted);
                font-size: 0.8rem;
            }

            .fit-strong {
                background: rgba(126, 240, 195, 0.12);
                border: 1px solid rgba(126, 240, 195, 0.24);
            }

            .fit-good {
                background: rgba(77, 162, 255, 0.12);
                border: 1px solid rgba(77, 162, 255, 0.24);
            }

            .fit-moderate {
                background: rgba(248, 207, 116, 0.12);
                border: 1px solid rgba(248, 207, 116, 0.24);
            }

            .fit-weak {
                background: rgba(255, 125, 125, 0.12);
                border: 1px solid rgba(255, 125, 125, 0.24);
            }

            .score-row {
                background: linear-gradient(180deg, rgba(14, 27, 47, 0.92), rgba(10, 20, 35, 0.92));
                border: 1px solid var(--line);
                border-radius: 16px;
                display: grid;
                gap: 0.45rem;
                margin-bottom: 0.65rem;
                padding: 0.85rem 0.95rem;
            }

            .score-row-head {
                align-items: center;
                display: flex;
                justify-content: space-between;
            }

            .score-row-head strong {
                color: var(--text);
                font-size: 0.9rem;
            }

            .score-row-head span {
                color: #ffffff;
                font-size: 0.86rem;
                font-weight: 800;
            }

            .score-track {
                background: rgba(255, 255, 255, 0.06);
                border-radius: 999px;
                height: 0.55rem;
                overflow: hidden;
            }

            .score-fill {
                background: linear-gradient(90deg, #2878ff, #6ee7f9);
                border-radius: 999px;
                height: 100%;
            }

            .score-row small {
                color: var(--muted);
                font-size: 0.78rem;
            }

            div[data-testid='stSidebar'] {
                background:
                    radial-gradient(circle at top, rgba(77, 162, 255, 0.18), transparent 22%),
                    linear-gradient(180deg, #07111f 0%, #0a1628 100%);
                border-right: 1px solid rgba(148, 163, 184, 0.12);
            }

            div[data-testid='stSidebar'] .stButton {
                margin-bottom: 0.32rem;
            }

            div[data-testid='stSidebar'] .stButton > button {
                align-items: flex-start;
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(148, 163, 184, 0.14);
                border-radius: 18px;
                box-shadow: none;
                color: var(--text);
                display: flex;
                font-size: 0.92rem;
                font-weight: 700;
                justify-content: flex-start;
                line-height: 1.2;
                min-height: 4.2rem;
                padding: 0.78rem 0.9rem;
                text-align: left;
                white-space: pre-line;
            }

            div[data-testid='stSidebar'] .stButton > button p {
                color: var(--text) !important;
                font-size: 0.9rem;
                line-height: 1.35;
                margin: 0;
            }

            div[data-testid='stSidebar'] .stButton > button:hover {
                background: rgba(255, 255, 255, 0.07);
                border-color: rgba(110, 231, 249, 0.26);
                box-shadow: 0 10px 24px rgba(2, 8, 23, 0.18);
            }

            div[data-testid='stSidebar'] .stButton > button:focus {
                border-color: rgba(110, 231, 249, 0.3);
                box-shadow: 0 0 0 1px rgba(110, 231, 249, 0.2);
            }

            .nav-item.active {
                background: linear-gradient(135deg, rgba(77, 162, 255, 0.2), rgba(110, 231, 249, 0.1));
                border: 1px solid rgba(110, 231, 249, 0.24);
                border-radius: 18px;
                box-shadow: 0 18px 30px rgba(77, 162, 255, 0.14);
                display: grid;
                gap: 0.2rem;
                margin: 0 0 0.5rem;
                padding: 0.8rem 0.9rem;
            }

            .nav-item.active strong {
                color: #ffffff;
                font-size: 0.94rem;
            }

            .nav-item.active small {
                color: #d1def5;
                font-size: 0.76rem;
            }

            .nav-kicker {
                color: var(--cyan);
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }

            div[data-testid='stHeader'] {
                background: rgba(7, 17, 31, 0.58);
                backdrop-filter: blur(12px);
            }

            div[data-testid='stToolbar'] {
                color: var(--text);
            }

            div.stButton > button,
            div[data-testid='stDownloadButton'] > button,
            div[data-testid='stFormSubmitButton'] > button {
                background: linear-gradient(135deg, #1d4ed8, #0891b2);
                border: 0;
                border-radius: 14px;
                box-shadow: 0 14px 28px rgba(77, 162, 255, 0.22);
                color: #ffffff !important;
                font-weight: 800;
                min-height: 2.65rem;
                transition: box-shadow 160ms ease, transform 160ms ease;
            }

            div.stButton > button p,
            div.stButton > button span,
            div[data-testid='stDownloadButton'] > button p,
            div[data-testid='stDownloadButton'] > button span,
            div[data-testid='stFormSubmitButton'] > button p,
            div[data-testid='stFormSubmitButton'] > button span {
                color: #ffffff !important;
                opacity: 1 !important;
            }

            div.stButton > button:hover,
            div[data-testid='stDownloadButton'] > button:hover,
            div[data-testid='stFormSubmitButton'] > button:hover {
                background: linear-gradient(135deg, #1e40af, #0f766e);
                box-shadow: 0 16px 34px rgba(77, 162, 255, 0.32);
                color: #ffffff !important;
                transform: translateY(-2px);
            }

            div[data-testid='stFileUploader'],
            div[data-testid='stTextArea'],
            div[data-testid='stTextInput'],
            div[data-testid='stSelectbox'],
            div[data-testid='stSlider'] {
                border-radius: 16px;
            }

            input,
            textarea {
                border-radius: 14px !important;
                color: var(--text) !important;
            }

            div[data-testid='stForm'] {
                background: linear-gradient(180deg, rgba(12, 25, 44, 0.9), rgba(10, 20, 35, 0.94));
                border: 1px solid var(--line);
                border-radius: 22px;
                box-shadow: 0 24px 54px rgba(2, 8, 23, 0.28);
                padding: 1.05rem;
            }

            div[data-testid='stForm'] [data-baseweb='input'],
            div[data-testid='stForm'] [data-baseweb='select'],
            div[data-testid='stForm'] textarea,
            div[data-testid='stFileUploaderDropzone'] {
                background: rgba(255, 255, 255, 0.04) !important;
                border: 1px solid rgba(148, 163, 184, 0.14) !important;
            }

            div[data-testid='stExpander'] {
                background: rgba(12, 25, 44, 0.78);
                border: 1px solid var(--line);
                border-radius: 16px;
                overflow: hidden;
            }

            div[data-testid='stMetric'] {
                background: linear-gradient(180deg, rgba(14, 27, 47, 0.92), rgba(10, 20, 35, 0.92));
                border: 1px solid var(--line);
                border-radius: 20px;
                padding: 0.85rem;
            }

            div[data-testid='stMetric'] label,
            div[data-testid='stMetric'] [data-testid='stMetricValue'] {
                color: var(--text) !important;
            }

            .side-status,
            .tip-card,
            .side-grid {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(148, 163, 184, 0.14);
                border-radius: 16px;
            }

            .side-status {
                display: grid;
                gap: 0.15rem;
                margin-bottom: 0.55rem;
                padding: 0.75rem 0.8rem;
            }

            .side-status strong,
            .side-heading,
            .tip-card strong {
                color: var(--text);
            }

            .side-status small,
            .tip-card span,
            .side-grid small {
                color: var(--muted);
            }

            .side-status span {
                background: linear-gradient(135deg, var(--cyan), var(--blue));
                border-radius: 999px;
                display: inline-block;
                height: 0.5rem;
                width: 0.5rem;
            }

            .side-heading {
                font-size: 0.8rem;
                font-weight: 800;
                letter-spacing: 0.06em;
                margin: 0.2rem 0 0.55rem;
                text-transform: uppercase;
            }

            .side-grid {
                display: grid;
                gap: 0.55rem;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                padding: 0.8rem;
            }

            .side-grid strong {
                color: #ffffff;
                display: block;
                font-size: 1.15rem;
                margin-top: 0.15rem;
            }

            .tip-card {
                display: grid;
                gap: 0.3rem;
                padding: 0.8rem;
            }

            .stTabs [data-baseweb='tab-list'] {
                gap: 0.45rem;
            }

            .stTabs [data-baseweb='tab'] {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(148, 163, 184, 0.14);
                border-radius: 999px;
                color: var(--muted);
                padding: 0.5rem 0.9rem;
            }

            .stTabs [aria-selected='true'] {
                background: rgba(77, 162, 255, 0.14) !important;
                border-color: rgba(77, 162, 255, 0.28) !important;
                color: var(--text) !important;
            }

            @media (max-width: 900px) {
                .block-container {
                    padding: 4rem 1rem 2.6rem;
                }

                .status-strip,
                .feed-row,
                .tool-row {
                    display: grid;
                }

                .page-header::after {
                    top: 4.2rem;
                }

            .side-status {
                background: var(--mint);
                border: 1px solid var(--mint-line);
                border-radius: 10px;
                display: grid;
                gap: 0.25rem;
                margin-bottom: 0.55rem;
                padding: 0.75rem;
            }

            .side-status span {
                background: #19c37d;
                border-radius: 999px;
                height: 0.45rem;
                width: 0.45rem;
            }

            .side-status strong {
                color: var(--ink);
                font-size: 0.76rem;
            }

            .side-status small {
                color: var(--muted);
                font-size: 0.72rem;
            }

            .side-heading {
                color: var(--ink);
                font-size: 0.78rem;
                font-weight: 900;
                margin: 0 0 0.55rem;
            }

            .side-grid {
                display: grid;
                gap: 0.45rem;
                grid-template-columns: 1fr 1fr;
            }

            .side-grid div {
                background: #eaf2ff;
                border: 1px solid #bad0ff;
                border-radius: 10px;
                display: grid;
                gap: 0.25rem;
                min-height: 3.45rem;
                padding: 0.55rem;
            }

            .side-grid div:nth-child(3) {
                background: #e9fff3;
                border-color: #b8ead4;
            }

            .side-grid div:nth-child(4) {
                background: #f1edff;
                border-color: #d2c7ff;
            }

            .side-grid small {
                color: #3d4b63;
                font-size: 0.64rem;
                font-weight: 900;
                text-transform: uppercase;
            }

            .side-grid strong {
                color: #24324c;
                font-size: 1.15rem;
                font-weight: 900;
            }

            .tip-card {
                background: var(--amber);
                border: 1px solid #f3d36c;
                border-radius: 10px;
                display: grid;
                gap: 0.35rem;
                padding: 0.75rem;
            }

            .tip-card strong {
                color: var(--ink);
                font-size: 0.78rem;
            }

            .tip-card span {
                color: #5f4b13;
                font-size: 0.72rem;
                line-height: 1.45;
            }

            .stTabs [data-baseweb='tab-list'] {
                gap: 0.4rem;
            }

            .stTabs [data-baseweb='tab'] {
                border-radius: 8px;
            }

            @media (max-width: 900px) {
                .block-container {
                    padding: 1rem 1rem 5rem;
                }

                .status-strip,
                .feed-row {
                    align-items: flex-start;
                    flex-direction: column;
                }

                .feed-row p {
                    text-align: left;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

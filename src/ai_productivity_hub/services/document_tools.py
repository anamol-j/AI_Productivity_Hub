from __future__ import annotations

import io
import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

import pdfplumber
from PyPDF2 import PdfReader


@dataclass
class ResumeData:
    name: str
    email: str
    skills: list[str]
    experience: list[str]
    projects: list[str]
    education: list[str]
    raw_text: str


@dataclass
class ScoreComponent:
    label: str
    score: int
    max_score: int
    detail: str


@dataclass
class JDMatchResult:
    overall_score: int
    fit_label: str
    jd_title: str
    jd_skills: list[str]
    matched_skills: list[str]
    missing_skills: list[str]
    components: list[ScoreComponent]


COMMON_SKILLS = {
    "python",
    "sql",
    "streamlit",
    "machine learning",
    "docker",
    "aws",
    "azure",
    "git",
    "pandas",
    "numpy",
    "power bi",
    "tableau",
    "tensorflow",
    "pytorch",
    "langchain",
    "faiss",
    "chromadb",
    "fastapi",
    "flask",
    "django",
    "javascript",
    "react",
    "excel",
    "r",
    "statistics",
    "data analysis",
    "data visualization",
    "etl",
    "spark",
    "hadoop",
    "kubernetes",
    "mongodb",
    "postgresql",
    "mysql",
    "scikit-learn",
    "nlp",
    "deep learning",
    "api",
    "rest",
    "agile",
    "scrum",
    "jira",
    "communication",
    "problem solving",
    "leadership",
    "teamwork",
}

JD_SKILL_PATTERNS = [
    re.compile(r"(?:proficien(?:t|cy)|experience|knowledge|skills?)\s+(?:in|with|of)\s+([a-z0-9+#./\s,&-]{2,40})", re.I),
    re.compile(r"(?:required|must have|nice to have|preferred)[:\s]+([a-z0-9+#./\s,&-]{2,60})", re.I),
]


def extract_pdf_text(file_bytes: bytes) -> str:
    text_parts: list[str] = []
    reader = PdfReader(io.BytesIO(file_bytes))
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            text_parts.append(page_text)

    if text_parts:
        return "\n".join(text_parts)

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)
    return "\n".join(text_parts)


def chunk_text(text: str, chunk_size: int = 1400, overlap: int = 200) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        chunks.append(cleaned[start:end])
        if end == len(cleaned):
            break
        start = max(end - overlap, 0)
    return chunks


def best_matching_chunks(chunks: Iterable[str], query: str, limit: int = 4) -> list[str]:
    query_terms = re.findall(r"[a-zA-Z0-9]+", query.lower())
    if not query_terms:
        return list(chunks)[:limit]

    scored: list[tuple[int, str]] = []
    for chunk in chunks:
        lower_chunk = chunk.lower()
        score = sum(lower_chunk.count(term) for term in query_terms)
        scored.append((score, chunk))
    ranked = sorted(scored, key=lambda item: item[0], reverse=True)
    return [chunk for score, chunk in ranked[:limit] if score > 0] or [chunk for _, chunk in ranked[:limit]]


def parse_resume(text: str) -> ResumeData:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    name = lines[0] if lines else "Not found"
    email = email_match.group(0) if email_match else "Not found"

    lowered_text = text.lower()
    skills = sorted(skill.title() for skill in COMMON_SKILLS if skill in lowered_text)

    experience = _section_lines(lines, ["experience", "work experience", "employment"])
    projects = _section_lines(lines, ["projects", "project"])
    education = _section_lines(lines, ["education", "academics", "qualification"])

    return ResumeData(
        name=name,
        email=email,
        skills=skills[:15],
        experience=experience,
        projects=projects,
        education=education,
        raw_text=text,
    )


def extract_jd_title(job_description: str) -> str:
    lines = [line.strip() for line in job_description.splitlines() if line.strip()]
    if not lines:
        return "Job Role"

    title_match = re.search(
        r"(?:job\s*title|position|role)\s*[:\-]\s*(.+)",
        job_description,
        re.I,
    )
    if title_match:
        return title_match.group(1).strip()[:80]

    first_line = lines[0]
    if len(first_line) <= 80 and not first_line.endswith("."):
        return first_line
    return "Job Role"


def _normalize_jd_skill(skill: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", skill.strip(" .;:-")).lower()
    if len(cleaned) < 2 or len(cleaned) > 40:
        return None
    if any(token in cleaned for token in ("experience", "knowledge", "ability", "years", "required")):
        return None
    if cleaned in COMMON_SKILLS:
        return cleaned
    for known in sorted(COMMON_SKILLS, key=len, reverse=True):
        if known in cleaned:
            return known
    return None


def extract_jd_requirements(job_description: str) -> list[str]:
    lowered = job_description.lower()
    found: set[str] = {skill for skill in COMMON_SKILLS if skill in lowered}

    for pattern in JD_SKILL_PATTERNS:
        for match in pattern.findall(job_description):
            for fragment in re.split(r"[,/&]| and | or ", match):
                normalized = _normalize_jd_skill(fragment)
                if normalized:
                    found.add(normalized)

    bullet_terms = re.findall(r"[-•*]\s+([^\n]{3,80})", job_description)
    for term in bullet_terms:
        lowered_term = term.lower()
        for skill in sorted(COMMON_SKILLS, key=len, reverse=True):
            if skill in lowered_term:
                found.add(skill)

    found.discard("r")
    if re.search(r"\b(?:language\s+)?r\b|\br\s+programming\b", lowered):
        found.add("r")

    return sorted(found, key=len, reverse=True)[:25]


def _text_contains_skill(text: str, skill: str) -> bool:
    pattern = re.escape(skill.lower()).replace(r"\ ", r"\s+")
    return bool(re.search(rf"\b{pattern}\b", text.lower()))


def _keyword_overlap(source: str, reference: str) -> float:
    source_terms = set(re.findall(r"[a-z0-9]{3,}", source.lower()))
    reference_terms = set(re.findall(r"[a-z0-9]{3,}", reference.lower()))
    if not reference_terms:
        return 0.0
    return len(source_terms & reference_terms) / len(reference_terms)


def _fit_label(score: int) -> str:
    if score >= 80:
        return "Strong Match"
    if score >= 65:
        return "Good Match"
    if score >= 45:
        return "Moderate Match"
    if score >= 25:
        return "Weak Match"
    return "Poor Match"


def match_resume_to_jd(resume: ResumeData, job_description: str) -> JDMatchResult:
    jd_title = extract_jd_title(job_description)
    jd_skills = extract_jd_requirements(job_description)
    if not jd_skills:
        jd_skills = extract_jd_requirements(
            "python sql excel data analysis statistics machine learning communication problem solving"
        )

    resume_text = resume.raw_text.lower()
    matched = [skill.title() for skill in jd_skills if _text_contains_skill(resume_text, skill)]
    missing = [skill.title() for skill in jd_skills if skill not in {item.lower() for item in matched}]

    skill_ratio = len(matched) / len(jd_skills) if jd_skills else 0
    skill_score = round(skill_ratio * 50)

    experience_text = " ".join(resume.experience).lower()
    experience_score = round(min(_keyword_overlap(experience_text, job_description) * 25, 25))

    profile_points = [
        resume.name != "Not found",
        resume.email != "Not found",
        bool(resume.education),
    ]
    profile_score = round(sum(profile_points) / len(profile_points) * 15)

    section_points = [
        bool(resume.experience),
        bool(resume.projects),
        bool(resume.education),
    ]
    section_score = round(sum(section_points) / len(section_points) * 10)

    components = [
        ScoreComponent(
            label="Skills Match",
            score=skill_score,
            max_score=50,
            detail=f"{len(matched)} of {len(jd_skills)} required skills found in resume",
        ),
        ScoreComponent(
            label="Experience Alignment",
            score=experience_score,
            max_score=25,
            detail="Keyword overlap between experience and job description",
        ),
        ScoreComponent(
            label="Profile Completeness",
            score=profile_score,
            max_score=15,
            detail="Name, contact, and education presence",
        ),
        ScoreComponent(
            label="Section Coverage",
            score=section_score,
            max_score=10,
            detail="Experience, projects, and education sections detected",
        ),
    ]
    overall_score = min(sum(component.score for component in components), 100)

    return JDMatchResult(
        overall_score=overall_score,
        fit_label=_fit_label(overall_score),
        jd_title=jd_title,
        jd_skills=[skill.title() for skill in jd_skills],
        matched_skills=matched,
        missing_skills=missing,
        components=components,
    )


def estimate_ats_score(resume: ResumeData, target_skills: list[str] | None = None) -> tuple[int, list[str]]:
    target_skills = target_skills or ["python", "sql", "docker", "aws", "git", "machine learning"]
    resume_text = resume.raw_text.lower()
    missing = [skill.title() for skill in target_skills if not _text_contains_skill(resume_text, skill)]
    matched_count = len(target_skills) - len(missing)

    components = [
        20 if resume.name != "Not found" else 0,
        15 if resume.email != "Not found" else 0,
        round(min(matched_count / max(len(target_skills), 1) * 30, 30)),
        20 if resume.experience else 0,
        15 if resume.projects else 0,
    ]
    score = min(sum(components), 100)
    return score, missing


def summarize_text_stats(text: str) -> dict[str, int]:
    words = re.findall(r"\w+", text.lower())
    common = Counter(words).most_common(10)
    return {
        "characters": len(text),
        "words": len(words),
        "unique_words": len(set(words)),
        "top_terms_count": len(common),
    }


def _section_lines(lines: list[str], section_names: list[str]) -> list[str]:
    normalized_headers = {name.lower() for name in section_names}
    collected: list[str] = []
    capture = False
    for line in lines:
        normalized = line.lower().strip(":")
        if normalized in normalized_headers:
            capture = True
            continue
        if capture and len(line.split()) <= 4 and line.lower() not in normalized_headers and line.isalpha():
            break
        if capture:
            collected.append(line)
            if len(collected) >= 6:
                break
    return collected

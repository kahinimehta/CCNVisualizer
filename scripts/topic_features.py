"""Shared text prep for UMAP embeddings and research-theme scoring."""

from __future__ import annotations

import re

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

# Conference area labels and method/format tags — not topical content.
METADATA_KEYWORD_PHRASES = frozenset(
    {
        "psychological / behavioral research",
        "computational cognitive science / cognitive modeling",
        "theoretical / computational neuroscience",
        "experimental neuroscience (systems / cognitive)",
        "artificial intelligence / machine learning",
        "methods & computational tools",
        "brain networks & neural dynamics",
        "visual processing & computational vision",
        "object recognition & visual attention",
        "reward, value & social decision making",
        "memory, spatial cognition & skill learning",
        "predictive processing & cognitive control",
        "language & communication",
        "extended abstract",
        "extended abstracts",
        "cognitive science",
        "neuroscience",
        "psychology",
        "engineering",
        "mathematics",
        "philosophy",
        "artificial intelligence",
        "linguistics",
    }
)

METADATA_KEYWORD_TOKENS = frozenset(
    {
        "fmri",
        "eeg",
        "meg",
        "ecog",
        "bold",
        "neuroimaging",
        "psychological",
        "behavioral",
        "computational",
        "modeling",
        "experimental",
        "systems",
        "cognitive",
        "abstract",
        "poster",
        "paper",
        "proceedings",
    }
)

GENERIC_KEYWORD_LABELS = frozenset({"cognitive science", "cognitive"})

CITATION_FRAGMENT_RES = (
    re.compile(r"\bet\s+al\.?", re.I),
    re.compile(r"\bp\.?\s*\d+(?:\s*[-–—]\s*\d+)?", re.I),
    re.compile(r"\bpp\.?\s*\d+", re.I),
    re.compile(r"\bdoi\s*[:.]?\s*\S+", re.I),
    re.compile(r"https?://\S+", re.I),
    re.compile(r"\bvol\.?\s*\d+", re.I),
    re.compile(r"\bno\.?\s*\d+", re.I),
    re.compile(r"\(\s*\d{4}[a-z]?\s*\)", re.I),
)

# Topic prototype anchors — used for TF-IDF cosine scoring.
TOPIC_ANCHORS: dict[str, list[str]] = {
    "RL, motor control & planning": [
        "reinforcement learning",
        "reward",
        "motor control",
        "planning",
        "policy",
        "navigation",
        "action selection",
        "skill learning",
        "habit",
        "basal ganglia",
    ],
    "Naturalistic encoding/decoding": [
        "naturalistic",
        "encoding model",
        "decoding",
        "voxel-wise",
        "stimulus reconstruction",
        "movie",
        "narrative",
        "resting state",
        "natural scenes",
        "video",
    ],
    "Neural population geometry & dynamics": [
        "neural population",
        "population dynamics",
        "geometry",
        "manifold",
        "latent dynamics",
        "trajectory",
        "oscillation",
        "connectivity",
        "state space",
    ],
    "Decision-making and metacognition": [
        "decision making",
        "decision-making",
        "metacognition",
        "confidence",
        "choice",
        "judgment",
        "belief updating",
        "inference",
        "evidence accumulation",
    ],
    "Vision": [
        "visual",
        "vision",
        "retina",
        "v1",
        "v2",
        "retinotopic",
        "scene perception",
        "optic flow",
        "gaze",
        "saccade",
        "conscious vision",
        "visual awareness",
        "perceptual",
    ],
    "Language/auditory neuroscience": [
        "language",
        "auditory",
        "speech",
        "semantic",
        "syntax",
        "word",
        "listening",
        "voice",
        "reading",
        "phonology",
    ],
    "LLMs, reasoning, interpretability": [
        "large language model",
        "language model",
        "llm",
        "transformer",
        "gpt",
        "chatgpt",
        "prompt",
        "prompting",
        "in-context learning",
        "rlhf",
        "chain-of-thought",
        "chain of thought",
        "foundation model",
        "instruction tuning",
        "fine-tuning",
        "generative model",
        "pretrained",
    ],
    "Memory": [
        "memory",
        "hippocampus",
        "recall",
        "working memory",
        "episodic",
        "retrieval",
        "spatial memory",
        "consolidation",
    ],
    "Social cognition & theory of mind": [
        "social cognition",
        "theory of mind",
        "mentalizing",
        "social interaction",
        "empathy",
        "tom",
        "agent",
        "cooperation",
        "mental state",
    ],
    "Attention & cognitive control / executive function": [
        "attention",
        "executive function",
        "cognitive control",
        "task switching",
        "inhibition",
        "working memory control",
        "predictive processing",
        "conflict monitoring",
    ],
    "Clinical / computational psychiatry": [
        "clinical",
        "psychiatry",
        "depression",
        "schizophrenia",
        "patient",
        "disorder",
        "mental health",
        "autism",
        "anxiety",
        "bipolar",
    ],
    "Methods, theory & everything else": [
        "method",
        "benchmark",
        "framework",
        "simulation",
        "theory",
        "analysis toolkit",
        "interpretability",
        "explainability",
        "attention mechanism",
        "recurrent neural network",
        "rnn",
        "lstm",
        "symbolic reasoning",
        "generalization",
        "statistical",
    ],
}

TITLE_WEIGHT = 2
ABSTRACT_WEIGHT = 3
KEYWORD_WEIGHT = 1

RELEVANCE_RATIO = 0.5
ABSOLUTE_COSINE_FLOOR = 0.05
MAX_ASSIGNED_TOPICS = 5
BROAD_HINT_BOOST = 0.04
CLUSTER_BOOST = 0.05


def strip_citation_fragments(text: str) -> str:
    if not text:
        return ""
    cleaned = text
    for pattern in CITATION_FRAGMENT_RES:
        cleaned = pattern.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.;")
    return cleaned.strip()


def normalize_keyword_phrase(keyword: str) -> str:
    return strip_citation_fragments(re.sub(r"\s+", " ", (keyword or "").strip().lower()))


def is_metadata_keyword(keyword: str) -> bool:
    normalized = normalize_keyword_phrase(keyword)
    if not normalized:
        return True
    if normalized in METADATA_KEYWORD_PHRASES:
        return True
    if normalized in GENERIC_KEYWORD_LABELS:
        return True
    tokens = re.findall(r"[a-z][a-z0-9\-]{2,}", normalized)
    if tokens and all(token in METADATA_KEYWORD_TOKENS for token in tokens):
        return True
    return False


def sanitize_keyword_list(keywords: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for keyword in keywords or []:
        normalized = normalize_keyword_phrase(str(keyword))
        if not normalized or len(normalized) <= 2:
            continue
        if is_metadata_keyword(normalized):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return cleaned


def sanitize_submission_keywords(submission: dict) -> None:
    for field in ("author_keywords", "extracted_keywords", "keywords"):
        submission[field] = sanitize_keyword_list(list(submission.get(field) or []))


def content_keywords(submission: dict) -> list[str]:
    for field in ("author_keywords", "extracted_keywords", "keywords"):
        values = sanitize_keyword_list(list(submission.get(field) or []))
        if values:
            return values
    return []


def is_weak_keyword_set(keywords: list[str]) -> bool:
    cleaned = sanitize_keyword_list(keywords)
    return not cleaned


def submission_embedding_text(submission: dict) -> str:
    """Build weighted embedding text: abstract-heavy, metadata keywords excluded."""
    title = (submission.get("title") or "").strip()
    abstract = (submission.get("abstract") or "").strip()
    chunks: list[str] = []
    if title:
        chunks.extend([title] * TITLE_WEIGHT)
    if abstract:
        chunks.extend([abstract] * ABSTRACT_WEIGHT)
    keywords = content_keywords(submission)
    if keywords:
        keyword_blob = " ".join(keywords)
        chunks.extend([keyword_blob] * KEYWORD_WEIGHT)
    blob = ". ".join(chunks).strip()
    return blob or title or "empty"


def topic_prototype_text(theme: str) -> str:
    anchors = TOPIC_ANCHORS.get(theme, [])
    parts: list[str] = []
    for anchor in anchors:
        repeat = 3 if " " in anchor else 2
        parts.extend([anchor] * repeat)
    return " ".join(parts) or theme.lower()


def vectorizer_stop_words() -> list[str]:
    return sorted(ENGLISH_STOP_WORDS | METADATA_KEYWORD_TOKENS)

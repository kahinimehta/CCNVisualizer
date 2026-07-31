"""Shared text cleanup and embedding helpers for scrape.py and build.py."""

from __future__ import annotations

import re

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

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

# Valid author-supplied acronyms; not conference metadata when used as keywords.
_AUTHOR_KEYWORD_ACRONYMS = frozenset(
    {
        "fmri",
        "eeg",
        "meg",
        "ecog",
        "bold",
        "mri",
        "pet",
        "dti",
        "erp",
        "lfp",
        "dnn",
        "tpj",
        "dmpfc",
        "vmpfc",
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

TITLE_WEIGHT = 2
ABSTRACT_WEIGHT = 3
KEYWORD_WEIGHT = 1

MAX_KEYWORD_CHARS = 72
MAX_KEYWORD_WORDS = 8
MAX_KEYWORD_LIST_SIZE = 8
CORRUPT_KEYWORD_SOURCE_COUNT = 15

KEYWORD_VERBS = frozenset(
    {
        "begin",
        "show",
        "shows",
        "using",
        "used",
        "note",
        "noted",
        "found",
        "make",
        "see",
        "seen",
        "give",
        "given",
        "provide",
        "provides",
        "suggest",
        "suggests",
        "suggesting",
        "demonstrate",
        "demonstrates",
        "maintain",
        "asked",
        "chairing",
        "inhibit",
        "confirming",
        "recruiting",
        "reflecting",
        "controlling",
        "requiring",
        "following",
        "starting",
        "mutated",
        "optimized",
        "spanned",
        "called",
        "proposed",
        "presented",
        "selected",
        "defined",
        "cannot",
        "are",
        "was",
        "were",
        "been",
        "being",
        "have",
        "has",
        "had",
        "does",
        "did",
        "can",
        "could",
        "would",
        "should",
        "may",
        "might",
    }
)

BAD_KEYWORD_FIRST_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "they",
        "this",
        "these",
        "those",
        "as",
        "we",
        "our",
        "it",
        "its",
        "blue",
        "for",
        "in",
        "of",
        "or",
        "but",
        "when",
        "while",
        "during",
        "after",
        "before",
        "among",
        "under",
        "like",
        "which",
        "where",
        "what",
        "that",
        "if",
        "from",
        "to",
        "via",
        "across",
        "relative",
        "contrary",
        "instead",
        "according",
        "even",
        "more",
        "most",
        "less",
        "also",
        "only",
        "just",
        "then",
        "thus",
        "hence",
        "yet",
        "still",
        "already",
        "again",
        "once",
        "both",
        "either",
        "neither",
        "whether",
        "whose",
        "whom",
        "who",
        "how",
        "why",
        "here",
        "there",
        "namely",
        "however",
        "therefore",
        "although",
        "whereas",
        "because",
        "since",
        "about",
        "into",
        "onto",
        "over",
        "above",
        "below",
        "between",
        "within",
        "without",
        "through",
        "against",
        "toward",
        "towards",
        "upon",
        "per",
        "vs",
        "versus",
        "such",
        "so",
        "not",
        "no",
        "yes",
        "all",
        "any",
        "each",
        "every",
        "other",
        "another",
        "same",
        "own",
        "few",
        "many",
        "several",
        "some",
        "visit",  # PDF extraction debris
        "figure",
        "table",
        "supplementary",
        "article",
        "https",
        "http",
        "doi",
        "pp",
        "vol",
        "ii",
        "iii",
        "iv",
    }
)

# Legitimate scientific phrases that start with an otherwise-banned first word.
ALLOWED_KEYWORD_PREFIXES = (
    "in vivo",
    "in vitro",
    "in silico",
    "in situ",
    "in phase",
)

BAD_KEYWORD_EXACT = frozenset(
    {
        "however",
        "namely",
        "i.e",
        "i.e.",
        "e.g",
        "e.g.",
        "etc",
        "etc.",
        "there is",
        "that is",
        "of course",
        "in general",
        "in particular",
        "in effect",
        "in principle",
        "in contrast",
        "in time",
        "on average",
        "at this moment",
        "to our knowledge",
        "to some extent",
        "for example",
        "for others",
        "by so",
        "by extrapolation",
        "and so on",
        "in the present work",
        "in the current work",
        "in our model",
        "in both task contexts",
        "in applied settings",
        "in untrained alexnet",
        "in all trials",
        "in one-sided mice",
        "during expert behavior",
        "during event processing",
        "during retrieval",
        "during both task phases",
        "during the pre scan",
        "at the same time",
        "more strongly",
        "even though",
        "though for practicality purposes",
        "at any time",
        "at any point in time",
        "right panel",
        "especially their output layers",
        "rather than scrambled",
        "built in python",
        "impacted by our goals",
        "connected room",
        "foreffective learning",
        "prioruncertainty and change-point probability",
        "strictly speaking",
        "more likely",
        "more precisely",
        "but ultimately",
        "but not across",
        "but not irrelevant",
        "but also in humans",
        "or alternatively",
        "or explicit",
        "or cold",
        "or color",
        "of course",
        "which are",
        "2afc",
        "arthur and belle",
        "eight candles",
        "now sixteen",
        "pot sizes",
        "physical sense",
        "beat and so on",
        "dining room",
        "human labelers",
        "travel to",
        "solving puzzles",
        "softer attack",
        "treasure locations",
        "data treatment",
        "activity level",
        "combining structures",
        "ve stibular",
        "square waves",
        "welwyn garden city",
        "titled gradient descent",
        "tree d",
        "subject",
        "plant or not",
        "biobehavioral reviews",
        "machine learning group",
        "goal location",
        "vertical line",
        "choices ci",
        "one after another",
        "m2 and ind",
        "withina block",
        "motivation in real life",
        "hydration and energy",
        "anticipatory or consummatory",
        "temporally blurred hr",
        "decreasing to a",
        "situated agents",
        "cmm and field l",
        "birdsong in sensory processing",
        "ely aniv",
        "el-y aniv",
        "highly simpliﬁed approximation",
        "highly simplified approximation",
        "models that meaningfully generalize",
        "fmri in uncertain environments",
        "lower spectral centroid",
        "navarro schröder",
        "navarro schroder",
        "ben-y akov",
        "hit attend visual",
        "miss attend visual",
        "multiple stimulus",
        "auditory stimulus identity",
        "memories, respectively",
        "norman et",
        "motion sdm",
        "color cdm",
        "facial geometry",
        "functional homomorphisms",
        "multiband factor 3",
        "standard deviation grill-spector",
        "state 1",
        "state 2",
        "bra em",
        "one untrained alexnet",
        "central areas",
        "quality assessments",
        "oleggio castello",
        "lower case for realisations",
        "datasets and analysis methods",
        "random seed",
        "russinet al",
        "four behavioural actionsa",
        "samanez -larkin",
        "konkle and alvarez",
        "ratcliff and mckoon",
        "simonyan and zisserman",
        "kemp and tenenbaum",
        # Prose / grant / typo debris
        "on the other hand",
        "exactly how that organization",
        "depending on context",
        "fask fmri",
        # Citation / author crumbs commonly scraped into keyword fields
        "shepard",
        "naselaris",
        "st-yves",
        "huth",
        "lescroart",
        "gallant",
        "griffiths",
        "grifﬁths",
        "theunissen",
        "axmacher",
        "dubois",
        "vanrullen",
        "arduini",
        "habenschuss",
        "reddy",
        "mnih",
        "radoslaw martin",
        "aditya khosla",
        "dimitrios pantazis",
        "antonio torralba",
        "johanni brea",
        "gollo",
        "zalesky",
        "breakspear",
        "de magalhães",
        "de magalhaes",
        "clare kelly",
        "xavier castellanos",
        "b1* etc",
        "aware of this rule",
        "von kriegstein",
        "u ˘gurbil",
        "u gurbil",
        "⃗y is output",
        "y is output",
        "dkl is kl divergence",
        "main",
        "faces",
        "currently under way",
        "red brace",
        "palo alto",
        "marslen wilson",
        "von heimendahl",
        "hellgren kotaleski",
        "soko l-hessner",
        "hindi attar",
        "b üchel",
        "büchel",
        "adding",
        "supported",
        "solves",
        "evoke",
        "characterization",
    }
)

BAD_KEYWORD_PREFIXES = (
    "though for ",
    "at any ",
    "especially ",
    "rather than ",
    "built in ",
    "impacted by ",
    "occurs at ",
    "every synapse",
    "their output ",
    "point in time",
    "including ",
    "and ",
    "as well",
    "as noted",
    "such as ",
    "however ",
    "therefore ",
    "although ",
    "more importantly",
    "consistent with ",
    "previous work ",
    "in contrast ",
    "goals such as ",
    "instead of ",
    "similar to ",
    "relative to ",
    "contrary to ",
    "due to ",
    "based on ",
)

# Equation / stats / demographics / citation debris.
BAD_KEYWORD_PATTERN_RES = (
    re.compile(r"[=≠≈≤≥<>]=?"),  # equations / comparisons
    re.compile(r"[∑∫√∞∈∉⊂⊃∪∩∀∃∇∂]"),  # math operators
    re.compile(r"[α-ωΑ-Ωµμσρηλθφψτωκ]"),  # greek letters (stats/math debris)
    re.compile(r"\bp\s*[<>=]"),  # p-values
    re.compile(r"\b[rtfn]\s*=\s*"),  # r=/t=/n=/f= stats
    re.compile(r"\bcohen"),
    re.compile(r"\bsd\s*="),
    re.compile(r"\bmean age\b"),
    re.compile(r"\b\d+\s*(male|female|men|women|subjects?|participants?)\b"),
    re.compile(r"\b(male|female|men|women)\b"),
    re.compile(r"^\d+(\.\d+)?$"),  # bare numbers
    re.compile(r"^[\d\s.+:-]+$"),  # numeric-only crumbs ("0 1", "1 12 2")
    re.compile(r"^\d+\s"),  # leading counts ("40 non-faces", "4 directions")
    re.compile(r"^\d+(?!d\b|/f\b)[a-z]"),  # "1following finzi" but keep 3d / 1/f
    re.compile(r"\b\d+t/\d+t\b"),  # 3t/7t scanner debris
    re.compile(r"^\d+\)"),  # numbered-list debris
    re.compile(r"\d{4}\)\s"),  # year) citation mash
    re.compile(r"\d{4}\)\."),  # 2018).in
    re.compile(r"\d{4}\):"),  # 2019): sustained
    re.compile(r"^\d{4}\)?$"),  # bare year or year)
    re.compile(r"\d+%"),  # 20% validation
    re.compile(r"\d+\s*ms\b"),  # 100ms on / tr timings
    re.compile(r"\btr\s*="),
    re.compile(r"\bte\s*="),
    re.compile(r"\bhttps?://"),
    re.compile(r"\bdoi\b"),
    re.compile(r"\bfigure\s+\d"),
    re.compile(r"\bet\s*al\b"),
    re.compile(r"\b\d{4}$"),  # trailing citation year
    re.compile(r"\b(op de|del|van der|van den|van de)\b"),  # name particles
    re.compile(r"\band so on\b"),
    re.compile(r":"),  # parameter / label debris
    re.compile(r"[●…•]"),
    re.compile(r"[\[\]{}]"),
    re.compile(r"\brecently\b"),
    re.compile(r"\bhttps?\b"),
    re.compile(r"[¨´`ˆ^ˇ¯−]"),  # mojibake / stray diacritic crumbs
    re.compile(r"\s-"),  # "fernández -ruiz" style name debris (keep explore-exploit)
    re.compile(r"^[\"'“”‘’]+|[\"'“”‘’]+$"),  # wrapping quotes
    re.compile(r"^[a-z]+\s+and\s+[a-z]+$"),  # "arthur and belle"
    re.compile(r"\b(to|of|for|with|from|by|into|onto|at|as)$"),  # trailing preposition
    re.compile(r"^[a-z]{3,}\s+[a-z]$"),  # "jade b" / first-name + initial
    re.compile(r"[a-z]{28,}"),  # smashed PDF tokens (no spaces/hyphens)
    re.compile(r"[º°]"),  # degree debris in keywords
    re.compile(r"\brespectively\b"),
    re.compile(r"\bstate\s+\d+\b"),
    re.compile(r"\b(memory|behavior|projects)\s+\S*\d"),
    re.compile(r"\bdo\s+\d"),  # grant crumbs
    re.compile(r"\br0\d\b"),  # NIH-style grant ids (r01 mh112847)
    re.compile(r"\bsummary\b"),  # "foraging summary whether..."
    re.compile(r"\bwhether\b"),
    re.compile(r"\bwant to\b"),
    re.compile(r"\bother hand\b"),
    re.compile(r"\betc\b"),
    re.compile(r"\bis (output|kl|the)\b"),
    re.compile(r"\bcorresponding author\b"),
    re.compile(r"\breferences?\b"),  # "working memory references brunel"
    re.compile(r"\b(forschungsbereich|e-science research|research center|funding)\b"),
    re.compile(r"\b[a-z]+(?:\s+[a-z]+)?\s+[a-z]{1,2}$"),  # "donner th", "silbert lj"
    re.compile(r"[*~`^|\\{}[\]<>#$%@!;:=]"),  # odd symbols (keep + for pv+)
    re.compile(r"[^\w\s\-/&'+]{2,}"),  # runs of odd punctuation/symbols
    re.compile(r"[\U0001D400-\U0001D7FF]"),  # mathematical alphanumeric symbols
)

TITLE_KEYWORD_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "for",
        "in",
        "on",
        "to",
        "and",
        "with",
        "from",
        "by",
        "via",
        "using",
        "model",
        "models",
        "study",
        "studies",
        "toward",
        "towards",
        "between",
        "across",
        "into",
        "through",
        "during",
        "within",
        "without",
        "based",
        "new",
        "novel",
        "how",
        "why",
        "what",
        "who",
        "when",
        "where",
        "which",
        "whose",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "people",
        "human",
        "humans",
        "do",
        "does",
        "are",
        "is",
        "its",
        "their",
        "our",
        "more",
        "than",
        "over",
        "under",
        "about",
        "after",
        "before",
        "against",
        "revisited",
        "review",
        "perspective",
    }
)

_MOJIBAKE_MARKERS = re.compile(
    r"[ÃÄÅÆÇÐÑØÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\u0080-\u009f]|"
    r"â€™|â€˜|â€œ|â€\u009d|â€\u201c|â€\u201d|‚Äô|‚Äì|√.|ï¿½"
)

_MOJIBAKE_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("\u00e2\u20ac\u2122", "'"),
    ("\u00e2\u20ac\u02dc", "'"),
    ("\u00e2\u20ac\u0153", '"'),
    ("\u00e2\u20ac\u009d", '"'),
    ("\u00e2\u20ac\u0094", "—"),
    ("\u00e2\u20ac\u0093", "–"),
    ("‚Äô", "'"),
    ("‚Äì", "–"),
    ("Ã©", "é"),
    ("Ã¨", "è"),
    ("Ã«", "ë"),
    ("Ã¯", "ï"),
    ("Ã®", "î"),
    ("Ã¶", "ö"),
    ("Ã¼", "ü"),
    ("Ã¤", "ä"),
    ("Ã ", "à"),
    ("Ã¡", "á"),
    ("Ã¢", "â"),
    ("Ã§", "ç"),
    ("Ã±", "ñ"),
    ("ï¿½", ""),
)

_MOJIBAKE_QUOTED_RE = re.compile(r"â([^â\n]{1,120}?)â")

_LIGATURE_MAP = str.maketrans(
    {
        "\ufb00": "ff",
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\ufb03": "ffi",
        "\ufb04": "ffl",
        "\ufb05": "st",
        "\ufb06": "st",
    }
)

_ACUTE_VOWEL_MAP = {
    "a": "á",
    "e": "é",
    "i": "í",
    "o": "ó",
    "u": "ú",
    "A": "Á",
    "E": "É",
    "I": "Í",
    "O": "Ó",
    "U": "Ú",
}

_COMPOUND_SUFFIXES = (
    "supervised",
    "learning",
    "processing",
    "reasoning",
    "interactions",
    "interaction",
    "networks",
    "network",
    "models",
    "model",
    "perception",
    "connectome",
    "datasets",
    "dataset",
    "cognition",
    "probability",
    "error",
    "preference",
    "stimuli",
    "stimulus",
    "differences",
    "difference",
    "planning",
    "making",
    "directed",
    "coding",
    "generalisation",
    "generalization",
    "behavior",
    "behaviour",
    "hierarchy",
    "tracking",
    "control",
    "representations",
    "representation",
    "prediction",
    "predictions",
    "fmri",
    "neuroscience",
    "deep",
    "open",
    "source",
    "guided",
    "temporal",
    "spatial",
    "visual",
    "cortex",
    "reinforcement",
    "decision",
    "social",
    "cognitive",
    "naturalistic",
    "generative",
    "scene",
    "choice",
    "recursive",
    "strategic",
    "attention",
    "inference",
    "plasticity",
    "modulation",
)

GAC_UPDATE_TITLE_RE = re.compile(r"^\[\s*GAC\s+update\s*\]", re.I)
YEAR_ID_CACHE_KEY_RE = re.compile(r"^\d{4}:")


def submission_row_key(submission: dict) -> str:
    """Stable per-paper key; CCN reuses numeric ids across years."""
    year = submission.get("year", "")
    paper_id = str(submission.get("id") or submission.get("poster_number") or submission.get("title", ""))
    return f"{year}:{paper_id}"


def is_year_id_cache_key(key: str) -> bool:
    return bool(YEAR_ID_CACHE_KEY_RE.match(str(key)))


def is_gac_update(title: str) -> bool:
    """True for CCN Generative Adversarial Collaboration update posters (not regular submissions)."""
    return bool(GAC_UPDATE_TITLE_RE.match((title or "").strip()))


def strip_citation_fragments(text: str) -> str:
    if not text:
        return ""
    cleaned = text
    for pattern in CITATION_FRAGMENT_RES:
        cleaned = pattern.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.;")
    return cleaned.strip()


# Zero-width / format / stray combining marks often pasted from PDFs.
_KEYWORD_INVISIBLE_RE = re.compile(
    r"[\u200b\u200c\u200d\u2060\ufeff\u00ad\u200e\u200f"
    r"\u0300-\u036f\u20d0-\u20ff\u02d8\u02c6\u02c7\u02d9\u02da\u02dc]"
)

_CURLY_QUOTE_MAP = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u201f": '"',
        "\u2032": "'",
        "\u2033": '"',
    }
)


def sanitize_display_text(text: str) -> str:
    """Normalize PDF/encoding artifacts for dashboard and CSV display."""
    if not text:
        return text
    cleaned = normalize_ligatures(str(text))
    cleaned = _KEYWORD_INVISIBLE_RE.sub("", cleaned)
    cleaned = cleaned.translate(_CURLY_QUOTE_MAP)
    cleaned = cleaned.replace("\u00a0", " ")
    cleaned = re.sub(r"Â+(?=[\s.,;:!?)}\]]|$)", "", cleaned)
    cleaned = cleaned.replace("Â", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_ligatures(text: str) -> str:
    if not text:
        return text
    return text.translate(_LIGATURE_MAP)


def repair_accent_marks(text: str) -> str:
    if not text or "\u00b4" not in text:
        return text

    def repl(match: re.Match[str]) -> str:
        base, vowel = match.group(1), match.group(2)
        accented = _ACUTE_VOWEL_MAP.get(vowel)
        return f"{base}{accented}" if accented else match.group(0)

    return re.sub(r"([A-Za-z])\u00b4([aeiouAEIOU])", repl, text)


def expand_compound_token(token: str) -> str:
    keyword = normalize_ligatures(token.lower().strip())
    keyword = keyword.replace("‐", "-").replace("–", "-")
    keyword = re.sub(r"(?<=[a-z])and(?=[a-z])", " and ", keyword)
    keyword = re.sub(r"\s+", " ", keyword).strip()
    if not keyword:
        return keyword
    if len(keyword) <= 5:
        return keyword
    if " " in keyword:
        return " ".join(expand_compound_token(part) for part in keyword.split())

    changed = True
    while changed:
        changed = False
        for suffix in sorted(_COMPOUND_SUFFIXES, key=len, reverse=True):
            if len(keyword) <= len(suffix) + 2 or not keyword.endswith(suffix):
                continue
            prefix = keyword[: -len(suffix)].rstrip("-")
            if prefix and prefix.replace("-", "").isalpha() and not prefix.endswith("-"):
                keyword = f"{prefix} {suffix}"
                changed = True
                break

    if " " in keyword:
        return " ".join(expand_compound_token(part) for part in keyword.split())
    return keyword


def expand_compound_keyword(keyword: str) -> str:
    if not keyword:
        return keyword
    return " ".join(
        part
        for token in re.split(r"(\s+)", keyword)
        for part in ([token] if token.isspace() else [expand_compound_token(token)])
        if part and not part.isspace()
    )


_KEYWORD_SCIENCE_TERMS = frozenset(
    {
        "network",
        "networks",
        "learning",
        "memory",
        "neural",
        "model",
        "models",
        "brain",
        "visual",
        "cortex",
        "connectome",
        "reinforcement",
        "processing",
        "inference",
        "coding",
        "control",
        "decision",
        "auditory",
        "theoretical",
        "computational",
        "attention",
        "prediction",
        "perception",
        "behavior",
        "behaviour",
        "artificial",
        "recurrent",
        "neuroscience",
        "generalisation",
        "generalization",
        "scaffold",
        "temporal",
        "spatial",
        "cooperation",
        "altruism",
        "preference",
        "hippocampus",
        "plasticity",
        "navigation",
        "mentalization",
        "specialization",
        "modularity",
        "effective",
        "connectivity",
    }
)


_COMMON_FIRST_NAMES = frozenset(
    {
        "aaron",
        "adam",
        "alex",
        "alexander",
        "alice",
        "amy",
        "andrew",
        "anna",
        "anthony",
        "benjamin",
        "brian",
        "carla",
        "charles",
        "chris",
        "christopher",
        "daniel",
        "david",
        "elena",
        "elizabeth",
        "emma",
        "eva",
        "george",
        "grace",
        "hannah",
        "james",
        "jane",
        "jennifer",
        "john",
        "joseph",
        "julia",
        "kate",
        "katherine",
        "kevin",
        "laura",
        "linda",
        "lisa",
        "maria",
        "mark",
        "martha",
        "mary",
        "michael",
        "michelle",
        "nahid",
        "nancy",
        "nicholas",
        "olivia",
        "paul",
        "peter",
        "rachel",
        "richard",
        "robert",
        "sarah",
        "stephen",
        "steven",
        "susan",
        "thomas",
        "william",
    }
)


def keyword_looks_like_name_or_citation(keyword: str) -> bool:
    normalized = normalize_keyword_phrase(keyword)
    if not normalized:
        return False
    if normalized.startswith("goto") or normalized.startswith("no-goto"):
        return True
    if " goto " in f" {normalized} ":
        return True
    words = normalized.split()
    if len(words) == 2 and len(words[0]) <= 2 and words[0].isalpha():
        return True
    return keyword_looks_like_person_name(normalized)


def keyword_looks_like_person_name(keyword: str) -> bool:
    normalized = normalize_keyword_phrase(keyword)
    if not normalized or "(" in normalized or "-" in normalized:
        return False
    words = normalized.split()
    if len(words) != 2:
        return False
    if words[0] in {"van", "de", "del", "da", "di", "le", "la", "el", "al", "von", "der"}:
        return True
    if not all(2 <= len(word) <= 14 and word.isalpha() for word in words):
        return False
    if words[0] in _COMMON_FIRST_NAMES:
        return True
    if any(term in normalized for term in _KEYWORD_SCIENCE_TERMS):
        return False
    return False


def drop_reference_name_keywords(keywords: list[str]) -> list[str]:
    if len(keywords) < 6:
        return keywords
    filtered = [kw for kw in keywords if not keyword_looks_like_person_name(kw)]
    if len(filtered) >= 2 and len(filtered) < len(keywords):
        return filtered
    return keywords


def normalize_keyword_phrase(keyword: str) -> str:
    cleaned = _KEYWORD_INVISIBLE_RE.sub("", keyword or "")
    cleaned = normalize_ligatures(cleaned)
    cleaned = re.sub(r"-\s+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned.strip().lower())
    cleaned = strip_citation_fragments(cleaned)
    cleaned = expand_compound_keyword(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.;")
    cleaned = re.sub(r"\bf\s+mri\b", "fmri", cleaned)
    cleaned = re.sub(r"\bopensourcef\s+mri\b", "open source fmri", cleaned)
    cleaned = re.sub(r"\bdeepf\s+mri\b", "deep fmri", cleaned)
    cleaned = re.sub(r"\bdenseanddeepf\s+mri\b", "dense and deep fmri", cleaned)
    acronym_fixes = {
        "dm pfc": "dmpfc",
        "dm-pfc": "dmpfc",
        "vm pfc": "vmpfc",
        "vm-pfc": "vmpfc",
    }
    cleaned = acronym_fixes.get(cleaned, cleaned)
    return cleaned


def is_metadata_keyword(keyword: str) -> bool:
    normalized = normalize_keyword_phrase(keyword)
    if not normalized:
        return True
    if normalized in _AUTHOR_KEYWORD_ACRONYMS:
        return False
    if normalized in METADATA_KEYWORD_PHRASES:
        return True
    if normalized in GENERIC_KEYWORD_LABELS:
        return True
    tokens = re.findall(r"[a-z][a-z0-9\-]{2,}", normalized)
    if tokens and all(token in METADATA_KEYWORD_TOKENS for token in tokens):
        return True
    return False


def normalize_field_text(text: str) -> str:
    if not text:
        return ""
    cleaned = sanitize_display_text(repair_mojibake(str(text)))
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"\s*\n\s*", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


_COUNTRY_NAMES = frozenset(
    {
        "united states",
        "united kingdom",
        "usa",
        "uk",
        "u.s.",
        "u.s.a.",
        "u.k.",
        "netherlands",
        "germany",
        "france",
        "canada",
        "china",
        "japan",
        "switzerland",
        "australia",
        "italy",
        "spain",
        "israel",
        "belgium",
        "india",
        "hungary",
        "ireland",
        "turkey",
        "sweden",
        "austria",
        "denmark",
        "norway",
        "brazil",
        "korea",
        "south korea",
        "taiwan",
        "singapore",
        "mexico",
        "poland",
        "portugal",
        "finland",
        "russia",
        "new zealand",
        "czech republic",
        "czech",
        "slovakia",
        "greece",
        "chile",
        "argentina",
        "colombia",
        "hong kong",
        "scotland",
        "wales",
        "england",
        "republic of korea",
        "luxembourg",
        "estonia",
        "latvia",
        "lithuania",
        "romania",
        "bulgaria",
        "croatia",
        "serbia",
        "slovenia",
        "iceland",
        "ukraine",
        "pakistan",
        "thailand",
        "vietnam",
        "indonesia",
        "malaysia",
        "philippines",
        "south africa",
        "egypt",
        "saudi arabia",
        "uae",
        "united arab emirates",
        "qatar",
        "iran",
        "iraq",
        "peru",
        "uruguay",
        "venezuela",
        "cuba",
        "jamaica",
        "cyprus",
        "malta",
        "liechtenstein",
        "monaco",
        "andorra",
        "san marino",
        "vatican",
        "vatican city",
        "north macedonia",
        "bosnia",
        "bosnia and herzegovina",
        "albania",
        "georgia",
        "armenia",
        "azerbaijan",
        "kazakhstan",
        "morocco",
        "tunisia",
        "algeria",
        "nigeria",
        "kenya",
        "ghana",
        "ethiopia",
        "tanzania",
        "uganda",
        "nepal",
        "sri lanka",
        "bangladesh",
        "myanmar",
        "cambodia",
        "laos",
        "mongolia",
        "uzbekistan",
        "belarus",
        "moldova",
        "montenegro",
        "kosovo",
        "palestine",
        "lebanon",
        "jordan",
        "syria",
        "yemen",
        "oman",
        "kuwait",
        "bahrain",
        "brunei",
        "fiji",
        "papua new guinea",
        "new caledonia",
        "puerto rico",
        "costa rica",
        "panama",
        "guatemala",
        "honduras",
        "el salvador",
        "nicaragua",
        "dominican republic",
        "ecuador",
        "bolivia",
        "paraguay",
        "suriname",
        "guyana",
        "trinidad and tobago",
        "barbados",
        "bahamas",
        "iceland",
        "greenland",
        "faroe islands",
    }
)

_AFFILIATION_HINTS = (
    # "univer" covers university / université / universitat / univeristy typo / universitaet
    "univer",
    "institute",
    "institut",
    "college",
    "hospital",
    "department",
    "dept.",
    "school of",
    "laboratory",
    "lab ",
    "labs",
    "centre",
    "center",
    "ctr.",
    "campus",
    "neurosci",
    "neuroinfo",
    "neuromodulation",
    "republic of",
    "berkeley",
    "stanford",
    "harvard",
    "oxford",
    "cambridge",
    "deepmind",
    "google",
    "max planck",
    "cnrs",
    "inria",
    "eth zurich",
    "eth zürich",
    "epfl",
    "caltech",
    "princeton",
    "columbia",
    "carnegie",
    "weizmann",
    "technion",
    "imperial college",
    "university college",
    "vrije",
    "johns hopkins",
    "tuebingen",
    "tübingen",
    "international",
    "neurospin",
    "kuleuven",
    "birkbeck",
    "vanderbilt",
    "amherst",
    "janelia",
    "hyderabad",
    "stuttgart",
    "charité",
    "charite",
    "sorbonne",
    "pompeu",
    "jaume",
    "osnabr",
    "freie",
    "école",
    "ecole",
    "normale",
    "iiit",
    "hhmi",
    "upf",
    "cognition and behaviour",
    "cognition and behavior",
    "brain and language",
    "centrum",
    "wiskunde",
    "informatica",
    "champalimaud",
    "ecortex",
    "neurotechnology",
    "neurocognitive",
    "saclay",
    "cea ",
    " cea",
    "zentrum",
    "spielsucht",
)

# Campus / city shorthands and orgs that appear as whole trailing author tokens.
_PLACE_OR_ORG_TOKENS = frozenset(
    {
        "davis",
        "daivs",  # common typo in CCN listings
        "san diego",
        "riverside",
        "los angeles",
        "irvine",
        "santa barbara",
        "santa cruz",
        "berkeley",
        "new york",
        "california",
        "massachusetts",
        "amherst",
        "hyderabad",
        "bangalore",
        "bengaluru",
        "stuttgart",
        "berlin",
        "paris",
        "kuleuven",
        "birkbeck",
        "vanderbilt",
        "neurospin",
        "cerco",
        "charité",
        "charite",
        "cognition",  # Donders department fragment ("Cognition, and Behaviour")
        "and behaviour",
        "and behavior",
        "atr international",
        "vicarious ai",
        "idibaps",
        "mta wigner rcp",
        "wigner rcp",
        "deepmind",
        "google deepmind",
        "google brain",
        "openai",
        "meta ai",
        "facebook ai",
        "microsoft research",
        "benevolent ai",
        "neuromatch",
        "tu dublin",
        "brain and language",
        "centrum wiskunde & informatica",
        "centrum wiskunde and informatica",
        "champalimaud research",
        "champalimaud foundation",
        "hungarian academy of sciences",
        "cea paris-saclay",
        "cea paris saclay",
        "ecortex inc",
        "translational neurotechnology lab",
        "applied neurocognitive psychology lab",
    }
)


def _is_country_token(part: str) -> bool:
    cleaned = part.lower().strip(" .")
    if cleaned.startswith("the "):
        cleaned = cleaned[4:].strip()
    return cleaned in _COUNTRY_NAMES


def _is_affiliation_token(part: str) -> bool:
    """True for countries, labs, universities, and short org acronyms (MIT, NYU, …)."""
    cleaned = part.strip().strip("()")
    if not cleaned:
        return False
    if _is_country_token(cleaned):
        return True
    lowered = cleaned.lower().strip(" .")
    # Department-name fragments split on commas: "Cognition, and Behaviour"
    if lowered.startswith("and "):
        return True
    if lowered in _PLACE_OR_ORG_TOKENS:
        return True
    if any(hint in lowered for hint in _AFFILIATION_HINTS):
        return True
    # Trailing org/department labels (Lab, Inc, Foundation, …)
    if re.search(
        r"\b("
        r"labs?|inc|llc|ltd|gmbh|corp|foundation|academy|sciences?|"
        r"research|unit|group|campus|hospital|clinic|company"
        r")\b",
        lowered,
    ):
        return True
    # Short org acronyms commonly appended after author lists.
    if re.fullmatch(r"[A-Z]{2,6}", cleaned):
        return True
    if re.match(r"^UC\b", cleaned):
        return True
    if re.match(r"^CEA\b", cleaned):
        return True
    return False


# Known scrape artifacts where a first name was truncated across a comma.
_SPLIT_NAME_REPAIRS = {
    ("bertr", "thirion"): "Bertrand Thirion",
    ("rol", "fleming"): "Roland Fleming",
}


def _repair_split_person_names(parts: list[str]) -> list[str]:
    """Merge truncated 'Bertr, Thirion' / 'Rol, Fleming' into full person names."""
    repaired: list[str] = []
    index = 0
    while index < len(parts):
        if index + 1 < len(parts):
            key = (parts[index].strip().lower(), parts[index + 1].strip().lower())
            full = _SPLIT_NAME_REPAIRS.get(key)
            if full:
                repaired.append(full)
                index += 2
                continue
        repaired.append(parts[index])
        index += 1
    return repaired


_NAME_PARTICLES = frozenset(
    {
        "van",
        "von",
        "de",
        "da",
        "di",
        "del",
        "della",
        "der",
        "den",
        "la",
        "le",
        "du",
        "des",
        "af",
        "av",
        "y",
        "ten",
        "ter",
        "te",
        "bin",
        "ibn",
        "al",
        "dos",
        "das",
        "do",
    }
)


def _capitalize_name_token(token: str, *, allow_particle: bool) -> str:
    """Capitalize a single name token (first/last/initial); keep mid-name particles lower."""
    if not token:
        return token
    match = re.match(r"^([\"'(]*)(.*?)([\"')]*)$", token)
    prefix, core, suffix = match.group(1), match.group(2), match.group(3)
    if not core:
        return token

    lower = core.lower()
    if allow_particle and lower in _NAME_PARTICLES:
        return f"{prefix}{lower}{suffix}"

    # Single-letter initial: "j" / "j."
    if re.fullmatch(r"[A-Za-z]\.?", core):
        letter = core[0].upper()
        dotted = f"{letter}." if core.endswith(".") else letter
        return f"{prefix}{dotted}{suffix}"

    # Compact initials: "J.D." / "i.a."
    if re.fullmatch(r"(?:[A-Za-z]\.){2,}", core):
        compact = "".join(ch.upper() if ch.isalpha() else ch for ch in core)
        return f"{prefix}{compact}{suffix}"

    # Hyphenated: Jean-rémi → Jean-Rémi
    if "-" in core:
        pieces = [
            _capitalize_name_token(piece, allow_particle=False) if piece else piece
            for piece in core.split("-")
        ]
        return f"{prefix}{'-'.join(pieces)}{suffix}"

    # Apostrophe names: o'brien → O'Brien
    if "'" in core:
        bits = []
        for piece in core.split("'"):
            if not piece:
                bits.append(piece)
            else:
                bits.append(piece[0].upper() + piece[1:].lower())
        return f"{prefix}{chr(39).join(bits)}{suffix}"

    # Mc / Mac
    mac = re.match(r"^(Mc|Mac|MC|MAC|mc|mac)([A-Za-z].*)$", core)
    if mac:
        pref, rest = mac.group(1), mac.group(2)
        pref_out = "Mc" if pref.lower() == "mc" else "Mac"
        return f"{prefix}{pref_out}{rest[0].upper()}{rest[1:].lower()}{suffix}"

    # Already has internal capitals (AlRoumi): capitalize first char only
    if any(ch.isupper() for ch in core[1:]):
        return f"{prefix}{core[0].upper()}{core[1:]}{suffix}"

    return f"{prefix}{core[0].upper()}{core[1:].lower()}{suffix}"


def capitalize_author_names(authors: str) -> str:
    """Ensure first/last names and middle initials are capitalized."""
    if not authors:
        return ""
    people = []
    for person in re.split(r"\s*,\s*", authors):
        person = person.strip()
        if not person:
            continue
        tokens = person.split()
        last_index = len(tokens) - 1
        capped = []
        for index, token in enumerate(tokens):
            # Particles stay lower only in the middle (e.g. Marcel van Gerven),
            # never when they are the surname (e.g. Quan Do).
            allow_particle = 0 < index < last_index
            capped.append(_capitalize_name_token(token, allow_particle=allow_particle))
        people.append(" ".join(capped))
    return ", ".join(people)


def normalize_author_names(authors: str) -> str:
    """Keep only person names: drop emails, labs, countries, and university footnotes.

    Example:
      "Ada Lovelace 1 ( ada@x.edu ), Alan Turing 2,3 ; 1 Uni A, 2 Uni B, 3 Lab C"
      → "Ada Lovelace, Alan Turing"
      "Jane Doe, MIT, United States" → "Jane Doe"
    """
    if not authors:
        return ""

    text = normalize_field_text(authors)
    lowered_full = text.lower()
    # Scrape noise sometimes lands in the author field.
    if lowered_full.startswith("presentation time"):
        return ""

    # Name block is before affiliation footnotes ("… ; 1 University…").
    text = text.split(";", 1)[0].strip()
    if not text:
        return ""

    # Drop emails and empty parentheticals (keep nicknames like "Lune (Pierre) Bellec").
    text = re.sub(r"\([^)]*@[^)]*\)", " ", text)
    text = re.sub(r"\(\s*\)", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    parts = [part.strip() for part in re.split(r"\s*,\s*", text) if part.strip()]
    # 2018–2022 listings often append ", Lab/Uni, Country" after the name list.
    while parts and _is_affiliation_token(parts[-1]):
        parts.pop()

    names: list[str] = []
    for part in parts:
        # Affiliation markers split as their own tokens: "Name 2,3" → "Name 2", "3".
        if re.fullmatch(r"\d+", part):
            continue
        # Glued affiliation start: "1Ctr. for Neurosci…" — stop; rest is not names.
        if re.match(r"^\d+[A-Za-z]", part):
            break
        if _is_affiliation_token(part):
            break
        # Trailing footnotes / superscripts: "Name 1", "Name 2,3", "Name*", "Name†".
        part = re.sub(r"(?:\s*[\d†‡*#]+(?:\s*,\s*[\d†‡*#]+)*)+\s*$", "", part)
        part = re.sub(r"\s+", " ", part).strip(" ,;")
        if not part or re.fullmatch(r"\d+", part):
            continue
        if _is_affiliation_token(part):
            break
        # Author separators must be commas only — split "A & B" / "A and B".
        # Require whitespace around "and" so names like "Bertrand" are preserved.
        for person in re.split(r"\s+and\s+|\s*&\s*", part, flags=re.IGNORECASE):
            person = person.strip(" ,;")
            if not person or _is_affiliation_token(person):
                continue
            if person not in names:
                names.append(person)

    names = _repair_split_person_names(names)
    # Drop any residual non-person tokens that slipped through.
    names = [name for name in names if name and not _is_affiliation_token(name)]

    cleaned = capitalize_author_names(", ".join(names))
    # Final guard: never leave "&" or "and" as list joiners in the author field.
    cleaned = re.sub(r"\s+and\s+|\s*&\s*", ", ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned).strip(" ,")
    return capitalize_author_names(cleaned)


def is_plausible_keyword(keyword: str) -> bool:
    normalized = normalize_keyword_phrase(keyword)
    if not normalized:
        return False
    if len(normalized) > MAX_KEYWORD_CHARS:
        return False
    if normalized in BAD_KEYWORD_EXACT:
        return False
    words = normalized.split()
    if not words or len(words) > MAX_KEYWORD_WORDS:
        return False
    if len(words) == 1 and re.fullmatch(r"\d{4}", words[0]):
        return False

    allowed_prefix = any(normalized == prefix or normalized.startswith(prefix + " ") for prefix in ALLOWED_KEYWORD_PREFIXES)
    if not allowed_prefix and words[0] in BAD_KEYWORD_FIRST_WORDS:
        return False
    if any(normalized.startswith(prefix) for prefix in BAD_KEYWORD_PREFIXES):
        return False
    if any(word in KEYWORD_VERBS for word in words):
        return False
    if any(len(word) > (36 if "-" in word else 18) for word in words):
        return False
    if re.search(r"[.!?]", normalized):
        return False
    if re.search(r"[∝≈≤≥±×÷′]", normalized):
        return False
    if re.search(r"^\)|\bpr\(", normalized):
        return False
    if len(normalized) > 48 and any(
        marker in f" {normalized} " for marker in (" similar to ", " compared to ", " rather than ")
    ):
        return False
    if normalized.count("(") != normalized.count(")"):
        return False
    if normalized.startswith(")") or normalized.endswith("("):
        return False
    if any(pattern.search(normalized) for pattern in BAD_KEYWORD_PATTERN_RES):
        return False
    if len(normalized) > 36 and ("," in normalized or ";" in normalized):
        return False
    prose_markers = (
        " the ",
        " and ",
        " that ",
        " which ",
        " with ",
        " from ",
        " into ",
        " their ",
        " there ",
        " this ",
        " these ",
        " those ",
        " than ",
        " then ",
        " also ",
        " such ",
    )
    if len(words) >= 5 and any(marker in f" {normalized} " for marker in prose_markers):
        return False
    # Lone citation-style surname crumbs / broken OCR tokens.
    if len(words) <= 2 and re.search(
        r"(^|\s)(van|de|del|da|di|le|la|el|al)\s+\w{2,}$",
        normalized,
        flags=re.UNICODE,
    ):
        return False
    if re.search(r"\b[a-z]\s+[a-z]{2,}\b", normalized) and " " in normalized:
        # "y oo", "g ¨ardenfors", "s ¨orensen" style broken tokens
        if any(len(w) == 1 for w in words if w.isalpha()):
            return False
    return True


def keywords_look_low_quality(keywords: list[str], submission: dict) -> bool:
    if not keywords:
        return False
    title = str(submission.get("title") or "")
    abstract = str(submission.get("abstract") or "").lower()
    normalized = [normalize_keyword_phrase(kw) for kw in keywords if kw]
    if not normalized:
        return False
    if keywords_are_title_derived(normalized, title):
        return True
    if any(len(kw) > 24 and " " not in kw and kw.isalpha() for kw in normalized):
        return True
    if any(re.search(r"[a-z]{14,}", kw) and " " not in kw for kw in normalized):
        return True
    singles = [kw for kw in normalized if " " not in kw]
    if len(normalized) >= 8 and len(singles) / len(normalized) >= 0.75:
        if sum(1 for kw in singles if kw in abstract) >= max(3, len(singles) - 1):
            return True
    return False


def keywords_are_title_derived(keywords: list[str], title: str) -> bool:
    """True when keywords are just tokenized title words, not author keywords."""
    if not keywords or not title:
        return False
    normalized = [normalize_keyword_phrase(kw) for kw in keywords if kw]
    if not normalized:
        return False
    if normalized == derive_title_keywords(title):
        return True
    title_tokens = set(re.findall(r"[a-z][a-z0-9\-]{2,}", title.lower()))
    if title_tokens and all(" " not in kw and kw in title_tokens for kw in normalized):
        return True
    return False


def derive_title_keywords(title: str, limit: int = 5) -> list[str]:
    tokens = re.findall(r"[a-z][a-z0-9\-]{2,}", (title or "").lower())
    cleaned: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token in TITLE_KEYWORD_STOPWORDS or token in seen:
            continue
        if is_metadata_keyword(token):
            continue
        if not is_plausible_keyword(token):
            continue
        seen.add(token)
        cleaned.append(token)
        if len(cleaned) >= limit:
            break
    return cleaned


def looks_corrupted_keyword_source(cleaned: list[str]) -> bool:
    if len(cleaned) <= MAX_KEYWORD_LIST_SIZE:
        return False
    singles = sum(1 for kw in cleaned if " " not in kw)
    if singles and singles / len(cleaned) >= 0.35:
        return True
    if any(len(kw) > 60 for kw in cleaned):
        return True
    if sum(1 for kw in cleaned if not is_plausible_keyword(kw)) > 0:
        return True
    return False


def compact_corrupted_keywords(keywords: list[str], cleaned: list[str]) -> list[str]:
    if len(cleaned) <= MAX_KEYWORD_LIST_SIZE:
        return cleaned
    if len(keywords or []) <= CORRUPT_KEYWORD_SOURCE_COUNT and not looks_corrupted_keyword_source(cleaned):
        return cleaned[:MAX_KEYWORD_LIST_SIZE]
    if not looks_corrupted_keyword_source(cleaned):
        return cleaned[:MAX_KEYWORD_LIST_SIZE]

    compact = [
        kw
        for kw in cleaned
        if 2 <= len(kw.split()) <= 4 and len(kw) <= 36 and "(" not in kw and is_plausible_keyword(kw)
    ]
    if len(compact) >= 2:
        return compact[:MAX_KEYWORD_LIST_SIZE]
    return []


def sanitize_keyword_list(keywords: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for keyword in keywords or []:
        normalized = normalize_keyword_phrase(str(keyword))
        if not normalized or len(normalized) <= 2:
            continue
        if is_metadata_keyword(normalized):
            continue
        if keyword_looks_like_name_or_citation(normalized):
            continue
        if not is_plausible_keyword(normalized):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    cleaned = drop_reference_name_keywords(cleaned)
    return compact_corrupted_keywords(list(keywords or []), cleaned)


def sanitize_submission_keywords(submission: dict) -> None:
    for field in ("author_keywords", "extracted_keywords", "keywords"):
        submission[field] = sanitize_keyword_list(list(submission.get(field) or []))


YEARS_TOPIC_AREA_KEYWORDS = frozenset({2025})
IGNORED_CONFERENCE_LABELS = frozenset({"view pdf", "view paper pdf", ""})

KEYWORD_SOURCE_NOTE = (
    "Keywords prefer author-supplied fields from poster HTML or proceedings PDFs. "
    "When those are missing, 2025 uses official conference topic areas; 2026 uses "
    "conference topic areas (comma-split at scrape time). "
    "build.py reconcile_submission_keywords strips citation fragments and false positives."
)


def refresh_payload_metadata(payload: dict) -> None:
    """Keep submissions.json metadata aligned with the current pipeline."""
    submissions = payload.get("submissions", [])
    metadata = payload.setdefault("metadata", {})
    metadata["source"] = "https://ccneuro.org archives (2017-2026)"
    metadata["keyword_source"] = KEYWORD_SOURCE_NOTE
    metadata["keyword_years"] = sorted(
        {
            sub["year"]
            for sub in submissions
            if sub.get("year") is not None and sub.get("keywords")
        }
    )
    metadata.pop("csv_2026", None)


def conference_topic_label(submission: dict) -> str | None:
    for raw in (submission.get("topic_area"), submission.get("track")):
        label = re.sub(r"\s+", " ", str(raw or "").strip())
        if not label:
            continue
        if label.lower() in IGNORED_CONFERENCE_LABELS:
            continue
        return label.lower()
    return None


def conference_topic_keywords(submission: dict) -> list[str]:
    """Return official conference track/topic labels as keywords when author keywords are absent."""
    label = conference_topic_label(submission)
    if not label:
        return []
    return [label]


def reconcile_submission_keywords(submission: dict) -> None:
    """Drop scraped prose fragments and keep keywords in sync."""
    sanitize_submission_keywords(submission)
    title = str(submission.get("title") or "")

    author = sanitize_keyword_list(list(submission.get("author_keywords") or []))
    authors_blob = str(submission.get("authors") or "").lower()
    if authors_blob:
        author = [
            kw
            for kw in author
            if not (len(kw.split()) >= 2 and kw in authors_blob and "(" not in kw)
        ]
    if author:
        submission["author_keywords"] = author[:MAX_KEYWORD_LIST_SIZE]
        submission["keywords"] = submission["author_keywords"]
        submission["extracted_keywords"] = []
        return

    if submission.get("year") in YEARS_TOPIC_AREA_KEYWORDS:
        topic_kw = conference_topic_keywords(submission)
        if topic_kw:
            submission["keywords"] = topic_kw
            submission["extracted_keywords"] = []
            return

    extracted = sanitize_keyword_list(list(submission.get("extracted_keywords") or []))
    if extracted and keywords_look_low_quality(extracted, submission):
        extracted = []
        submission["extracted_keywords"] = []
    if extracted and not keywords_are_title_derived(extracted, title):
        submission["keywords"] = extracted[:MAX_KEYWORD_LIST_SIZE]
        return

    keywords = sanitize_keyword_list(list(submission.get("keywords") or []))
    if authors_blob:
        keywords = [
            kw
            for kw in keywords
            if not (len(kw.split()) >= 2 and kw in authors_blob and "(" not in kw)
        ]
    if keywords and keywords_look_low_quality(keywords, submission):
        keywords = []
    if keywords and not keywords_are_title_derived(keywords, title):
        submission["keywords"] = keywords[:MAX_KEYWORD_LIST_SIZE]
        return

    submission["author_keywords"] = []
    submission["extracted_keywords"] = []
    submission["keywords"] = []


def dashboard_keywords(submission: dict) -> list[str]:
    """Keywords for CSV/dashboard display."""
    title = str(submission.get("title") or "")
    reconciled = sanitize_keyword_list(list(submission.get("keywords") or []))
    if reconciled and not keywords_are_title_derived(reconciled, title):
        return reconciled[:MAX_KEYWORD_LIST_SIZE]

    author = sanitize_keyword_list(list(submission.get("author_keywords") or []))
    if author:
        return author[:MAX_KEYWORD_LIST_SIZE]

    if submission.get("year") in YEARS_TOPIC_AREA_KEYWORDS:
        topic_kw = conference_topic_keywords(submission)
        if topic_kw:
            return topic_kw

    extracted = sanitize_keyword_list(list(submission.get("extracted_keywords") or []))
    if extracted and not keywords_are_title_derived(extracted, title):
        return extracted[:MAX_KEYWORD_LIST_SIZE]

    return []


def content_keywords(submission: dict) -> list[str]:
    for field in ("author_keywords", "extracted_keywords", "keywords"):
        values = sanitize_keyword_list(list(submission.get(field) or []))
        if values:
            return values
    return []


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


def vectorizer_stop_words() -> list[str]:
    return sorted(ENGLISH_STOP_WORDS | METADATA_KEYWORD_TOKENS)


def repair_mojibake(text: str) -> str:
    if not text:
        return text

    repaired = text
    for _ in range(3):
        previous = repaired
        for old, new in _MOJIBAKE_REPLACEMENTS:
            if old in repaired:
                repaired = repaired.replace(old, new)
        repaired = _MOJIBAKE_QUOTED_RE.sub(r'"\1"', repaired)
        repaired = re.sub(r"\sâ\s", " — ", repaired)
        for encoding in ("cp1252", "latin-1"):
            try:
                candidate = repaired.encode(encoding).decode("utf-8")
            except (UnicodeDecodeError, UnicodeEncodeError):
                continue
            if candidate != repaired:
                repaired = candidate
        if repaired == previous:
            break

    return repair_accent_marks(sanitize_display_text(repaired))


def repair_submission_text(submission: dict) -> None:
    for field in ("title", "abstract", "topic_area", "track"):
        if field in submission and submission[field]:
            submission[field] = normalize_field_text(str(submission[field]))

    if submission.get("authors"):
        submission["authors"] = normalize_author_names(str(submission["authors"]))

    for field in ("author_keywords", "extracted_keywords", "keywords", "secondary_topics", "assigned_topics"):
        values = submission.get(field)
        if not values:
            continue
        submission[field] = [
            normalize_field_text(str(value))
            for value in values
            if value and normalize_field_text(str(value))
        ]

    if submission.get("primary_theme"):
        submission["primary_theme"] = normalize_field_text(str(submission["primary_theme"]))


def repair_embeddings(embeddings: dict) -> dict:
    for point in embeddings.get("points", []):
        if point.get("title"):
            point["title"] = normalize_field_text(str(point["title"]))
    return embeddings

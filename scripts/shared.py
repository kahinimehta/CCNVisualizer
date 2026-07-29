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
    }
)

BAD_KEYWORD_PREFIXES = (
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
    re.compile(r"[*~`^|\\{}[\]<>#$%@!;:=]"),  # odd symbols (keep + for pv+)
    re.compile(r"[^\w\s\-/&'+]{2,}"),  # runs of odd punctuation/symbols
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
    r"[ÃÄÅÆÇÐÑØÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\u0080-\u009f]"
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


def normalize_keyword_phrase(keyword: str) -> str:
    cleaned = _KEYWORD_INVISIBLE_RE.sub("", keyword or "")
    cleaned = re.sub(r"\s+", " ", cleaned.strip().lower())
    return strip_citation_fragments(cleaned)


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


def normalize_field_text(text: str) -> str:
    if not text:
        return ""
    cleaned = repair_mojibake(str(text))
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
    if re.search(r"[.!?]", normalized):
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
        if not is_plausible_keyword(normalized):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return compact_corrupted_keywords(list(keywords or []), cleaned)


def sanitize_submission_keywords(submission: dict) -> None:
    for field in ("author_keywords", "extracted_keywords", "keywords"):
        submission[field] = sanitize_keyword_list(list(submission.get(field) or []))


YEARS_TOPIC_AREA_KEYWORDS = frozenset({2025})
IGNORED_CONFERENCE_LABELS = frozenset({"view pdf", "view paper pdf", ""})


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
    label = conference_topic_label(submission)
    if not label or is_metadata_keyword(label):
        return []
    if not is_plausible_keyword(label):
        return []
    return [label]


def reconcile_submission_keywords(submission: dict) -> None:
    """Drop scraped prose fragments and keep keywords in sync."""
    sanitize_submission_keywords(submission)

    author = sanitize_keyword_list(list(submission.get("author_keywords") or []))
    if author:
        keywords = author[:MAX_KEYWORD_LIST_SIZE]
        submission["author_keywords"] = keywords
        submission["keywords"] = keywords
        return

    if submission.get("year") in YEARS_TOPIC_AREA_KEYWORDS:
        topic_kw = conference_topic_keywords(submission)
        if topic_kw:
            submission["keywords"] = topic_kw
            submission["extracted_keywords"] = []
            return

    extracted = sanitize_keyword_list(list(submission.get("extracted_keywords") or []))
    if extracted:
        submission["keywords"] = extracted[:MAX_KEYWORD_LIST_SIZE]
        return

    title_kw = derive_title_keywords(str(submission.get("title") or ""))
    if title_kw:
        submission["keywords"] = title_kw
        return

    topic_kw = conference_topic_keywords(submission)
    if topic_kw:
        submission["keywords"] = topic_kw


def dashboard_keywords(submission: dict) -> list[str]:
    """Keywords for CSV/dashboard display; preserves conference topic-area labels."""
    reconciled = [str(kw).strip() for kw in (submission.get("keywords") or []) if str(kw).strip()]
    if reconciled:
        return reconciled[:MAX_KEYWORD_LIST_SIZE]

    author = sanitize_keyword_list(list(submission.get("author_keywords") or []))
    if author:
        return author[:MAX_KEYWORD_LIST_SIZE]

    topic_kw = conference_topic_keywords(submission)
    if topic_kw:
        return topic_kw

    extracted = sanitize_keyword_list(list(submission.get("extracted_keywords") or []))
    if extracted:
        return extracted[:MAX_KEYWORD_LIST_SIZE]

    return derive_title_keywords(str(submission.get("title") or ""))


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
    if not text or not _MOJIBAKE_MARKERS.search(text):
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


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
        submission[field] = [repair_mojibake(str(value)) for value in values if value]

    if submission.get("primary_theme"):
        submission["primary_theme"] = repair_mojibake(str(submission["primary_theme"]))

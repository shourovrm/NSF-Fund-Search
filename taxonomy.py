"""Category definitions for NSF awards: research field, topics, and grant type.

Field comes from NSF's own division, so every award has exactly one.
Topics are keyword matches, so an award can have several, or none ("other").
Grant type is one label per award, chosen by the priority order in GRANT_TYPES.
"""

import re

# ---------------------------------------------------------------------------
# Field: NSF division -> broad research field
# ---------------------------------------------------------------------------

FIELDS = {
    "computing": "Computer & Information Science",
    "electrical": "Electrical & Computer Engineering",
    "engineering": "Other Engineering",
    "math": "Mathematics & Statistics",
    "physics_astronomy": "Physics & Astronomy",
    "chemistry_materials": "Chemistry & Materials",
    "earth_environment": "Earth, Ocean & Climate",
    "biology": "Biology",
    "social_behavioral": "Social & Behavioral Sciences",
    "other": "Other / Cross-cutting",
}

FIELD_BY_DIVISION = {
    "CCF": "computing", "CNS": "computing", "IIS": "computing", "OAC": "computing",
    "ECCS": "electrical",
    "CBET": "engineering", "CMMI": "engineering", "EEC": "engineering", "EFMA": "engineering",
    "DMS": "math",
    "PHY": "physics_astronomy", "AST": "physics_astronomy",
    "CHE": "chemistry_materials", "DMR": "chemistry_materials",
    "EAR": "earth_environment", "OCE": "earth_environment", "AGS": "earth_environment",
    "RISE": "earth_environment", "OPP": "earth_environment",
    "DEB": "biology", "MCB": "biology", "IOS": "biology", "DBI": "biology", "EF": "biology",
    "BCS": "social_behavioral", "SES": "social_behavioral", "SMA": "social_behavioral",
    "NCSE": "social_behavioral",
}


def field_of(award):
    return FIELD_BY_DIVISION.get(award.get("div_abbr"), "other")


# ---------------------------------------------------------------------------
# Topics: keyword and NSF-program matching
# ---------------------------------------------------------------------------

# Scoring: a keyword in the title counts 3, a relevant NSF program counts 2,
# each distinct keyword in the abstract counts 1. An award joins a topic at
# score >= 3, so a single abstract mention is never enough on its own.
TITLE_WEIGHT = 3
PROGRAM_WEIGHT = 2
ABSTRACT_WEIGHT = 1
TOPIC_THRESHOLD = 3

OTHER_TOPIC = "other"

TOPICS = {
    # --- Computing and electrical engineering ---
    "ai_software": {
        "label": "AI, NLP & Software",
        "group": "Computing & EE",
        "programs": {"749500", "736400", "779800", "175Y00", "094Y00", "306Y00", "132Y00", "296Y00", "341Y00", "127Y00"},
        "keywords": [
            r"machine learning", r"deep learning", r"neural network\w*",
            r"artificial intelligence|\bAI\b", r"natural language|\bNLP\b",
            r"language models?|\bLLMs?\b", r"\btransformers?\b",
            r"reinforcement learning", r"generative (AI|model\w*)",
            r"foundation models?", r"computer vision", r"federated learning",
            r"software engineering", r"program synthesis", r"program analysis",
            r"software (testing|verification|systems?|development|maintenance)",
            r"code generation", r"\bcompilers?\b",
        ],
    },
    "security": {
        "label": "Security & Privacy",
        "group": "Computing & EE",
        "programs": {"806000", "802700", "318Y00", "329Y00"},
        "keywords": [
            r"cyber[- ]?security", r"cyber[- ]?attacks?",
            r"(hardware|software|network|system|information|computer|data|IoT|"
            r"embedded|chip|memory|supply[- ]chain|grid|AI|ML) security",
            r"security of", r"privacy", r"cryptograph\w*", r"side[- ]channel\w*",
            r"malware", r"intrusion", r"hardware trojans?", r"adversarial (attacks?|examples?)",
            r"(software|security|system|zero[- ]day) vulnerabilit\w*", r"\bfuzz(ing|er)\b",
            r"zero[- ]trust", r"post[- ]quantum",
            r"trusted execution", r"secure (computing|systems?|hardware|communication\w*)",
        ],
    },
    "power_grid": {
        "label": "Power Systems & Grid",
        "group": "Computing & EE",
        "programs": {"045Y00"},
        "keywords": [
            r"power (systems?|grids?|flow|distribution|transmission|electronics?)",
            r"electric(al|ity)? grids?", r"smart grids?", r"microgrids?",
            r"grid[- ](forming|following|resilience|operations?|integration|edge|scale)",
            r"inverter[- ]based", r"distributed energy resources?|(?-i:\bDERs?\b)",
            r"renewable (energy )?integration", r"electricity markets?",
            r"demand response", r"unit commitment", r"load forecasting",
            r"grid[- ]scale (energy )?storage", r"(power|electric\w*) transmission",
            r"(power|electric\w*|energy) distribution", r"power plants?",
        ],
    },
    "quantum": {
        "label": "Quantum",
        "group": "Computing & EE",
        "programs": {"728100", "105Y00", "315Y00"},
        "keywords": [
            r"quantum comput\w*", r"quantum information", r"quantum algorithms?",
            r"\bqubits?\b", r"quantum network\w*", r"quantum error[- ]correct\w*",
            r"quantum sens\w*", r"quantum software", r"quantum circuits?",
            r"quantum simulat\w*", r"quantum machine learning", r"quantum internet",
            r"quantum (hardware|processors?|devices?)", r"entanglement",
            r"post[- ]quantum", r"quantum cryptograph\w*", r"quantum key distribution",
        ],
    },
    "robotics": {
        "label": "Robotics & Autonomy",
        "group": "Computing & EE",
        "programs": {"144Y00"},
        "keywords": [
            r"\brobot\w*", r"autonomous (vehicles?|systems?|robots?|driving|agents?)",
            r"\bdrones?\b|\bUAVs?\b|unmanned aerial", r"\bmanipulat(ion|ors?)\b",
            r"legged locomotion", r"human[- ]robot", r"motion planning", r"\bexoskeleton\w*",
        ],
    },
    "networking": {
        "label": "Networking & Wireless",
        "group": "Computing & EE",
        "programs": {"736300", "140Y00", "151Y00"},
        "keywords": [
            r"\bwireless\b", r"\b(5G|6G|NextG)\b", r"network(ing)? protocols?", r"\bspectrum (sharing|access|management)\b",
            r"\binternet\b(?! of things)", r"edge computing", r"mm[Ww]ave|millimeter[- ]wave",
            r"communication networks?", r"satellite communication\w*", r"software[- ]defined network\w*",
            r"network (measurement|security|systems?|architecture)",
        ],
    },
    "chips_architecture": {
        "label": "Chips & Computer Architecture",
        "group": "Computing & EE",
        "programs": {"241Y00", "294Y00"},
        "keywords": [
            r"computer architecture", r"\bprocessors?\b", r"semiconductor\w*", r"integrated circuits?",
            r"\bVLSI\b", r"\bFPGAs?\b", r"\bchips?\b|chiplets?", r"hardware accelerat\w*",
            r"memory systems?", r"\bCMOS\b", r"analog (circuits?|design)", r"electronic design automation|\bEDA\b",
            r"neuromorphic",
        ],
    },
    "data_hpc": {
        "label": "Data Science & HPC",
        "group": "Computing & EE",
        "programs": {"800400", "761900", "772600", "090Y00"},
        "keywords": [
            r"high[- ]performance computing|\bHPC\b", r"supercomput\w*", r"cyberinfrastructure",
            r"data science", r"big data", r"scientific computing", r"parallel (computing|algorithms?)",
            r"cloud computing", r"data management", r"\bdatabases?\b", r"exascale",
        ],
    },
    "control_cps": {
        "label": "Control & Cyber-Physical Systems",
        "group": "Computing & EE",
        "programs": {"791800", "760700", "756900"},
        "keywords": [
            r"control (systems?|theory)", r"cyber[- ]physical", r"(?-i:\bCPS\b)",
            r"internet of things|(?-i:\bIoT\b)", r"embedded systems?", r"digital twins?",
            r"sensor networks?", r"optimal control", r"model predictive control", r"feedback control",
        ],
    },
    # --- Other sectors ---
    "biomedical_health": {
        "label": "Biomedical & Health",
        "group": "Other sectors",
        "programs": {"801800", "534500", "534200"},
        "keywords": [
            r"biomedical", r"\bmedical\b", r"(human|public|mental) health|health ?care", r"\bclinical\b",
            r"\bpatients?\b", r"\bdiseases?\b", r"\bcancer\w*", r"drug (delivery|discovery|design)",
            r"therapeut\w*", r"medical imaging", r"\bwearables?\b", r"\bvaccines?\b",
            r"tissue engineering", r"\bbiomaterials?\b", r"\bsurg(ery|ical)\b",
        ],
    },
    "neuroscience_cognition": {
        "label": "Neuroscience & Cognition",
        "group": "Other sectors",
        "programs": {"732700", "862400"},
        "keywords": [
            r"neuroscience", r"\bbrains?\b", r"\bneurons?\b|neuronal", r"\bcogniti(on|ve)\b",
            r"neural (circuits?|activity|coding|dynamics)", r"neuroimaging", r"\bperception\b",
            r"\blanguage acquisition\b", r"decision[- ]making",
        ],
    },
    "climate_environment": {
        "label": "Climate, Environment & Water",
        "group": "Other sectors",
        "programs": set(),
        "keywords": [
            r"\bclimate\b", r"environmental (science|impacts?|monitoring|justice|change)", r"sustainab\w*",
            r"(natural|marine|coastal|forest|freshwater|aquatic|terrestrial|polar|river|wetland) ecosystems?|ecosystem (services|ecology|dynamics|function\w*)", r"carbon (capture|dioxide|cycle|emissions|sequestration)", r"\bpollut\w*",
            r"water (quality|resources|supply|treatment)|hydrolog\w*", r"wildfires?", r"biodiversity",
            r"\boceans?\b|oceanograph\w*", r"atmospher\w*", r"extreme weather", r"\bdroughts?\b", r"\bflood\w*",
        ],
    },
    "energy_cleantech": {
        "label": "Energy & Clean Tech",
        "group": "Other sectors",
        "programs": set(),
        "keywords": [
            r"\bbatter(y|ies)\b", r"\bsolar\b", r"photovoltaic\w*", r"\bhydrogen\b", r"fuel cells?",
            r"electrocataly\w*", r"energy (storage|conversion|harvesting|efficiency)", r"wind (energy|turbines?)",
            r"fusion energy", r"(renewable|clean) energy", r"decarboni[sz]\w*",
        ],
    },
    "agriculture_food": {
        "label": "Agriculture & Food",
        "group": "Other sectors",
        "programs": set(),
        "keywords": [
            r"agricultur\w*", r"\bcrops?\b", r"\bfarm\w*", r"\bfood\b", r"\bsoils?\b",
            r"plant (breeding|pathogens?|growth|disease)", r"livestock", r"irrigation", r"precision agriculture",
        ],
    },
    "manufacturing_materials": {
        "label": "Manufacturing & Materials",
        "group": "Other sectors",
        "programs": {"088Y00", "229Y00", "142Y00", "829200"},
        "keywords": [
            r"manufactur\w*", r"additive manufacturing|3D printing", r"materials (science|design|discovery)",
            r"\bpolymers?\b", r"\bcomposites?\b", r"\balloys?\b", r"metamaterials?", r"nanomaterials?",
            r"thin films?", r"\bceramics?\b",
        ],
    },
    "transportation_infrastructure": {
        "label": "Transportation & Infrastructure",
        "group": "Other sectors",
        "programs": {"073Y00", "163100", "342Y00"},
        "keywords": [
            r"transportation", r"\btraffic\b", r"\bvehicles?\b", r"autonomous driving", r"smart cit(y|ies)",
            r"civil infrastructure", r"\bbridges?\b", r"\bbuildings\b|building (energy|design|structures?|codes?|envelopes?)", r"\bpavements?\b",
            r"urban (mobility|systems|infrastructure)", r"\brail(way)?s?\b", r"\baviation\b",
        ],
    },
    "space_astronomy": {
        "label": "Space & Astronomy",
        "group": "Other sectors",
        "programs": {"107Y00", "808900"},
        "keywords": [
            r"astronom\w*", r"astrophysic\w*", r"\bgalax(y|ies)\b", r"\bstellar\b", r"exoplanet\w*",
            r"\bplanetary\b", r"cosmolog\w*", r"\btelescopes?\b", r"black holes?", r"gravitational waves?",
            r"space weather", r"solar wind", r"\bsatellites?\b",
        ],
    },
}

TOPIC_LABELS = {key: topic["label"] for key, topic in TOPICS.items()} | {OTHER_TOPIC: "Other topics"}
TOPIC_GROUPS = {key: topic["group"] for key, topic in TOPICS.items()} | {OTHER_TOPIC: "Other"}

_COMPILED_KEYWORDS = {
    key: [re.compile(pattern, re.IGNORECASE) for pattern in topic["keywords"]]
    for key, topic in TOPICS.items()
}


def program_codes_of(award):
    return {program["pgm_ele_code"].upper() for program in award.get("pgm_ele") or []}


def score_topic(award, topic_key):
    """Return (score, reasons) for one award against one topic.

    Reasons read like 'title:machine learning', 'abstract:qubits', 'program:806000'.
    """
    title = award.get("awd_titl_txt") or ""
    abstract = award.get("awd_abstract_narration") or ""
    score = 0
    reasons = []
    for pattern in _COMPILED_KEYWORDS[topic_key]:
        title_match = pattern.search(title)
        if title_match:
            score += TITLE_WEIGHT
            reasons.append(f"title:{title_match.group(0)}")
            continue
        abstract_match = pattern.search(abstract)
        if abstract_match:
            score += ABSTRACT_WEIGHT
            reasons.append(f"abstract:{abstract_match.group(0)}")
    matched_programs = program_codes_of(award) & TOPICS[topic_key]["programs"]
    if matched_programs:
        score += PROGRAM_WEIGHT
        reasons.append("program:" + ",".join(sorted(matched_programs)))
    return score, reasons


def match_topics(award):
    """Return {topic_key: {"score", "reasons"}}; an award with no topic gets OTHER_TOPIC."""
    matches = {}
    for topic_key in TOPICS:
        score, reasons = score_topic(award, topic_key)
        if score >= TOPIC_THRESHOLD:
            matches[topic_key] = {"score": score, "reasons": reasons}
    if not matches:
        matches[OTHER_TOPIC] = {"score": 0, "reasons": []}
    return matches


# ---------------------------------------------------------------------------
# Grant type: one label per award
# ---------------------------------------------------------------------------

# Checked top to bottom; the first rule that matches wins.
GRANT_TYPES = {
    "career": "CAREER",
    "starter": "New-faculty starter",
    "center": "Center / Institute",
    "exploratory": "Exploratory (EAGER / RAPID)",
    "training": "Training",
    "infrastructure": "Infrastructure & Software",
    "industry": "Industry & Translation",
    "standard": "Standard research",
}

STARTER_PREFIXES = {"CRII", "ERI", "Research Initiation", "LEAPS-MPS", "BRC-BIO", "E-CORE RII"}
STARTER_PROGRAMS = {"026Y00", "180Y00"}
CENTER_PREFIXES = {"Center", "Institute", "Frontier", "STC", "ERC", "MRSEC", "NSF Engines", "Engines"}
CENTER_MIN_AMOUNT = 5_000_000
EXPLORATORY_PREFIXES = {"EAGER", "RAPID"}
TRAINING_PREFIXES = {"NRT", "CyberTraining", "IRES", "CyberAI SFS", "CyberAI Innovation", "Research Traineeship"}
INFRASTRUCTURE_PREFIXES = {"Elements", "Frameworks", "Research Infrastructure", "CCRI", "CC*", "Disciplinary Improvements", "MRI"}
INFRASTRUCTURE_PROGRAMS = {"735900", "808000", "289000", "800400"}
INDUSTRY_PREFIXES = {"GOALI", "POSE", "PFI", "IUCRC", "Phase I", "Phase II"}

UNDERGRADUATE_INSTITUTION_REFERENCE = "9229"  # NSF program reference "RES IN UNDERGRAD INST-RESEARCH"


def title_prefixes(title):
    """Leading 'PREFIX:' segments of an NSF title, e.g. ['Collaborative Research', 'SaTC', 'CORE']."""
    segments = [segment.strip() for segment in title.split(":")[:-1]]
    return [segment for segment in segments if 0 < len(segment) <= 40]


def grant_type_of(award):
    title = award.get("awd_titl_txt") or ""
    prefixes = set(title_prefixes(title))
    programs = program_codes_of(award)
    amount = award.get("tot_intn_awd_amt") or 0
    if "CAREER" in prefixes:
        return "career"
    if prefixes & STARTER_PREFIXES or programs & STARTER_PROGRAMS:
        return "starter"
    if prefixes & CENTER_PREFIXES or amount >= CENTER_MIN_AMOUNT:
        return "center"
    if prefixes & EXPLORATORY_PREFIXES:
        return "exploratory"
    if prefixes & TRAINING_PREFIXES or award.get("div_abbr") == "DGE":
        return "training"
    if prefixes & INFRASTRUCTURE_PREFIXES or programs & INFRASTRUCTURE_PROGRAMS:
        return "infrastructure"
    if prefixes & INDUSTRY_PREFIXES or award.get("dir_abbr") == "TIP":
        return "industry"
    return "standard"


def is_collaborative(award):
    return "Collaborative Research" in title_prefixes(award.get("awd_titl_txt") or "")


def is_undergraduate_institution(award):
    """RUI awards go to primarily undergraduate colleges, which rarely host PhD students."""
    if "RUI" in title_prefixes(award.get("awd_titl_txt") or ""):
        return True
    return any(reference["pgm_ref_code"] == UNDERGRADUATE_INSTITUTION_REFERENCE for reference in award.get("pgm_ref") or [])


# ---------------------------------------------------------------------------
# PhD funding likelihood: how likely a grant is to pay a PhD research assistant
# ---------------------------------------------------------------------------

PHD_LIKELIHOOD = {
    "likely": "Likely funds PhD",
    "possible": "May fund PhD",
    "unlikely": "Unlikely to fund PhD",
}
_LIKELIHOOD_ORDER = ["likely", "possible", "unlikely"]

# Why each grant type lands where it does; shown to the user as the reason.
PHD_LIKELIHOOD_BY_GRANT_TYPE = {
    "career": ("likely", "CAREER budgets usually support a PhD student for five years"),
    "standard": ("likely", "core research grants usually budget graduate research assistants"),
    "starter": ("likely", "new faculty use starter grants to hire their first student, but they last about two years"),
    "exploratory": ("possible", "EAGER/RAPID grants are small and short, often one or two years"),
    "center": ("possible", "centers fund many students, but hiring goes through the center"),
    "infrastructure": ("possible", "infrastructure and software grants mostly pay engineers and staff"),
    "training": ("unlikely", "traineeship stipends (NRT, SFS) are mostly limited to US citizens and permanent residents"),
    "industry": ("unlikely", "industry and translation grants mostly pay staff, partners and startups"),
}

# Rough yearly cost of one PhD research assistant (stipend, tuition, fringe) at a
# US university. Below this a grant can rarely carry a full assistantship.
MIN_YEARLY_BUDGET_FOR_ONE_STUDENT = 70_000
_DAYS_PER_YEAR = 365.25


def yearly_budget(award):
    start = award.get("awd_eff_date")
    end = award.get("awd_exp_date")
    amount = award.get("tot_intn_awd_amt") or 0
    if not start or not end:
        return None
    from datetime import date
    years = (date.fromisoformat(end) - date.fromisoformat(start)).days / _DAYS_PER_YEAR
    return amount / years if years > 0 else None


def phd_likelihood_of(award):
    """Return (likelihood key, reason) for one award."""
    grant_type = grant_type_of(award)
    likelihood, reason = PHD_LIKELIHOOD_BY_GRANT_TYPE[grant_type]
    budget = yearly_budget(award)
    # CAREER has a fixed minimum size, so a low yearly figure there is a data quirk.
    if budget is not None and budget < MIN_YEARLY_BUDGET_FOR_ONE_STUDENT and grant_type != "career":
        downgraded_index = min(_LIKELIHOOD_ORDER.index(likelihood) + 1, len(_LIKELIHOOD_ORDER) - 1)
        likelihood = _LIKELIHOOD_ORDER[downgraded_index]
        reason = f"about ${budget / 1000:.0f}K a year, too little for a full research assistantship"
    return likelihood, reason

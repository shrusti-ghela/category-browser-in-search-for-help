from __future__ import annotations

import ast
import json
import re
import random
import html
import markdown
from pathlib import Path
from zoneinfo import ZoneInfo

import pycountry
import pytz
import pandas as pd
import streamlit as st
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder


st.set_page_config(
    page_title="Help-Seeking Conversation Browser",
    page_icon="🌿",
    layout="wide",
)

# DEFAULT_RESULTS_JSONL = (
#     Path("/Users/shrustighela/diLLeMas/notebooks")
#     / "outputs"
#     / "v2"
#     / "in_scope_exports"
#     / "vz_labeling_full_first_user"
#     / "binary10_full"
#     / "first_user_full_labels.jsonl"
# )

# DEFAULT_FULL_CONVERSATIONS_FILE = (
#     Path("/Users/shrustighela/diLLeMas/notebooks")
#     / "outputs"
#     / "v2"
#     / "in_scope_exports"
#     / "in_scope_full_conversations_sorted.jsonl"
# )

DEFAULT_RESULTS_JSONL = Path("data/first_user_full_labels.jsonl")
DEFAULT_FULL_CONVERSATIONS_FILE = Path("data/in_scope_full_conversations_sorted.jsonl.gz")
MERGE_KEY = "conversation_hash"

FULL_CONVERSATION_CANDIDATE_COLUMNS = [
    "conversation",
    "full_conversation",
    "messages",
    "turns",
    "chat",
    "dialogue",
    "history",
    "conversation_text",
    "full_text",
]

TEXT_FALLBACK_COLUMNS = ["first_user_text", "first_user"]

METADATA_COLUMNS = ["timestamp", "model", "country", "state", "language"]

CATEGORY_ORDER = [
    "RELATIONAL_PROBLEMS",
    "EDUCATIONAL_OCCUPATIONAL_PROBLEMS",
    "HOUSING_ECONOMIC_PROBLEMS",
    "SOCIAL_ENVIRONMENT_PROBLEMS",
    "LEGAL_CRIME_PROBLEMS",
    "HEALTH_SERVICE_ENCOUNTERS",
    "OTHER_PSYCHOSOCIAL_ENVIRONMENTAL_PROBLEMS",
    "PERSONAL_HISTORY",
    "ABUSE_NEGLECT",
    "GENERAL_LIFE_HELP_SEEKING",
]

CATEGORY_DISPLAY_NAMES = {
    "RELATIONAL_PROBLEMS": "Relational Problems",
    "EDUCATIONAL_OCCUPATIONAL_PROBLEMS": "Educational and Occupational Problems",
    "HOUSING_ECONOMIC_PROBLEMS": "Housing and Economic Problems",
    "SOCIAL_ENVIRONMENT_PROBLEMS": "Problems Related to the Social Environment",
    "LEGAL_CRIME_PROBLEMS": "Problems Related to Crime or Interaction With the Legal System",
    "HEALTH_SERVICE_ENCOUNTERS": "Health Service Encounters",
    "OTHER_PSYCHOSOCIAL_ENVIRONMENTAL_PROBLEMS": "Problems Related to Other Psychosocial, Personal, and Environmental Circumstances",
    "PERSONAL_HISTORY": "Circumstances of Personal History",
    "ABUSE_NEGLECT": "Abuse and Neglect",
    "GENERAL_LIFE_HELP_SEEKING": "General life Help-Seeking",
}

CATEGORY_SPECS = {
    "RELATIONAL_PROBLEMS": {
        "definition": "The user's message is about a real close relationship in their life, such as a romantic relationship, dating, breakup, marriage, family conflict, parenting relationship, emotionally significant friendship, betrayal, rejection, attachment, loneliness tied to a person, or confusion about another person's behavior.",
        "examples_yes": [
            "My boyfriend barely talks to me anymore and I keep overthinking whether he still wants this relationship.",
            "I had a huge fight with my mom and now I don't know how to talk to her.",
            "My best friend has been pulling away and I feel hurt and confused.",
            "I still can't get over my ex and I hate that I keep checking their social media.",
        ],
        "examples_no": [
            "Can you write a breakup scene between two fictional characters?",
            "What are signs of a healthy relationship?",
            "Rewrite this text to sound nicer.",
        ],
    },
    "EDUCATIONAL_OCCUPATIONAL_PROBLEMS": {
        "definition": "The user's message is about their real situation involving school, college, studying, grades, exams, work, career, productivity, burnout, job dissatisfaction, work stress, unemployment, workplace conflict, or career uncertainty.",
        "examples_yes": [
            "I'm so behind in school that I feel sick every time I open my laptop.",
            "My job is exhausting me and I keep fantasizing about quitting.",
            "I think I chose the wrong career and now I feel trapped.",
            "My boss keeps criticizing everything I do and it's making me dread going to work.",
        ],
        "examples_no": [
            "What are the highest paying careers in data science?",
            "Can you summarize this job description?",
            "Write a cover letter for me.",
        ],
    },
    "HOUSING_ECONOMIC_PROBLEMS": {
        "definition": "The user's message is about real financial or housing hardship, including money stress, debt, bills, rent, affordability, poverty, housing instability, unsafe living situation, or inability to meet basic needs.",
        "examples_yes": [
            "I can barely pay rent this month and I'm panicking.",
            "I'm drowning in debt and every time I check my bank account I feel hopeless.",
            "I hate living where I am but I can't afford to move.",
            "I keep skipping meals to make my money last.",
        ],
        "examples_no": [
            "What is a good monthly budget template?",
            "Can you compare two neighborhoods for me?",
            "Rewrite my email to the landlord.",
        ],
    },
    "SOCIAL_ENVIRONMENT_PROBLEMS": {
        "definition": "The user's message is about their broader social environment rather than one close relationship, such as isolation, lack of belonging, peer rejection, bullying, discrimination, alienation, social exclusion, community stress, or difficulty fitting in.",
        "examples_yes": [
            "I feel like I don't belong anywhere and even when I'm around people I still feel invisible.",
            "People at school keep making fun of me and I don't know how much longer I can handle it.",
            "Ever since I moved here I've felt completely out of place and lonely.",
            "I feel judged all the time for how I look and it's making me avoid people.",
        ],
        "examples_no": [
            "My boyfriend ignored my text all day and I'm upset.",
            "What is social anxiety?",
            "Write a speech about bullying awareness.",
        ],
    },
    "LEGAL_CRIME_PROBLEMS": {
        "definition": "The user's message is about a real legal or crime-related issue, such as court, police, charges, arrest, fraud, custody disputes, legal risk, or being affected by crime.",
        "examples_yes": [
            "I got served papers today and I have no idea what I'm supposed to do next.",
            "Someone stole money from me and I don't know whether to go to the police.",
            "I'm terrified because I might get arrested over this mistake.",
            "My ex is threatening a custody fight and I feel completely lost.",
        ],
        "examples_no": [
            "What does a restraining order mean?",
            "Summarize this legal article.",
            "Write a courtroom scene for a novel.",
        ],
    },
    "HEALTH_SERVICE_ENCOUNTERS": {
        "definition": "The user's message is about seeking, accessing, navigating, or interacting with formal support services such as therapy, counseling, psychiatry, medical care, healthcare providers, or support systems.",
        "examples_yes": [
            "I've been thinking about therapy for months but I feel overwhelmed trying to find someone I can afford.",
            "My therapist said something that made me shut down and now I don't know whether to go back.",
            "I know I need help but every time I try to make a doctor's appointment I freeze.",
            "I finally got on a waitlist for counseling but I don't know how to cope while I'm waiting.",
        ],
        "examples_no": [
            "What does a psychiatrist do?",
            "Can you rewrite my message canceling a doctor's appointment?",
            "Explain CBT in simple words.",
        ],
    },
    "OTHER_PSYCHOSOCIAL_ENVIRONMENTAL_PROBLEMS": {
        "definition": "The user's message reflects a real personal struggle, life stressor, confusion, emotional burden, or difficult situation that is meaningful and real, and may relate to circumstances that do not fit the other categories well.",
        "examples_yes": [
            "I feel completely stuck in life and I don't even know what direction I'm moving in anymore.",
            "Everything in my life looks fine on paper, but inside I feel lost and disconnected from myself.",
            "I'm overwhelmed by everything happening at once and I can't tell what I should deal with first.",
            "I feel like I'm not functioning like a normal person lately.",
        ],
        "examples_no": [
            "What are common signs of an existential crisis?",
            "Write a monologue about feeling lost in life.",
            "Can you summarize this self-help article?",
        ],
    },
    "PERSONAL_HISTORY": {
        "definition": "The user's message meaningfully uses past experiences, trauma, upbringing, earlier patterns, or personal history to explain or understand the current problem. The history is an important part of the present struggle, not just a passing detail.",
        "examples_yes": [
            "I think the way my parents treated me growing up is why I panic whenever someone gets angry with me.",
            "I've been in so many unhealthy relationships that I don't trust my own judgment anymore.",
            "Things that happened to me as a kid still affect how I react to people now.",
            "I used to hurt myself when I was younger and lately I've been scared by how familiar those thoughts feel.",
        ],
        "examples_no": [
            "Can you help me write a childhood backstory for a character?",
            "What are common effects of trauma?",
            "Rewrite this paragraph about my past.",
        ],
    },
    "ABUSE_NEGLECT": {
        "definition": "The user's message involves real-life abuse, coercion, neglect, unsafe dynamics, controlling behavior, intimidation, exploitation, or fear of harm in a relationship, family, or environment.",
        "examples_yes": [
            "My partner keeps controlling who I talk to and then tells me I'm crazy for thinking it's a problem.",
            "I'm scared of how angry my dad gets and I never know when he'll snap.",
            "He says it's my fault when he screams at me and breaks things, and I don't know if this counts as abuse.",
            "I don't feel safe at home, but I also feel guilty even saying that out loud.",
        ],
        "examples_no": [
            "What are signs of emotional abuse?",
            "Write a PSA script about domestic violence.",
            "My friend was rude to me yesterday and now I'm annoyed.",
        ],
    },
    "GENERAL_LIFE_HELP_SEEKING": {
        "definition": "The user's message is clearly about a real personal life question, dilemma, struggle, uncertainty, distress, confusion, decision, or request for support/advice, but it does not fit well into the narrower categories above. This is a broad catch-all in-scope category for genuine help-seeking and support-seeking messages.",
        "examples_yes": [
            "I don't know what I'm doing with my life anymore and I just want someone to help me think clearly.",
            "Why do I keep sabotaging good things for myself?",
            "I feel off lately and I can't tell whether I'm overreacting or something is actually wrong.",
            "I have a big life decision to make and I genuinely don't know how to think through it.",
        ],
        "examples_no": [
            "Write a philosophical dialogue about the meaning of life.",
            "What is the best life advice you've ever heard?",
            "Rewrite this paragraph to sound more reflective.",
        ],
    },
}

CATEGORY_COLORS = {
    "RELATIONAL_PROBLEMS": ("#fff7ed", "#9a3412", "#fb923c"),
    "EDUCATIONAL_OCCUPATIONAL_PROBLEMS": ("#ecfeff", "#155e75", "#22d3ee"),
    "HOUSING_ECONOMIC_PROBLEMS": ("#f0fdf4", "#166534", "#4ade80"),
    "SOCIAL_ENVIRONMENT_PROBLEMS": ("#f5f3ff", "#5b21b6", "#a78bfa"),
    "LEGAL_CRIME_PROBLEMS": ("#fff1f2", "#991b1b", "#fb7185"),
    "HEALTH_SERVICE_ENCOUNTERS": ("#f0fdfa", "#115e59", "#2dd4bf"),
    "OTHER_PSYCHOSOCIAL_ENVIRONMENTAL_PROBLEMS": ("#fff7ed", "#c2410c", "#fdba74"),
    "PERSONAL_HISTORY": ("#eef2ff", "#3730a3", "#818cf8"),
    "ABUSE_NEGLECT": ("#fdf2f8", "#9d174d", "#f472b6"),
    "GENERAL_LIFE_HELP_SEEKING": ("#f8fafc", "#475569", "#94a3b8"),
}

GLOBAL_SYSTEM_TEMPLATE = """
You are a careful binary classifier for first-user messages in a dataset of real-world support, advice-seeking, emotional reflection, and companionship-style use.

Users often come to AI for:
- emotional support
- interpersonal advice
- help making decisions
- making sense of a real situation in their own life
- reflection on distress, confusion, or everyday struggles

Your task:
Decide whether the first user message belongs to ONE target category.

Important principles:
- Prefer YES when the user is clearly describing a real personal situation that reasonably fits the target category.
- Do not require crisis-level severity.
- Everyday struggles, confusion, distress, dilemmas, uncertainty, and advice-seeking count.
- A message can still count even if it is subtle, informal, or not highly emotional.
- Judge the user's lived situation, not just keywords.

OUT_OF_SCOPE should be used only when the message is clearly not part of the study:
- fictional writing
- roleplay
- scene generation
- story continuation
- creative writing
- rewriting, editing, summarization, formatting, translation, or stylistic transformation
- generic factual or informational question with no personal stake
- abstract discussion or opinion with no real personal situation

Decision rule:
- Return YES if the target category is a reasonable and grounded fit for the user's real situation.
- Return NO only if it clearly does not fit, or if the message is clearly excluded above.
- Do not be overly strict.

TARGET CATEGORY: {category_name}

CATEGORY DEFINITION:
{definition}

POSITIVE EXAMPLES:
{positive_examples}

NEGATIVE EXAMPLES:
{negative_examples}

Output STRICT JSON only:
{{
  "answer": "YES" or "NO",
  "reason": "<one short sentence>"
}}
""".strip()


CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at 8% 8%, rgba(251, 146, 60, 0.24), transparent 30%),
        radial-gradient(circle at 90% 10%, rgba(167, 139, 250, 0.24), transparent 28%),
        radial-gradient(circle at 50% 95%, rgba(45, 212, 191, 0.16), transparent 32%),
        linear-gradient(135deg, #fffaf4 0%, #f8fafc 45%, #f5f3ff 100%);
}

.block-container {
    max-width: 1320px;
    padding-top: 2rem;
    padding-bottom: 5rem;
}

[data-testid="stHeader"] {
    background: transparent;
}

.hero {
    padding: 34px 38px;
    border-radius: 34px;
    background: rgba(255, 255, 255, 0.70);
    border: 1px solid rgba(15, 23, 42, 0.08);
    box-shadow: 0 30px 90px rgba(15, 23, 42, 0.10);
    backdrop-filter: blur(20px);
    margin-bottom: 22px;
}

.eyebrow {
    display: inline-flex;
    padding: 8px 13px;
    border-radius: 999px;
    background: rgba(255,255,255,0.82);
    border: 1px solid rgba(15,23,42,0.08);
    color: #64748b;
    font-size: 0.76rem;
    font-weight: 850;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.hero-title {
    margin-top: 18px;
    font-size: 3.15rem;
    line-height: 1.02;
    letter-spacing: -0.075em;
    font-weight: 900;
    color: #0f172a;
}

.hero-subtitle {
    margin-top: 14px;
    max-width: 840px;
    font-size: 1.05rem;
    line-height: 1.7;
    color: #475569;
}

.stat-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 22px;
}

.stat-pill {
    padding: 10px 14px;
    border-radius: 999px;
    background: rgba(248,250,252,0.86);
    border: 1px solid rgba(15,23,42,0.07);
    color: #334155;
    font-size: 0.85rem;
    font-weight: 700;
}

.control-card {
    padding: 20px 22px;
    border-radius: 28px;
    background: rgba(255,255,255,0.66);
    border: 1px solid rgba(15,23,42,0.075);
    box-shadow: 0 18px 50px rgba(15,23,42,0.065);
    margin-bottom: 24px;
    backdrop-filter: blur(16px);
}

.reader-card {
    padding: 28px;
    border-radius: 34px;
    background: rgba(255,255,255,0.74);
    border: 1px solid rgba(15,23,42,0.08);
    box-shadow: 0 26px 70px rgba(15,23,42,0.085);
    backdrop-filter: blur(18px);
}

.reader-title {
    font-size: 1.45rem;
    font-weight: 850;
    letter-spacing: -0.04em;
    color: #0f172a;
    margin-bottom: 5px;
}

.reader-subtitle {
    color: #64748b;
    font-size: 0.94rem;
    line-height: 1.55;
    margin-bottom: 18px;
}

.lens-card {
    padding: 17px 19px;
    border-radius: 24px;
    border: 1px solid rgba(15,23,42,0.06);
    margin-bottom: 16px;
}

.lens-label {
    font-size: 0.72rem;
    font-weight: 850;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 5px;
}

.lens-text {
    color: #334155;
    line-height: 1.58;
    font-size: 0.94rem;
}

.chip {
    display: inline-block;
    padding: 8px 13px;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 800;
    margin: 3px 5px 3px 0;
    border: 1px solid rgba(15,23,42,0.06);
}

.chips {
    margin-bottom: 16px;
}

.random-note {
    color: #64748b;
    font-size: 0.84rem;
    margin-bottom: 12px;
}

.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(15,23,42,0.18), transparent);
    margin: 24px 0;
}

.message {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
}

.avatar {
    width: 34px;
    height: 34px;
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    font-size: 0.8rem;
    flex-shrink: 0;
    box-shadow: 0 10px 20px rgba(15,23,42,0.08);
}

.avatar-user {
    background: linear-gradient(135deg, #fb923c, #f97316);
    color: white;
}

.avatar-assistant {
    background: linear-gradient(135deg, #8b5cf6, #6366f1);
    color: white;
}

.avatar-system {
    background: linear-gradient(135deg, #94a3b8, #64748b);
    color: white;
}

.bubble {
    flex: 1;
    padding: 15px 17px;
    border-radius: 22px;
    border: 1px solid rgba(15,23,42,0.07);
    box-shadow: 0 12px 28px rgba(15,23,42,0.055);
}

.bubble-user {
    background: rgba(255, 247, 237, 0.88);
}

.bubble-assistant {
    background: rgba(248, 250, 252, 0.92);
}

.bubble-system {
    background: rgba(241, 245, 249, 0.92);
}

.role {
    font-size: 0.72rem;
    font-weight: 850;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #64748b;
    margin-bottom: 7px;
}

.content {
    color: #1e293b;
    font-size: 0.96rem;
    line-height: 1.66;
    white-space: normal;
}

.content p {
    margin: 0 0 0.75rem 0;
}

.content p:last-child {
    margin-bottom: 0;
}

.content ol,
.content ul {
    margin: 0.45rem 0 0.75rem 1.35rem;
    padding-left: 1.15rem;
}

.content li {
    margin-bottom: 0.35rem;
    padding-left: 0.15rem;
    line-height: 1.62;
}


.content h1,
.content h2,
.content h3,
.content h4 {
    margin: 0.85rem 0 0.45rem 0;
    color: #0f172a;
    line-height: 1.25;
    letter-spacing: -0.02em;
}

.content h1 { font-size: 1.22rem; }
.content h2 { font-size: 1.12rem; }
.content h3 { font-size: 1.03rem; }
.content h4 { font-size: 0.98rem; }

.content p {
    margin: 0.2rem 0 0.75rem 0;
}

.content pre {
    padding: 12px 14px;
    border-radius: 14px;
    background: rgba(15,23,42,0.06);
    overflow-x: auto;
}

.content code {
    white-space: pre-wrap !important;
}

.metadata-panel {
    position: sticky;
    top: 1rem;
    padding: 22px;
    border-radius: 32px;
    background: rgba(255,255,255,0.76);
    border: 1px solid rgba(15,23,42,0.08);
    box-shadow: 0 26px 70px rgba(15,23,42,0.085);
    backdrop-filter: blur(18px);
}

.metadata-title {
    font-size: 1.18rem;
    font-weight: 900;
    letter-spacing: -0.045em;
    color: #0f172a;
    margin-bottom: 5px;
}

.metadata-subtitle {
    color: #64748b;
    font-size: 0.83rem;
    line-height: 1.45;
    margin-bottom: 17px;
}

.meta-card {
    padding: 13px 14px;
    border-radius: 19px;
    background: rgba(248,250,252,0.88);
    border: 1px solid rgba(15,23,42,0.06);
    margin-bottom: 10px;
}

.meta-label {
    font-size: 0.68rem;
    color: #64748b;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 4px;
}

.meta-value {
    font-size: 0.91rem;
    color: #0f172a;
    line-height: 1.4;
    word-break: break-word;
    font-weight: 560;
}

button[kind="secondary"], .stButton > button {
    border-radius: 999px !important;
    padding: 0.78rem 1.35rem !important;
    min-width: 285px;
    border: 1px solid rgba(15,23,42,0.10) !important;
    background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(248,250,252,0.82)) !important;
    box-shadow: 0 14px 28px rgba(15,23,42,0.09) !important;
    font-weight: 850 !important;
    color: #0f172a !important;
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 18px 36px rgba(15,23,42,0.13) !important;
}

div[data-testid="stSelectbox"] label,
div[data-testid="stSlider"] label {
    font-weight: 850;
    color: #334155;
}

div[data-testid="stSelectbox"] > div > div {
    border-radius: 18px !important;
    background: rgba(255,255,255,0.78) !important;
    border-color: rgba(15,23,42,0.08) !important;
}

div[data-testid="stExpander"] {
    border-radius: 22px !important;
    border: 1px solid rgba(15,23,42,0.07) !important;
    background: rgba(255,255,255,0.58) !important;
    overflow: hidden;
    margin-bottom: 16px;
}

div[data-testid="stExpander"] summary {
    font-weight: 850;
    color: #0f172a;
}

code {
    white-space: pre-wrap !important;
}

@media (max-width: 900px) {
    .hero-title {
        font-size: 2.2rem;
    }
    .metadata-panel {
        position: relative;
        top: 0;
    }
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def is_missing(value):
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def safe_value(value, default="N/A"):
    if is_missing(value):
        return default
    value = str(value).strip()
    return value if value else default


def pretty_category(cat: str) -> str:
    return CATEGORY_DISPLAY_NAMES.get(cat, cat.replace("_", " ").title())


@st.cache_resource
def get_geocoder():
    return Nominatim(user_agent="wildchat_browser")


@st.cache_resource
def get_timezone_finder():
    return TimezoneFinder()


@st.cache_data(show_spinner=False)
def geocode_location(country, state):
    country = safe_value(country, default="")
    state = safe_value(state, default="")

    if not country:
        return None

    query = f"{state}, {country}" if state else country

    try:
        location = get_geocoder().geocode(query, timeout=10)
        if location is None:
            return None
        return location.latitude, location.longitude
    except Exception:
        return None


# def get_timezone_from_country_state(country, state):
#     coords = geocode_location(country, state)
#     if coords is None:
#         return None

#     lat, lon = coords

#     try:
#         tf = get_timezone_finder()
#         return tf.timezone_at(lat=lat, lng=lon) or tf.closest_timezone_at(lat=lat, lng=lon)
#     except Exception:
#         return None

def get_country_timezone_fallback(country):
    country = safe_value(country, default="")

    if not country:
        return None

    try:
        match = pycountry.countries.lookup(country)
        timezones = pytz.country_timezones.get(match.alpha_2)

        if timezones:
            return timezones[0]

    except Exception:
        return None

    return None


def get_timezone_from_country_state(country, state):
    coords = geocode_location(country, state)

    if coords is not None:
        lat, lon = coords

        try:
            tf = get_timezone_finder()

            tz = tf.certain_timezone_at(lat=lat, lng=lon)

            if tz is None:
                tz = tf.timezone_at(lat=lat, lng=lon)

            if tz is None:
                tz = tf.closest_timezone_at(lat=lat, lng=lon)

            if tz:
                return tz

        except Exception:
            pass

    return get_country_timezone_fallback(country)

def format_utc_time(timestamp):
    if is_missing(timestamp):
        return "N/A"

    try:
        dt_utc = pd.to_datetime(timestamp, utc=True)
        return dt_utc.strftime("%Y-%m-%d %I:%M %p UTC")
    except Exception:
        return safe_value(timestamp)


def get_local_time_from_metadata(timestamp, country=None, state=None):
    if is_missing(timestamp):
        return "N/A"

    tz_name = get_timezone_from_country_state(country, state)

    if not tz_name:
        return "N/A"

    try:
        dt_utc = pd.to_datetime(timestamp, utc=True)

        local_dt = dt_utc.tz_convert(ZoneInfo(tz_name))

        zone_label = local_dt.tzname()

        if not zone_label:
            zone_label = tz_name.split("/")[-1].replace("_", " ")

        return (
            local_dt.strftime("%Y-%m-%d %I:%M %p")
            + f" ({zone_label})"
        )

    except Exception:
        return "N/A"


@st.cache_data(show_spinner=False)
def load_table(path_str: str):
    path = Path(path_str)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if str(path).endswith(".jsonl.gz"):
        return pd.read_json(
        path,
        lines=True,
        compression="gzip",
    )
    if path.suffix == ".jsonl":
        return pd.read_json(path, lines=True)
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    if path.suffix == ".csv":
        return pd.read_csv(path)

    raise ValueError(f"Unsupported file type: {path.suffix}")


def normalize_categories(x):
    if isinstance(x, list):
        return x

    if pd.isna(x):
        return []

    if isinstance(x, str):
        s = x.strip()
        if s.startswith("[") and s.endswith("]"):
            try:
                val = ast.literal_eval(s)
                if isinstance(val, list):
                    return val
            except Exception:
                pass
        return [s]

    return []


def repair_broken_conversation_string(s: str):
    s = s.strip()
    s = re.sub(r"\}\s*\n+\s*\{", "}, {", s)
    s = re.sub(r"\}\s+\{", "}, {", s)

    if not s.startswith("[") and s.startswith("{") and s.endswith("}"):
        s = "[" + s + "]"

    return s


def parse_python_or_json(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    if isinstance(value, (list, dict)):
        return value

    if not isinstance(value, str):
        return value

    s = value.strip()
    if not s:
        return None

    s = repair_broken_conversation_string(s)

    try:
        return json.loads(s)
    except Exception:
        pass

    try:
        return ast.literal_eval(s)
    except Exception:
        pass

    return s


def maybe_parse_messages(value):
    parsed = parse_python_or_json(value)

    if parsed is None:
        return None

    if isinstance(parsed, list):
        return parsed

    if isinstance(parsed, dict):
        for key in ["messages", "conversation", "turns", "chat", "dialogue", "history"]:
            if key in parsed:
                inner = parse_python_or_json(parsed[key])
                if isinstance(inner, list):
                    return inner
        return [parsed]

    return parsed


@st.cache_data(show_spinner=False)
def prepare_data(results_path, full_conversations_path):
    results_df = load_table(results_path)

    results_df[MERGE_KEY] = results_df[MERGE_KEY].astype(str)
    results_df["categories"] = results_df["categories"].apply(normalize_categories)

    if full_conversations_path.strip():
        conv_df = load_table(full_conversations_path)
        conv_df[MERGE_KEY] = conv_df[MERGE_KEY].astype(str)

        keep_cols = [MERGE_KEY]

        for c in FULL_CONVERSATION_CANDIDATE_COLUMNS + METADATA_COLUMNS:
            if c in conv_df.columns and c not in keep_cols:
                keep_cols.append(c)

        return results_df.merge(
            conv_df[keep_cols],
            on=MERGE_KEY,
            how="left",
            suffixes=("", "_source"),
        )

    return results_df


def filter_categories_for_display(cats):
    if not isinstance(cats, list):
        return []

    cleaned = [c for c in cats if c in CATEGORY_ORDER and c != "OUT_OF_SCOPE"]

    if len(cleaned) > 1 and "GENERAL_LIFE_HELP_SEEKING" in cleaned:
        cleaned = [c for c in cleaned if c != "GENERAL_LIFE_HELP_SEEKING"]

    return sorted(cleaned, key=lambda c: CATEGORY_ORDER.index(c))


def infer_messages_from_row(row):
    for col in FULL_CONVERSATION_CANDIDATE_COLUMNS:
        if col in row.index:
            parsed = maybe_parse_messages(row[col])
            if parsed is not None:
                return parsed

    for col in TEXT_FALLBACK_COLUMNS:
        if col in row.index and pd.notna(row[col]):
            return [{"role": "user", "content": row[col]}]

    return None


def normalize_message_item(m, index=0):
    if isinstance(m, dict):
        role = (
            m.get("role")
            or m.get("speaker")
            or m.get("author")
            or ("user" if index % 2 == 0 else "assistant")
        )

        content = (
            m.get("content")
            or m.get("text")
            or m.get("message")
            or m.get("value")
            or m.get("parts")
        )

        if isinstance(content, list):
            content = "\n".join(str(x) for x in content)

        if content is None:
            content = json.dumps(m, ensure_ascii=False, indent=2)

        return {"role": str(role).lower(), "content": str(content)}

    return {
        "role": "user" if index % 2 == 0 else "assistant",
        "content": str(m),
    }


def get_turn_count_from_messages(messages):
    if not isinstance(messages, list):
        return None

    normalized = [
        normalize_message_item(m, i)
        for i, m in enumerate(messages)
        if m is not None
    ]

    conversational = [
        m for m in normalized if m.get("role") in {"user", "assistant"}
    ]

    if not conversational:
        return None

    user_count = sum(1 for m in conversational if m.get("role") == "user")
    assistant_count = sum(1 for m in conversational if m.get("role") == "assistant")

    return max(user_count, assistant_count)


def build_category_prompt(category_name: str) -> str:
    cfg = CATEGORY_SPECS[category_name]

    pos = "\n".join(f"- {x}" for x in cfg.get("examples_yes", []))
    neg = "\n".join(f"- {x}" for x in cfg.get("examples_no", []))

    return GLOBAL_SYSTEM_TEMPLATE.format(
        category_name=category_name,
        definition=cfg["definition"],
        positive_examples=pos,
        negative_examples=neg,
    )


def chip_html(cat):
    bg, fg, accent = CATEGORY_COLORS.get(cat, ("#f8fafc", "#475569", "#94a3b8"))
    label = pretty_category(cat)
    return (
        f"<span class='chip' style='background:{bg}; color:{fg}; "
        f"box-shadow: inset 0 0 0 1px {accent}33;'>"
        f"{html.escape(label)}</span>"
    )


def render_chips(categories):
    chips = "".join(chip_html(cat) for cat in categories)
    st.markdown(f"<div class='chips'>{chips}</div>", unsafe_allow_html=True)


def render_definition_prompt(category):
    cfg = CATEGORY_SPECS[category]
    bg, fg, _ = CATEGORY_COLORS.get(category, ("#f8fafc", "#475569", "#94a3b8"))

    st.markdown(
        f"""
        <div class="lens-card" style="background:{bg};">
            <div class="lens-label" style="color:{fg};">Current Category</div>
            <div class="lens-text">
                <b>{html.escape(pretty_category(category))}</b> — {html.escape(cfg["definition"])}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("View category prompt"):
        #st.markdown("**Definition**")
        #st.write(cfg["definition"])

        #st.markdown("**Prompt used**")
        st.code(build_category_prompt(category), language="text")


def render_metadata_sidebar(row):
    timestamp = row.get("timestamp")
    country = row.get("country")
    state = row.get("state")

    metadata_items = [
        ("Conversation hash", safe_value(row.get("conversation_hash"))),
        ("Number of turns", safe_value(row.get("turn_count"))),
        ("Model", safe_value(row.get("model"))),
        ("Time UTC", format_utc_time(timestamp)),
        ("Estimated local time", get_local_time_from_metadata(timestamp, country, state)),
        ("Country", safe_value(country)),
        ("State", safe_value(state)),
        ("Language", safe_value(row.get("language"))),
    ]

    cards = ""
    for label, value in metadata_items:
        cards += f"""
        <div class="meta-card">
            <div class="meta-label">{html.escape(str(label))}</div>
            <div class="meta-value">{html.escape(str(value))}</div>
        </div>
        """

    st.markdown(
        f"""
        <div class="metadata-panel">
            <div class="metadata-title">Metadata</div>
            <!-- <div class="metadata-subtitle">
                Metadata to situate the exchange without interrupting the reading flow.
            </div> -->
            {cards}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero(total_rows):
    st.markdown(
        f"""
        <div class="hero">
            <!-- <div class="eyebrow">🌿 Help-seeking conversations · WildChat-4.8M </div> -->
            <div class="hero-title">In Search for Help</div>
            <div class="hero-subtitle">
                Browse real-world help-seeking conversations by category and conversation length.
            </div>
            <!-- <div class="stat-row"> -->
                <!-- <div class="stat-pill"> Help-Seeking Conversations in the wild</div> -->
                <!-- <div class="stat-pill">Browse by category and conversation length</div> -->
                <!-- <div class="stat-pill">10 Categories</div> -->
            <!-- </div> -->
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_content_html(raw_content):
    text = str(raw_content or "").replace("\r\n", "\n").replace("\r", "\n")

    # Escape raw HTML first, then render Markdown so headings, numbered lists,
    # bullets, bold text, links, and code blocks display properly inside the
    # custom chat bubble without changing the rest of the app.
    return markdown.markdown(
        html.escape(text),
        extensions=["fenced_code", "sane_lists", "nl2br"],
    )


def render_message_bubble(msg):
    role = msg["role"] if msg["role"] in {"user", "assistant", "system"} else "assistant"
    content = render_content_html(msg["content"])

    if role == "user":
        avatar = "U"
        avatar_class = "avatar-user"
        bubble_class = "bubble-user"
        label = "User"
    elif role == "system":
        avatar = "S"
        avatar_class = "avatar-system"
        bubble_class = "bubble-system"
        label = "System"
    else:
        avatar = "A"
        avatar_class = "avatar-assistant"
        bubble_class = "bubble-assistant"
        label = "Assistant"

    st.markdown(
        f"""
        <div class="message">
            <div class="avatar {avatar_class}">{avatar}</div>
            <div class="bubble {bubble_class}">
                <div class="role">{label}</div>
                <div class="content">{content}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.title("")

df = prepare_data(
    str(DEFAULT_RESULTS_JSONL),
    str(DEFAULT_FULL_CONVERSATIONS_FILE),
)

df["display_categories"] = df["categories"].apply(filter_categories_for_display)
df = df[df["display_categories"].apply(len) > 0].copy()

df["turn_count"] = df.apply(
    lambda row: get_turn_count_from_messages(infer_messages_from_row(row)),
    axis=1,
)

render_hero(len(df))

category_options = [
    c
    for c in CATEGORY_ORDER
    if df["display_categories"].apply(lambda cats: c in cats).any()
]

if not category_options:
    st.info("No in-scope conversations found after removing OUT_OF_SCOPE.")
    st.stop()

#st.markdown("<div class='control-card'>", unsafe_allow_html=True)

col_category, col_turns = st.columns([1.1, 1])

with col_category:
    category = st.selectbox(
        "Choose a category",
        category_options,
        format_func=pretty_category,
    )

category_df = df[
    df["display_categories"].apply(lambda cats: category in cats)
].copy()

valid_turn_counts = category_df["turn_count"].dropna()

if valid_turn_counts.empty:
    st.info("No conversations found for this category.")
    st.stop()

min_available_turns = int(valid_turn_counts.min())
max_available_turns = int(valid_turn_counts.max())

with col_turns:
    if min_available_turns == max_available_turns:
        selected_turn_range = (min_available_turns, max_available_turns)
        st.write(f"Conversation length (# turns): {min_available_turns}")
    else:
        selected_turn_range = st.slider(
            "Conversation length (# turns)",
            min_value=min_available_turns,
            max_value=max_available_turns,
            value=(min_available_turns, max_available_turns),
            step=1,
        )

st.markdown("</div>", unsafe_allow_html=True)

subset = category_df[
    category_df["turn_count"].notna()
    & (category_df["turn_count"] >= selected_turn_range[0])
    & (category_df["turn_count"] <= selected_turn_range[1])
].copy()

if subset.empty:
    st.info("No conversations found in this range.")
    st.stop()

range_key = f"{selected_turn_range[0]}_{selected_turn_range[1]}"
session_key = f"{category}_{range_key}"

hashes = subset[MERGE_KEY].astype(str).tolist()
current_hash = st.session_state.get(session_key)

if current_hash not in hashes:
    current_hash = random.choice(hashes)
    st.session_state[session_key] = current_hash

row = subset[subset[MERGE_KEY].astype(str) == current_hash].iloc[0]

main_col, metadata_col = st.columns([2.55, 1], gap="large")

with main_col:
    #st.markdown("<div class='reader-card'>", unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="reader-title">Conversation view</div>
        <div class="reader-subtitle">
            Randomly sampled from <b>{len(subset):,}</b> matching conversations.
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_definition_prompt(category)

    display_cats = row.get("display_categories", [])
    if display_cats:
        render_chips(display_cats)

    st.markdown("<div class='random-note'>Find another random conversation while keeping the same category and length filters.</div>", unsafe_allow_html=True)

    if st.button("Show another random conversation"):
        st.session_state[session_key] = random.choice(hashes)
        st.rerun()

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    messages = infer_messages_from_row(row)

    if isinstance(messages, list):
        normalized = [
            normalize_message_item(m, i)
            for i, m in enumerate(messages)
        ]

        for msg in normalized:
            render_message_bubble(msg)
    else:
        st.write("No conversation text available.")

    st.markdown("</div>", unsafe_allow_html=True)

with metadata_col:
    render_metadata_sidebar(row)


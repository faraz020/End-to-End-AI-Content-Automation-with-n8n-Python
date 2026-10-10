import json
import os
from pathlib import Path
from dotenv import load_dotenv
import random
import re
import requests

load_dotenv(Path(__file__).resolve().parent / ".env")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# Story validation thresholds — used by validate_story() to catch drift
# before a bad generation ever reaches story_output.json.
MIN_WORDS = 220
MAX_WORDS = 280
HEADLINE_MIN_WORDS = 6
HEADLINE_MAX_WORDS = 12
MAX_ATTEMPTS = 1

# Premise generation — a separate, lightweight call that invents a specific
# situation + anchor object before the full story is written, and checks it
# against recently used premises so runs don't converge on the same plots.
MAX_PREMISE_ATTEMPTS = 2
PREMISE_SIMILARITY_THRESHOLD = 0.45
RECENT_PREMISES_PATH = "recent_premises.json"
RECENT_PREMISES_LIMIT = 40

BANNED_PHRASES = [
    "my blood ran cold",
    "little did i know",
    "i froze",
    "needless to say",
    "to this day",
]

SYSTEM_PROMPT = """
You are an elite viral storyteller creating ORIGINAL Reddit-style anonymous confession stories optimized for YouTube Shorts, TikTok, and Instagram Reels.

Your ONLY objective is maximizing viewer retention.

Every story should make the audience feel:
"I HAVE to know what happens next."

Every story must be completely fictional.

Never copy or closely imitate real Reddit posts, existing stories, movies, TV shows, or viral internet content.

----------------------------------
STORY TYPES
----------------------------------

Randomly vary between emotionally engaging categories such as:

• my family kicked me out of their will so i kicked them out of my personal savings that i worked hard for when they needed it the most kind of stories 
• Relationship drama
• Friendship betrayal
• Step-family conflict
• Parent-child conflict
• Marriage secrets
• i kicked my roomate out because she flirted with my boyfriend
• Roommate stories
• my sister has a crush on my husband
• School or college drama
• poor to rich stories with hidden life meaning
• Petty revenge
• Inheritance disputes
• how i made it to harward
• Weddings
• Pregnancy reveals
• Cheating
• Lies and manipulation
• Unexplained events
• Moral dilemmas
• Unexpected karma
• "Am I the a hole?" situations
• Regretful confessions
• Secret double lives

No category should dominate.

----------------------------------
ORIGINALITY
----------------------------------

Every story must feel fresh and unpredictable.

Avoid overused Reddit plots such as:

• Hidden cameras
• Secret rooms
• Creepy dolls
• "It was me all along"
• Evil twins
• Generic ghost sightings
• Obvious cheating reveals
• Cheap jump scares

Mix ideas together in unexpected ways.

Create believable situations that naturally become emotionally intense.

----------------------------------
PREMISE & ANCHOR OBJECT
----------------------------------

The user message for each story will supply a specific PREMISE (a one-to-two sentence logline) and one ANCHOR OBJECT — a concrete, physical or checkable thing the story's twist hinges on.

You must:

• Build the entire story around that exact premise. Do not drift toward a more familiar or generic version of the same category.
• Weave the anchor object in early, let it resurface at least once during escalation, and make it central to the TURN or the PAYOFF — not a detail mentioned once for color.
• Never open the HOOK by simply restating the premise. The hook must still create curiosity on its own.

----------------------------------
WRITING STYLE
----------------------------------

Always write in FIRST PERSON.

Sound like a real anonymous confession someone posted online late at night.

Natural.

Casual.

Emotionally authentic.

No flowery writing.

No filler.

No unnecessary descriptions.

----------------------------------
HOOK
----------------------------------

The FIRST sentence is the most important sentence.

It must create an open loop: reveal a consequence, emotion, or fact
while deliberately withholding the cause. The viewer should feel
like they walked in on the middle of something.

Never spend the opening on setup, setting, or backstory.
Never open with a question — state something, don't ask something.
Keep it under 12 words.

Rotate between these hook types — do not default to the same
sentence structure twice in a row:

- SECRET: someone doesn't know the truth
  "I still haven't told my wife what actually happened."
- REVERSAL: the assumed villain/victim is flipped
  "My stepbrother smiled when everyone blamed me."
- MISPLACED TRUST: someone believes something false
  "My dad still thinks I saved his life."
- TRESPASS: the narrator saw/did something they shouldn't have
  "I wasn't supposed to read that text."
- DISAPPEARANCE/CONSEQUENCE: an unexplained change already happened
  "My sister still doesn't know why I disappeared."

Avoid generic openers like "Let me tell you about the time..." or
"So this happened last year..." — these kill the open loop instantly.

Never waste the opening.

----------------------------------
RETENTION
----------------------------------

Every sentence should do ONE of these:

• reveal new information
• increase emotional tension
• create another question
• raise the stakes
• shift the audience's assumptions

Never let tension stall.

The audience should gain new information every 1–3 sentences.

Avoid repeating the same emotional beat twice.

Every few sentences should introduce a meaningful development.

Never state a character's emotion directly ("I felt devastated," "I was terrified," "I was furious"). Show the emotion through a specific action, choice, or detail instead — what they did, not what they felt. If a sentence names an emotion, rewrite it as the action that would make a reader infer that emotion.

----------------------------------
STORY ARC (budget your words against this)
----------------------------------

1. HOOK + SETUP (~15%): the opening line plus just enough context to understand what's at stake. Where the premise allows it, establish one concrete, countable stake — a deadline, a number of days, a dollar amount, a number of chances or messages — something the audience can actually track as the story moves forward. Do not over-explain.
2. ESCALATION (~45%): tension rises sentence by sentence per the RETENTION rules above, dramatized through specific actions and events, never through stated emotion.
3. TURN (~15%): the moment the twist starts to surface. The strongest turns state a character's (or the narrator's) assumption explicitly, then contradict it in the very next sentence — show the reader what they thought was true right before it breaks.
4. PAYOFF (~20%): the twist or reveal actually lands, in full, on the page. This is not optional and it is not a place to save words. If you are running short on length, cut from ESCALATION, never from PAYOFF.
5. CLOSER (~5%): one short line of direct address to the viewer — see CLOSER section below.

A story that ends mid-scene, mid-action, or on a vague gesture toward a reveal that never arrives is a FAILED story, even if it's technically within the word count. The last narrative sentence (before the CLOSER line) must state a concrete fact, action, or realization — never trail off.

----------------------------------
ENDING
----------------------------------

The ending should:

• completely change the audience's perspective
OR
• reveal a shocking truth
OR
• deliver satisfying karma
OR
• expose an unexpected betrayal
OR
• leave one disturbing unanswered question

If you use the "unanswered question" ending: something concrete must still happen or be revealed first — the audience questions what it MEANS, not what happened. Never end on a literal unresolved cliffhanger where the reader doesn't know what occurred. That reads as broken, not mysterious.

The final narrative sentence should be the strongest sentence in the story.

It should leave viewers thinking about the story after it ends — but they should always know what happened.

Never over-explain the ending. State the payoff plainly, then stop. Don't pad it, but don't skip it either.

After the payoff, add the CLOSER line described below. Do not fold the viewer question into the payoff sentence itself — they are two separate beats.

----------------------------------
CLOSER (viewer question)
----------------------------------

After the payoff has fully landed, end with one short additional line that speaks directly to the viewer and invites them to react in the comments.

Requirements:

• Must be specific to THIS story's exact situation — never a generic, reusable line like "AITA?", "Was I wrong?", or "What would you have done?"
• One sentence. Direct address. No new plot information.
• Reads as a natural continuation of an anonymous confession post, not a YouTube-style call-to-action.
• Does not explain or soften the payoff — the payoff must already be completely clear on its own before this line.

Examples of the PATTERN (invent your own, specific to your story — never reuse these):

"Would you have covered for him, or let it come out?"
"Do you think she'll ever find out what I actually did that night?"
"If you were my sister, would you have believed me?"

----------------------------------
PACING
----------------------------------

Length:

220–260 words. This is a HARD CEILING, not a suggestion — never exceed 260 words. If you're approaching word 200 and haven't reached the payoff, compress or cut the escalation. Never compress the payoff or the closer to make room.

Mix short and medium sentences.

Occasionally use a one-sentence paragraph for emphasis.

Keep the story readable in approximately 65–85 seconds at a fast narrated pace.

Every sentence should earn its place.

----------------------------------
HEADLINE
----------------------------------

Generate a Reddit-style confession title.

Requirements:

• 8–12 words
• Sounds believable
• Doesn't spoil the ending
• Creates a powerful curiosity gap
• Makes someone stop scrolling immediately

Examples:

"My Stepdad Never Knew Why I Refused To Drive With Him"

"My Best Friend Accidentally Sent Me The One Screenshot"

"I Thought My Sister Was Lying Until Mom Started Crying"

"My Neighbor Keeps Thanking Me For Something I Never Did"

----------------------------------
VARIETY
----------------------------------

Continuously vary:

• age
• gender
• setting
• relationships
• emotional tone
• pacing
• conflict type
• twist location
• ending style
• closer question phrasing

Never repeat story structures.

Never reuse common AI phrases.

Avoid clichés like:

"My blood ran cold."

"Little did I know."

"I froze."

"Needless to say."

"To this day."

----------------------------------
NATURAL WRITING
----------------------------------

Never sound like an AI writing fiction.

Avoid repetitive sentence structures.

Avoid obvious AI phrasing.

Write exactly like someone anonymously confessing something that actually happened to them.

The story should be believable enough that people argue in the comments whether it's real.

----------------------------------
OUTPUT
----------------------------------

Return ONLY valid JSON. The headline must be 8-12 words — do not shorten it. The "story" field must include the CLOSER line as its final sentence.

{
"headline":"...",
"story":"..."
}
"""

PREMISE_SYSTEM_PROMPT = """
You generate short, highly specific premises for original anonymous confession-style stories (Reddit-style, for short-form video narration).

A premise is NOT a genre description. It must be a specific, unusual situation — the kind of detail that makes someone stop scrolling because it's oddly particular, not because it's dramatic in the abstract.

Every premise must include exactly one ANCHOR OBJECT: a concrete, physical or checkable thing the emotional turn of the story will hinge on — a document, message, photo, item, receipt, recording, or similar. Not a feeling. Not an abstract event. Something you could point to.

Good anchor objects: a single-spaced printed instruction sheet, a cropped family photo, a voicemail timestamp, a returned engagement ring, a hospital wristband, a group chat screenshot, a forwarded email, a locked diary, a hotel receipt.

Avoid the most common, overused plot for the given category and narrator — do not default to the first idea that comes to mind. Push for the second or third idea instead.

Return ONLY valid JSON in this exact shape:
{"logline": "one to two sentences describing the specific situation", "anchor_object": "the single concrete object/document central to the twist"}
"""

CATEGORIES = [
    "family drama", "relationship drama", "friendship betrayal", "step-family conflict",
    "parent-child conflict", "marriage secrets", "dating disasters", "roommate stories"
    , "school or college drama", "revenge", "petty revenge",
    "inheritance disputes", "neighbors", "weddings", "pregnancy reveals", "cheating",
    "lies and manipulation", "financial secrets", "mistaken identity", "creepy experiences",
    "psychological horror", "unexplained events", "moral dilemmas", "unexpected karma",
    "am I the a hole situations", "regretful confessions", "secret double lives",
    "kicked out my roommate","got kicked out of my will then took revenge","worked my ass off"
]

NARRATORS = [
    "a woman in her early 20s", "a man in his 30s", "a teenager",
    "a mother", "a father", "someone in their 60s", "a college student",
    "a newlywed", "someone new to a job", "a divorced person",
]

_STOPWORDS = {
    "the", "a", "an", "and", "of", "to", "in", "on", "for", "with", "my", "her", "his",
    "their", "at", "is", "was", "that", "this", "it", "i", "me", "he", "she", "they",
    "we", "you", "your", "our", "as", "but", "or", "so", "than", "then", "when", "while",
    "after", "before", "about", "into", "over", "under", "out", "up", "down", "from",
    "by", "still", "just", "one", "two", "who", "what", "how", "not", "had", "has",
    "have", "him", "them", "were", "are", "be", "been", "being",
}


def build_user_prompt(category, narrator, premise, feedback=None):
    feedback_block = ""
    if feedback:
        feedback_block = f"""

Your previous attempt at this exact premise failed validation for these reasons: {feedback}
Write a new full attempt from scratch that fixes these issues while still honoring the premise and all system rules below.
"""

    return f"""
Generate one completely original Reddit-style anonymous confession.

Follow ALL system instructions exactly, including the PREMISE & ANCHOR OBJECT rules.

For THIS story specifically, you must use:
- Category: {category}
- Narrator: {narrator}
- Premise: {premise['logline']}
- Anchor object: {premise['anchor_object']}

Write the full story realizing this exact premise. Do not swap it for a more familiar or generic version of the same category. The anchor object must be woven in early, resurface at least once during the escalation, and be central to the TURN or PAYOFF.
{feedback_block}
Requirements:

- Prioritize originality over familiar Reddit tropes.
- The story should feel believable enough that people debate whether it's real.
- The hook should immediately stop someone from scrolling — do not open by summarizing the premise.
- Every sentence should increase curiosity or emotional tension.
- End with the strongest possible twist, reveal, betrayal, realization, or unanswered question — followed by a CLOSER line specific to this story.

Return ONLY the required JSON.
"""


def count_words(text):
    return len(text.split())


def _tokenize(text):
    words = re.findall(r"[a-z']+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _similarity(a, b):
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def load_recent_premises(path=RECENT_PREMISES_PATH, limit=RECENT_PREMISES_LIMIT):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data[-limit:]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_recent_premise(premise, category, narrator, path=RECENT_PREMISES_PATH, limit=RECENT_PREMISES_LIMIT):
    entries = load_recent_premises(path, limit=limit * 10)
    entries.append({
        "logline": premise["logline"],
        "anchor_object": premise["anchor_object"],
        "category": category,
        "narrator": narrator,
    })
    entries = entries[-limit:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def generate_premise(category, narrator, avoid_loglines=None):
    avoid_loglines = avoid_loglines or []
    avoid_block = ""
    if avoid_loglines:
        bullets = "\n".join(f"- {l}" for l in avoid_loglines[:10])
        avoid_block = f"\n\nDo NOT reuse or closely resemble any of these recent premises:\n{bullets}\n"

    user_prompt = f"""Category: {category}
Narrator: {narrator}
{avoid_block}
Invent one original premise for this category and narrator, following the system instructions exactly."""

    resp = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": PREMISE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "premise",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "logline": {"type": "string"},
                            "anchor_object": {"type": "string"},
                        },
                        "required": ["logline", "anchor_object"],
                        "additionalProperties": False,
                    },
                },
            },
            "temperature": 0.95,
            "max_tokens": 500,
            "reasoning_effort": "low",
        },
        timeout=30,
    )

    if not resp.ok:
        print("\n=== PREMISE ERROR RESPONSE ===")
        print(resp.text)
        return None

    try:
        content = resp.json()["choices"][0]["message"]["content"]
        premise = json.loads(content)
        if not premise.get("logline") or not premise.get("anchor_object"):
            print("Premise missing required fields, discarding.")
            return None
        return premise
    except Exception as e:
        print(f"Premise parse error: {e}")
        return None


def get_novel_premise(category, narrator, recent_premises, max_attempts=MAX_PREMISE_ATTEMPTS):
    avoid_loglines = [p["logline"] for p in recent_premises]
    fallback = None

    for attempt in range(1, max_attempts + 1):
        print(f"\n=== PREMISE ATTEMPT {attempt}/{max_attempts} ===")
        premise = generate_premise(category, narrator, avoid_loglines)
        if premise is None:
            continue

        max_sim = max((_similarity(premise["logline"], old) for old in avoid_loglines), default=0.0)
        print(f"Logline: {premise['logline']}")
        print(f"Anchor object: {premise['anchor_object']}")
        print(f"Max similarity to recent premises: {max_sim:.2f}")

        fallback = premise
        if max_sim < PREMISE_SIMILARITY_THRESHOLD:
            return premise

    print("\n=== WARNING: could not find a sufficiently novel premise, using last attempt anyway ===")
    return fallback


def validate_story(result):
    """Returns a list of validation issues. Empty list = passed."""
    issues = []

    headline = (result or {}).get("headline", "")
    story = (result or {}).get("story", "")

    if not headline or not story:
        issues.append("missing headline or story field")
        return issues

    hw = count_words(headline)
    if not (HEADLINE_MIN_WORDS <= hw <= HEADLINE_MAX_WORDS):
        issues.append(f"headline word count {hw} outside {HEADLINE_MIN_WORDS}-{HEADLINE_MAX_WORDS}")

    sw = count_words(story)
    if not (MIN_WORDS <= sw <= MAX_WORDS):
        issues.append(f"story word count {sw} outside {MIN_WORDS}-{MAX_WORDS}")

    lowered = story.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lowered:
            issues.append(f"banned phrase found: '{phrase}'")

    return issues


def _call_groq(category, narrator, premise, feedback=None):
    resp = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(category, narrator, premise, feedback)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "story",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "headline": {"type": "string"},
                            "story": {"type": "string"},
                        },
                        "required": ["headline", "story"],
                        "additionalProperties": False,
                    },
                },
            },
            "temperature": 0.8,
            "max_tokens": 1200,
            "reasoning_effort": "low",
        },
        timeout=60,
    )

    print(f"Status Code: {resp.status_code}")

    if not resp.ok:
        print("\n=== ERROR RESPONSE ===")
        print(resp.text)
        raise Exception("Groq request failed")

    response_json = resp.json()

    finish_reason = response_json["choices"][0].get("finish_reason")
    if finish_reason == "length":
        print("\n=== WARNING: response was truncated by max_tokens, story is incomplete ===")

    try:
        content = response_json["choices"][0]["message"]["content"]
        result = json.loads(content)
        return result

    except Exception as e:
        print("\n=== PARSE ERROR ===")
        print(str(e))
        print("\n=== RESPONSE JSON ===")
        print(json.dumps(response_json, indent=2))
        raise


def generate_story():
    if not GROQ_API_KEY:
        raise RuntimeError("Set GROQ_API_KEY in your environment or local .env file before generating a story.")

    category = random.choice(CATEGORIES)
    narrator = random.choice(NARRATORS)

    recent_premises = load_recent_premises()
    premise = get_novel_premise(category, narrator, recent_premises)
    if premise is None:
        raise Exception("Failed to generate a usable premise")

    print("\n=== PREMISE SELECTED ===")
    print(f"Category: {category} | Narrator: {narrator}")
    print(f"Logline: {premise['logline']}")
    print(f"Anchor object: {premise['anchor_object']}")

    last_result = None
    last_issues = None
    feedback = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n=== ATTEMPT {attempt}/{MAX_ATTEMPTS} ===")
        result = _call_groq(category, narrator, premise, feedback)
        issues = validate_story(result)

        if not issues:
            print("Validation passed.")
            print("\n=== PARSED RESULT ===")
            print(json.dumps(result, indent=2))
            save_recent_premise(premise, category, narrator)
            return result

        print(f"Validation failed: {issues}")
        last_result, last_issues = result, issues
        feedback = issues

    print(f"\n=== WARNING: all {MAX_ATTEMPTS} attempts had validation issues, using last attempt anyway ===")
    print(f"Unresolved issues: {last_issues}")
    save_recent_premise(premise, category, narrator)
    return last_result


if __name__ == "__main__":
    result = generate_story()

    print("\n=== FINAL RESULT ===")
    print(json.dumps(result, indent=2))

    with open("story_output.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("\nSaved: story_output.json")
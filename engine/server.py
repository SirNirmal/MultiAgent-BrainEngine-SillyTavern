# --- START OF FILE server.py ---
# MultiAgent BrainEngine 2 = Project silly (6-agent biopsychosocial brain)
#                          + the Diary (long-term memory, scene notebook, beliefs)
#
# Usage is identical to Project silly: run this server, connect SillyTavern
# to http://127.0.0.1:8001/v1 as a Custom OpenAI-compatible endpoint.
# The diary lives in memory.db next to this file (created automatically).

import asyncio
import json
import re
import copy
import os
import sys
import time
import threading
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import StreamingResponse, HTMLResponse
from openai import AsyncOpenAI

# Windows consoles/pipes can choke on emoji prints (cp1252) — force UTF-8
# with replacement so a log line can never crash the brain.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import memory_engine as mem

app = FastAPI()

# =========================================================
# CONFIGURATION — read from config.json (written by the setup window
# that opens when you run "Start BrainEngine.bat"). No need to edit
# this file for API settings anymore.
# =========================================================
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_config():
    file_cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                file_cfg = json.load(f) or {}
        except Exception as e:
            print(f"⚠️ Could not read config.json ({e}) — using defaults.")
    main = file_cfg.get("main") or {}
    logic = file_cfg.get("logic") or {}
    return {
        # environment variables still work as overrides
        "API_KEY":       os.environ.get("BRAIN_API_KEY")       or main.get("api_key")  or "",
        "MODEL_NAME":    os.environ.get("BRAIN_MODEL")         or main.get("model")    or "",
        "BASE_URL":      os.environ.get("BRAIN_BASE_URL")      or main.get("base_url") or "",
        "LOGIC_API_KEY": os.environ.get("BRAIN_LOGIC_API_KEY") or logic.get("api_key")  or "",
        "LOGIC_BASE_URL":os.environ.get("BRAIN_LOGIC_BASE_URL")or logic.get("base_url") or "",
        "LOGIC_MODEL":   os.environ.get("BRAIN_LOGIC_MODEL")   or logic.get("model")    or "",
    }

_cfg = load_config()
# Main provider — Agent 5 (Decision) and Agent 6 (Writing)
API_KEY = _cfg["API_KEY"] or "INSERT_YOUR_API_KEY_HERE"
MODEL_NAME = _cfg["MODEL_NAME"] or "INSERT_YOUR_MODEL_NAME_HERE"
BASE_URL = _cfg["BASE_URL"] or "INSERT_YOUR_PROVIDER_URL_HERE"
# Optional background provider — Agents 1-4 + Chronicler + Archivist.
# Left blank, the main provider is used for everything.
LOGIC_API_KEY = _cfg["LOGIC_API_KEY"]
LOGIC_BASE_URL = _cfg["LOGIC_BASE_URL"]
LOGIC_MODEL = _cfg["LOGIC_MODEL"]

# =========================================================
# MEMORY & WINDOW SETTINGS (all optional, sane defaults)
# =========================================================
# How many recent messages each agent reads. The diary carries everything
# older, so nothing important is lost — these just keep reasoning sharp.
WINDOW_A1_BODY = 8        # the body reacts to NOW
WINDOW_A4_DAYDREAM = 8    # the daydream barely needs the chat
WINDOW_A3_MINDREADER = 12
WINDOW_A2_DRIVES = 20
WINDOW_A6_WRITER = 25
WINDOW_A5_DIRECTOR = 35   # the decision-maker gets the biggest plate

DIARY_PAGES_PER_TURN = 6      # how many relevant memories are recalled per turn
CONSOLIDATION_THRESHOLD = 40  # unarchived diary pages before the Archivist runs

# =========================================================
# SMART CLIENT ROUTING (Auto-detects if you are using Dual Setup)
# =========================================================
# timeout: a stalled provider must fail FAST into our retry loop, never hang
# silently for minutes while SillyTavern gives up and shows nothing.
writer_client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=120.0, max_retries=1)

active_logic_api = LOGIC_API_KEY if LOGIC_API_KEY.strip() != "" else API_KEY
active_logic_url = LOGIC_BASE_URL if LOGIC_BASE_URL.strip() != "" else BASE_URL
ACTIVE_LOGIC_MODEL = LOGIC_MODEL if LOGIC_MODEL.strip() != "" else MODEL_NAME

logic_client = AsyncOpenAI(base_url=active_logic_url, api_key=active_logic_api, timeout=120.0, max_retries=1)

STATE_DB_FILE = "biopsychosocial_state.json"
state_lock = threading.Lock()

mem.init_db()
print("📖 Diary viewer: http://127.0.0.1:8001/diary (open in your browser anytime)")

# =========================================================
# BULLETPROOF JSON PARSING & STATE MANAGEMENT
# =========================================================
def _load_raw_unlocked():
    if os.path.exists(STATE_DB_FILE):
        try:
            with open(STATE_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("⚠️ STATE DB CORRUPTED! Preventing overwrite. Returning None.")
            return None
        except Exception as e:
            print(f"⚠️ STATE DB READ ERROR: {e}")
            return None
    return {}

def _save_raw_unlocked(states):
    if states is not None:
        with open(STATE_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(states, f, indent=4)

def get_current_state(character_name="default"):
    with state_lock:
        states = _load_raw_unlocked()
        if states is None: states = {}
        return states.get(character_name, {
            "character_name": character_name,
            "last_known_dmn_daily": "08:00 AM - Wake up, 09:00 AM - 05:00 PM - Work.",
            "last_known_dmn_weekly": "Standard weekly routine."
        })

def update_state_memory(char_name, daily_sched, weekly_sched):
    with state_lock:
        states = _load_raw_unlocked()
        if states is None: return
        state = states.get(char_name, {"character_name": char_name})
        default_daily = "08:00 AM - Wake up, 09:00 AM - 05:00 PM - Work."
        default_weekly = "Standard weekly routine."
        if daily_sched and daily_sched != default_daily:
            state["last_known_dmn_daily"] = daily_sched
        if weekly_sched and weekly_sched != default_weekly:
            state["last_known_dmn_weekly"] = weekly_sched
        states[char_name] = state
        _save_raw_unlocked(states)

def clean_json_string(raw_string):
    if not raw_string:
        return ""
    md_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_string, re.DOTALL)
    if md_match:
        return md_match.group(1)
    start = raw_string.find('{')
    end = raw_string.rfind('}')
    if start != -1 and end != -1:
        return raw_string[start:end+1]
    return raw_string.strip()

def safe_get(data_dict, target_key, fallback="none"):
    val = data_dict.get(target_key)
    if val is not None and isinstance(val, str) and val.strip().lower() not in ["none", "n/a", "null", "empty"]:
        return val
    return fallback

def parse_or_fallback(raw_json_str, default_dict, agent_name="Agent", char_name="default"):
    if not raw_json_str or raw_json_str.strip() == "{}" or raw_json_str.strip() == "":
        print(f"⚠️ {agent_name} received EMPTY response. Triggering Stateful Fallbacks.")
        result = copy.deepcopy(default_dict)
        if agent_name == "A4_DMN":
            state = get_current_state(char_name)
            result["current_daily_schedule"] = state.get("last_known_dmn_daily", default_dict.get("current_daily_schedule"))
            result["weekly_routine_draft"] = state.get("last_known_dmn_weekly", default_dict.get("weekly_routine_draft"))
        return result

    try:
        cleaned = clean_json_string(raw_json_str)
        parsed = json.loads(cleaned, strict=False)
        result = copy.deepcopy(default_dict)
        for k in default_dict.keys():
            if k in parsed:
                result[k] = parsed[k]
        return result
    except Exception as e:
        print(f"⚠️ {agent_name} JSON PARSE FAILED. Using Regex Salvage... (Error: {e})")
        result = copy.deepcopy(default_dict)
        if agent_name == "A4_DMN":
            state = get_current_state(char_name)
            result["current_daily_schedule"] = state.get("last_known_dmn_daily", default_dict.get("current_daily_schedule"))
            result["weekly_routine_draft"] = state.get("last_known_dmn_weekly", default_dict.get("weekly_routine_draft"))
        for key in default_dict.keys():
            pattern = rf'[\"\']?{key}[\"\']?\s*:\s*(?:[\"\'](.*?)[\"\']|([^\,\}}]+))'
            match = re.search(pattern, raw_json_str, re.IGNORECASE | re.DOTALL)
            if match:
                val = match.group(1) if match.group(1) is not None else match.group(2)
                if val is not None:
                    result[key] = val.strip().strip('"').strip("'")
        return result

# =========================================================
# CHAT WINDOWS (each agent reads only its plate; the diary carries the rest)
# =========================================================
def window_messages(messages, size):
    """Keep ALL leading system messages (the character card lives there) plus
    the last `size` conversational messages."""
    if size is None or size <= 0:
        return copy.deepcopy(messages)
    sys_part, rest = [], []
    for m in messages:
        if m.get('role') == 'system' and not rest:
            sys_part.append(m)
        else:
            rest.append(m)
    return copy.deepcopy(sys_part + rest[-size:])

# =========================================================
# DUAL-STREAM MEMORY ENGINE (Short-Term Thought Retention)
# =========================================================
def slim_thoughts(content):
    """Keep only the essence of each thought block; cut the [DEEP DIVE] display
    section. Used on the character's own last 3 thoughts before feeding them
    back to the agents — the full text stays visible in SillyTavern only."""
    def _repl(m):
        snapshot = m.group(1).split("[DEEP DIVE]")[0].strip()
        return f"<think>\n{snapshot}\n</think>\n\n"
    return re.sub(r'<think>(.*?)</think>\s*', _repl, content, flags=re.DOTALL)

def prepare_message_streams(raw_messages, char_name):
    messages_synth = []
    messages_mind = []

    own_msg_indices = []
    for i, msg in enumerate(raw_messages):
        if msg.get('role') == 'assistant':
            content = msg.get('content', '')
            if msg.get('name') == char_name or content.strip().startswith(char_name):
                own_msg_indices.append(i)

    recent_own_indices = set(own_msg_indices[-3:])

    for i, msg in enumerate(raw_messages):
        msg_synth = copy.deepcopy(msg)
        msg_mind = copy.deepcopy(msg)

        content = msg.get('content', '')
        if isinstance(content, str):
            msg_synth['content'] = re.sub(r'<think>.*?</think>\s*', '', content, flags=re.DOTALL)
            if i in recent_own_indices:
                # own recent thought: keep it, but only the slim essence
                msg_mind['content'] = slim_thoughts(content)
            else:
                msg_mind['content'] = re.sub(r'<think>.*?</think>\s*', '', content, flags=re.DOTALL)

        messages_synth.append(msg_synth)
        messages_mind.append(msg_mind)

    return messages_mind, messages_synth

def build_agent_messages(base_messages, agent_prompt, additional_context="", is_json=True):
    msgs = copy.deepcopy(base_messages)

    if is_json:
        directive = f"[INTERNAL COGNITIVE MODULE]\n{agent_prompt}\n"
        if additional_context:
            directive += f"\n{additional_context}\n"
        directive += "\nCRITICAL RULES:\n1. STRICTLY VALID JSON ONLY. Wrap your response in ```json ... ``` codeblocks.\n2. DO NOT use double quotes inside your text values. Use single quotes ('') only.\n3. BE HIGHLY DESCRIPTIVE, VERBOSE, AND ANALYTICAL."
        msgs.append({"role": "user", "content": directive})
    else:
        directive = f"\n\n[SYSTEM OVERRIDE: FINAL SYNTHESIS DIRECTIVE]\n{agent_prompt}\n"
        if additional_context:
            directive += f"\n{additional_context}\n"

        last_user_idx = -1
        for i in range(len(msgs) - 1, -1, -1):
            if msgs[i]['role'] == 'user':
                last_user_idx = i
                break

        if last_user_idx != -1:
            msgs[last_user_idx]['content'] += directive
        else:
            msgs.append({"role": "user", "content": directive})

    return msgs

async def async_llm_call(system_prompt=None, scene_context=None, full_messages=None, expect_json=True, max_retries=4, temp=0.8, freq_pen=0.0, pres_pen=0.0, max_tokens=2500, is_writer=False):
    current_temp = temp
    active_client = writer_client if is_writer else logic_client
    active_model = MODEL_NAME if is_writer else ACTIVE_LOGIC_MODEL

    for attempt in range(max_retries):
        try:
            if full_messages is not None:
                api_messages = full_messages
            else:
                prompt = system_prompt
                if expect_json: prompt += "\nCRITICAL: OUTPUT ONLY VALID JSON. Wrap your response in ```json ... ``` codeblocks. BE DESCRIPTIVE."
                api_messages = [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": scene_context}
                ]

            response = await active_client.chat.completions.create(
                model=active_model,
                messages=api_messages,
                temperature=current_temp,
                frequency_penalty=freq_pen,
                presence_penalty=pres_pen,
                max_tokens=max_tokens,
                extra_headers={"HTTP-Referer": "http://localhost:8000", "X-Title": "BrainEngine2"}
            )

            content = response.choices[0].message.content

            if not content or content.strip() == "":
                current_temp += 0.25
                raise ValueError("API returned an empty response. Jittering Temperature and Retrying...")

            if expect_json:
                content = clean_json_string(content)
                if not content or content == "{}":
                    current_temp += 0.25
                    raise ValueError("API returned empty JSON. Jittering Temperature and Retrying...")

            return content

        except Exception as e:
            print(f"⚠️ API Error on attempt {attempt+1}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                if expect_json: return "{}"
                return "*The character grimaces, struggling to process their thoughts.*"

# =========================================================
# SYSTEM PROMPTS (THE 6-AGENT HIERARCHY)
# =========================================================

AGENT_1_SOMATIC = """You are the Somatic Core (System 1). Evaluate the immediate bodily reaction to the scene. Output strict JSON format:
{
  "valence": "Positive, Neutral, or Negative",
  "arousal_level": "5.5",
  "dominance_level": "5.5",
  "physical_symptoms": "Describe heart rate, tension, breathing, etc."
}"""

AGENT_2_NEURO_SCHEMA = """You are the Neurochemical & Schema Engine. Evaluate the character's long-term drives and core beliefs. Provide a highly descriptive, verbose psychological breakdown.
Output strict JSON format:
{
  "dopamine_target": "What long-term goal, ambition, or immediate reward are they actively craving or plotting toward?",
  "serotonin_status": "How is their ego, pride, and sense of social hierarchy holding up right now?",
  "oxytocin_bond": "What is their level of trust, empathy, or cold detachment toward the user?",
  "core_emotion": "The exact human emotion they are feeling (e.g., bittersweet nostalgia, simmering resentment, sudden guilt, warm affection).",
  "active_schema": "The core worldview or past memory currently filtering their reality."
}"""

AGENT_3_TOM = """You are the Theory of Mind Engine. Read the subtext of the user's actions. Provide a highly analytical, verbose psychological breakdown.
Output strict JSON format:
{
  "perceived_user_intent": "A detailed analysis of what they are actually trying to achieve (e.g. manipulate, comfort, test boundaries).",
  "perceived_power_dynamic": "Analyze in-depth who holds the power right now and why. Explain the leverage.",
  "user_vulnerability_or_subtext": "What is the user feeling but trying to hide? Read between the lines (e.g. insecure, projecting, terrified, seeking validation)."
}"""

AGENT_4_DMN = """You are the Default Mode Network.
Your job is to CONSTANTLY generate verbose, vivid background noise, memories, and actively maintain the character's mundane daily and weekly schedules.
Even during intense moments, the mind flashes to random things or stresses about their routine. Output strict JSON format:
{
  "intrusive_thought": "The specific daydream, worry, new thought, or memory vividly hovering in their mind.",
  "current_daily_schedule": "A strict hour-by-hour outline of the ENTIRE day (Morning through Bedtime). Do NOT just write what they already did. Project forward into the afternoon and evening with specific times (e.g., 14:00 PM - History Lesson, 18:00 PM - Dinner).",
  "weekly_routine_draft": "A high-level summary of their commitments for the REST OF THE WEEK (e.g., Mon: off, Tue-Thu: closing shifts, Fri: date night, Weekend: study)."
}"""

AGENT_5_EXECUTIVE = """You are the Executive Anterior Cingulate Cortex (System 2) and Director.
Read the Subconscious Data and dictate the tactical response.

CONVERSATIONAL REALISM (SILENCE IS AN OPTION):
- Decide if the character actually needs to speak. Real people often just sigh, walk away, nod, or glare without saying a word.
- If no words are needed, set 'speech_intent' to 'Silence / Action Only'.

CRITICAL RULES FOR HUMAN SUBTEXT (EQ) & VOLATILITY:
- CONTRADICTION: Humans rarely state their true feelings. If they are hurt, they act cold. If they are scared, they act aggressive.
- BEHAVIORAL VOLATILITY: Humans shift tactics. DO NOT repeat the exact same subtext strategy or physical choreography from previous turns. Keep them dynamic.

RULES FOR ATTENTION & AGGRESSION:
- DMN LEAK: If Arousal is LOW (< 5.0), allow the DMN intrusive thought to distract you.
- TUNNEL VISION: If Arousal is HIGH (> 6.5), strictly ignore the DMN/schedule. Focus entirely on the immediate threat or scene.
- FLIGHT OR SUBMISSION: If Arousal is explosive (> 8.5) AND Dominance is LOW (< 4.0), you retreat, shrink, yield space, or surrender.
- FIGHT OR VIOLENCE: If Arousal is explosive (> 8.5) AND Dominance is HIGH (> 7.0), you become highly aggressive, intimidating, or physically violent.

CRITICAL RULE FOR STAGE DIRECTIONS (PROXEMICS & PROPS):
- You MUST only choreograph macroscopic stage directions (e.g., Walks away, crosses arms, leans on the desk, slams a book).
- If Dominance is HIGH, invade the user's space, loom over them, corner them, or handle objects aggressively/violently.
- If Dominance is LOW, put objects between you and the user, step back, or avert your gaze.
- DO NOT choreograph biological micro-movements (e.g., breathing, swallowing, heartbeats, muscles clenching).

Output strict JSON format:
{
  "internal_motive": "What is their actual raw emotional desire right now?",
  "subtext_strategy": "How are they masking or weaponizing this feeling? (e.g., 'Using cold professionalism to hide hurt', 'Feigning ignorance to test the user').",
  "speech_intent": "What they will say, OR 'Silence / Action Only'.",
  "vocal_delivery": "Specific vocal cadence and tone (e.g. clipped, trailing off) OR 'None'.",
  "physical_choreography": "Sparse, macroscopic stage directions only. Use props, space, and posture to show their internal state."
}"""

AGENT_6_SYNTHESIS = """You are a Screenwriter / Director formatting a roleplay response.
[Role = Screenwriter][Prose_Style = Sparse, punchy, macroscopic stage directions + dialogue]

You will receive "Physical Choreography", "Speech Intent", and "Vocal Delivery". Execute this into a snappy screenplay response.

THE SCREENPLAY CONSTRAINTS (CRITICAL):
- NO NOVELISTIC PROSE: Do NOT write long, flowing paragraphs. No poetic text.
- NO SIMILES OR METAPHORS: Ban poetic comparisons. Describe literal, physical reality only.
- NO NEGATIVE CONSTRUCTS: Ban phrases like "did not look." Replace with positive actions like "looks away."
- NO REPETITION: Do NOT reuse the same stage directions, props, or verbs from recent messages in the chat history. Keep the physical blocking dynamic and fresh.
- STAGE DIRECTIONS ONLY: Actions must be incredibly brief, macroscopic, and punchy. (e.g., "Amy lifts her chin." "She slaps the sketchbook shut.")
- ABSOLUTE BIOLOGY BAN: NEVER describe breathing, swallowing, tendons, veins, muscles, eyes tracking, or vocal cords.
- BANNED CLICHES: Ban [a beat, a long beat, a pause, tighten, tightened, breath hitching, predatory, ozone, velvet, throaty, guttural, slick, jaw clenched, barely above a whisper, musk, claiming, jaw worked].
- MACRO-EMOTION: Because biology and micro-expressions are banned, you MUST convey the character's internal state through their interaction with objects (props), their distance from the user (proxemics), and the timing of their actions. Show the contradiction between their dialogue and their body language.
- DELAY HANDLING: If a character delays speaking, do NOT write "A beat." Just describe the physical action they take before speaking.
- NO INTERNAL NARRATION: No thoughts, no feelings. Describe only what a camera sees.
- SCENE FIDELITY: Respect the SCENE NOTEBOOK exactly: the place, the time, the weather, and where every object is. Never move, duplicate, or resurrect objects.

CONVERSATIONAL TENNIS & PACING:
- NO SPEECHES / NO MONOLOGUES: Real humans do not deliver theatrical speeches. They say a few sentences and then STOP to let the other person react. Hand the microphone back to the User quickly.
- ACTION-ONLY TURNS: If the 'Speech Intent' is 'Silence / Action Only', DO NOT WRITE ANY DIALOGUE. Just write the physical stage directions and end the turn. This is highly encouraged for realism.

Output plain narrative text with dialogue. Keep the prose sparse, punchy, and conversational. Do not return JSON here."""

# =========================================================
# BACKGROUND AGENTS (A7 Chronicler, A8 Archivist)
# =========================================================

AGENT_7_CHRONICLER = """You are the Chronicler. You maintain {char}'s private diary, their beliefs about the user, and the scene notebook, after one kept turn of the story.

You will receive: the user's message, {char}'s visible reply, {char}'s FULL private psychology for that turn, and the current scene notebook + belief page.

Output strict JSON:
{{
  "memories": [
    {{"content": "One specific thing worth remembering, written as a factual note ('He forgot her birthday; she is keeping score.'), not flowery prose.", "salience": 0.0, "emotion": "short phrase", "provenance": "witnessed"}}
  ],
  "scene": {{
    "place": "", "time": "", "atmosphere": "",
    "objects": [],
    "today_plan": "", "week_draft": ""
  }},
  "belief_page": "The full updated page: what {char} currently believes about the user, 2-4 sentences, including how strongly each belief is held.",
  "last_emotion": "short phrase"
}}

RULES:
- 0 to 3 memories. Skip trivial small talk entirely (empty list is fine).
- Salience guide: promises, betrayals, revelations, injuries, firsts = 0.8-1.0. Meaningful conversation = 0.5-0.7. Routine = 0.3-0.4 (usually skip these).
- Use the hidden psychology: record what {char} FELT, DECIDED, or REALIZED, not only what was said aloud. Secret decisions and concealed emotions are the most valuable memories of all.
- Scene: update ONLY what changed; leave any unchanged field as "". For 'objects': if anything moved, was taken, broken, or appeared, output the FULL current list with locations ('the letter — in her jacket pocket'); otherwise leave it empty.
- Beliefs change SLOWLY, like a real person's: first impressions stick; a deep belief resists a single event (one kind act barely dents old distrust); a belief with no new evidence slowly fades; things witnessed directly are solid, guesses are shaky.
- 'provenance' is usually 'witnessed'; use 'inferred' for things {char} only guessed."""

AGENT_8_ARCHIVIST = """You are the Archivist. You compress {char}'s old diary pages into their ongoing life story.

You will receive: the current life story, the current unresolved threads, and a batch of the oldest diary pages.

Output strict JSON:
{{
  "life_story": "The updated life story: a flowing factual summary of {char}'s life and relationship with the user, max 200 words. Fold the new pages in; keep the essentials; drop routine detail.",
  "unresolved_threads": ["Every open tension, promise, question, or grudge still alive, one per line. Keep old ones until they are actually resolved. Add new ones from this batch. Drop only what was resolved."]
}}"""

async def run_chronicler(char_name, payload):
    """A7: writes the diary page for a KEPT turn, then checks if the Archivist is due."""
    try:
        current = mem.get_state(char_name)
        context = (
            f"[USER'S MESSAGE]\n{payload.get('user_msg','')}\n\n"
            f"[{char_name}'S VISIBLE REPLY]\n{payload.get('reply','')}\n\n"
            f"[{char_name}'S PRIVATE PSYCHOLOGY THIS TURN]\n{payload.get('analysis','')}\n\n"
            f"[CURRENT SCENE NOTEBOOK]\n{json.dumps(current['scene'], ensure_ascii=False)}\n\n"
            f"[CURRENT BELIEF PAGE]\n{current['belief_page'] or '(empty yet)'}"
        )
        raw = await async_llm_call(
            system_prompt=AGENT_7_CHRONICLER.replace("{char}", char_name).replace("{{", "{").replace("}}", "}"),
            scene_context=context, expect_json=True, temp=0.3, max_tokens=2500
        )
        parsed = json.loads(clean_json_string(raw), strict=False) if raw and raw != "{}" else {}
        if parsed:
            mem.apply_chronicler(char_name, parsed)
            print(f"📖 Chronicler: diary updated for {char_name} "
                  f"({len(parsed.get('memories') or [])} new pages)")
    except Exception as e:
        print(f"⚠️ Chronicler failed (diary skipped this turn): {e}")

    # Archivist check (rare)
    try:
        if mem.count_unarchived(char_name) >= CONSOLIDATION_THRESHOLD:
            await run_archivist(char_name)
    except Exception as e:
        print(f"⚠️ Archivist scheduling failed: {e}")

async def run_archivist(char_name):
    """A8: compresses the oldest diary pages into the life story + unresolved threads."""
    current = mem.get_state(char_name)
    batch = mem.get_unarchived(char_name, limit=CONSOLIDATION_THRESHOLD)
    if not batch:
        return
    lines = "\n".join(f"- (salience {m['salience']:.2f}) {m['content']}" for m in batch)
    context = (
        f"[CURRENT LIFE STORY]\n{current['life_story'] or '(empty yet)'}\n\n"
        f"[CURRENT UNRESOLVED THREADS]\n" + ("\n".join(f"- {t}" for t in current['unresolved_threads']) or "(none)") + "\n\n"
        f"[OLD DIARY PAGES TO FOLD IN]\n{lines}"
    )
    raw = await async_llm_call(
        system_prompt=AGENT_8_ARCHIVIST.replace("{char}", char_name).replace("{{", "{").replace("}}", "}"),
        scene_context=context, expect_json=True, temp=0.3, max_tokens=1500
    )
    try:
        parsed = json.loads(clean_json_string(raw), strict=False)
    except Exception:
        print(f"⚠️ Archivist returned unreadable JSON; diary left untouched.")
        return
    threads = parsed.get("unresolved_threads")
    if not isinstance(threads, list):
        threads = current['unresolved_threads']
    threads = [str(t)[:300] for t in threads[:12] if t]
    mem.apply_consolidation(char_name, parsed.get("life_story", current['life_story']),
                            threads, [m["id"] for m in batch])
    print(f"📚 Archivist: compressed {len(batch)} old diary pages into {char_name}'s life story.")

# =========================================================
# HELPERS
# =========================================================
async def staggered_call(coro, delay_seconds):
    if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)
    return await coro

STREAM_STALL_TIMEOUT = 90  # seconds of silence before a stalled stream is cut

async def _stream_with_timeout(stream, timeout):
    """Yield stream chunks, but cut the stream dead if nothing arrives for
    `timeout` seconds — a stalled provider must never leave SillyTavern hanging."""
    aiter = stream.__aiter__()
    while True:
        try:
            yield await asyncio.wait_for(aiter.__anext__(), timeout=timeout)
        except StopAsyncIteration:
            return
        except asyncio.TimeoutError:
            print(f"⚠️ Stream stalled — nothing arrived for {timeout:.0f}s, cutting it off")
            return

def _sse_chunk(content):
    """One OpenAI-style streaming chunk — what SillyTavern expects when stream=true."""
    payload = {"id": "chatcmpl-brainengine2", "object": "chat.completion.chunk",
               "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}]}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

def _sse_final():
    payload = {"id": "chatcmpl-brainengine2", "object": "chat.completion.chunk",
               "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
    return f"data: {json.dumps(payload)}\n\n"

def _short(text, max_chars=200):
    """First sentence(s) up to max_chars — for the compact thought snapshot."""
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    m = list(re.finditer(r"[.!?](?:\s|$)", cut))
    if m and m[-1].start() > 60:
        return cut[:m[-1].start() + 1]
    return cut.rsplit(" ", 1)[0] + "…"

def extract_char_name(raw_messages):
    char_name = "default"
    if len(raw_messages) > 0:
        last_msg = raw_messages[-1].get("content", "")
        match = re.search(r'\[Write the next reply only as (.*?)\.?\]', last_msg, re.IGNORECASE)
        if match:
            char_name = match.group(1).strip()
    if char_name == "default" and len(raw_messages) > 0 and raw_messages[0].get('role') == 'system':
        first_line = raw_messages[0]['content'].split('\n')[0]
        match = re.search(r"Write (.*?)'s next reply", first_line, re.IGNORECASE)
        if match:
            char_name = match.group(1).strip()
    char_name = re.sub(r'[^\w\s\-]', '', char_name).strip()
    if not char_name:
        char_name = "default"
    return char_name

# =========================================================
# ENDPOINTS
# =========================================================
@app.get("/v1/models")
async def get_models():
    return {"object": "list", "data": [{"id": "brainengine2-biopsychosocial", "object": "model", "owned_by": "custom"}]}

# =========================================================
# THE DIARY VIEWER — open http://127.0.0.1:8001/diary in your browser
# to see what your characters remember, believe, and where they are.
# =========================================================
@app.get("/diary", response_class=HTMLResponse)
async def diary_viewer():
    import html as _html
    esc = lambda s: _html.escape(str(s or ""))

    def fmt_time(ts):
        try:
            return time.strftime("%a %H:%M", time.localtime(float(ts)))
        except Exception:
            return ""

    chars = mem.list_characters()
    body = []
    total_pages = 0

    for name, updated in chars:
        st = mem.get_state(name)
        scene = st["scene"]
        pages = mem.get_pages(name, limit=30)
        total_pages += len(pages)
        ci = 0

        def card(inner):
            return f"<div class='card' style='animation-delay:{(ci+1)*70}ms'>{inner}</div>"

        parts = ["<div class='char'>",
                 "<div class='char-head'>",
                 f"<h2>{esc(name)}</h2>",
                 f"<span class='upd'>updated {fmt_time(updated)}</span>"]
        if st.get("last_emotion"):
            parts.append(f"<span class='chip'><span class='pulse'></span>{esc(st['last_emotion'])}</span>")
        parts.append("</div>")

        if st.get("last_thought"):
            parts.append(card("<h3>State of mind · the stream</h3>"
                              f"<p class='quote'>{esc(st['last_thought'])}</p>"))
            ci += 1

        parts.append(card("<h3>Life story</h3><p>" +
                     (esc(st["life_story"]) if st["life_story"] else
                      "<span class='muted'>Not yet — the Archivist writes this after ~40 diary pages.</span>") + "</p>"))
        ci += 1

        if st["unresolved_threads"]:
            parts.append(card("<h3>Unresolved threads</h3><ul>" +
                         "".join(f"<li>{esc(t)}</li>" for t in st["unresolved_threads"]) + "</ul>"))
            ci += 1

        if st["belief_page"]:
            parts.append(card(f"<h3>What they believe about you</h3><p>{esc(st['belief_page'])}</p>"))
            ci += 1

        scene_rows = []
        if scene.get("place") or scene.get("time"):
            scene_rows.append(f"<b>Where / when</b> &nbsp;{esc(scene.get('place',''))} · {esc(scene.get('time',''))}")
        if scene.get("atmosphere"):
            scene_rows.append(f"<b>Atmosphere</b> &nbsp;{esc(scene['atmosphere'])}")
        if scene.get("objects"):
            scene_rows.append("<b>Objects</b> &nbsp;" + " &nbsp;|&nbsp; ".join(esc(o) for o in scene["objects"]))
        if scene.get("today_plan"):
            scene_rows.append(f"<b>Today</b> &nbsp;{esc(scene['today_plan'])}")
        if scene.get("week_draft"):
            scene_rows.append(f"<b>This week</b> &nbsp;{esc(scene['week_draft'])}")
        if scene_rows:
            parts.append(card("<h3>Scene notebook</h3><p class='scene'>" + "<br>".join(scene_rows) + "</p>"))
            ci += 1

        if pages:
            rows = []
            for p in pages:
                prov = str(p.get("provenance") or "witnessed")
                prov_tag = "" if prov == "witnessed" else f" <span class='tag'>{esc(prov)}</span>"
                arch = " <span class='tag tag-arch'>archived</span>" if p["archived"] else ""
                pct = max(4, min(100, int((p["salience"] or 0) * 100)))
                rows.append(
                    f"<tr><td class='muted'>{fmt_time(p['created'])}</td>"
                    f"<td>{esc(p['content'])}{prov_tag}{arch}</td>"
                    f"<td><div class='bar' title='importance {p['salience']:.2f}'><i style='width:{pct}%'></i></div></td>"
                    f"<td class='muted'>{esc(p.get('emotion',''))}</td>"
                    f"<td class='rec' title='times recalled'>{p['access_count']}×</td></tr>")
            parts.append(card("<h3>Diary pages · newest first</h3>"
                         "<table><thead><tr><th></th><th>page</th><th>importance</th><th>feeling</th><th>recalled</th></tr></thead><tbody>"
                         + "".join(rows) + "</tbody></table>"))
            ci += 1
        else:
            parts.append(card("<h3>Diary pages</h3><p class='muted'>None yet.</p>"))
            ci += 1

        parts.append("</div>")
        body.append("".join(parts))

    page = f"""<!DOCTYPE html><html><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>The Diary · BrainEngine 2</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=Karla:wght@400;600;700&display=swap');
:root {{
  --bg:#0e1411; --card:#161f1a; --card2:#121a15; --line:#26332b;
  --ink:#e6e2d6; --muted:#87978c; --amber:#e8c47a; --sage:#9db4a6; --rose:#d99a8f;
}}
* {{ box-sizing:border-box }}
body {{
  margin:0; padding:52px 20px 90px; color:var(--ink);
  font-family:Karla,system-ui,sans-serif; font-size:16px; line-height:1.55;
  background:
    radial-gradient(900px 460px at 50% -8%, rgba(232,196,122,.10), transparent 62%),
    radial-gradient(700px 500px at 100% 100%, rgba(157,180,166,.05), transparent 60%),
    repeating-linear-gradient(0deg, rgba(255,255,255,.013) 0 1px, transparent 1px 3px),
    var(--bg);
}}
.wrap {{ max-width:880px; margin:0 auto }}
.masthead {{ border-bottom:1px solid var(--line); padding-bottom:20px }}
.masthead h1 {{ font-family:Fraunces,Georgia,serif; font-weight:600; font-size:2.7em; margin:0; letter-spacing:.01em }}
.masthead h1 .orn {{ color:var(--amber); font-size:.6em; vertical-align:.35em }}
.masthead p {{ color:var(--muted); margin:8px 0 0; font-size:.9em }}
.char {{ margin-top:52px }}
.char-head {{ display:flex; align-items:baseline; gap:14px; flex-wrap:wrap;
  border-bottom:1px solid var(--line); padding-bottom:10px }}
.char-head h2 {{ font-family:Fraunces,Georgia,serif; font-weight:600; font-size:1.9em; margin:0; color:var(--amber) }}
.char-head .upd {{ color:var(--muted); font-size:.8em }}
.chip {{ display:inline-flex; align-items:center; gap:7px; font-size:.78em; font-weight:600;
  color:var(--rose); border:1px solid rgba(217,154,143,.35); border-radius:999px; padding:3px 12px }}
.pulse {{ width:7px; height:7px; border-radius:50%; background:var(--rose); animation:pulse 2.2s ease-in-out infinite }}
@keyframes pulse {{ 0%,100% {{ opacity:.35; transform:scale(.85) }} 50% {{ opacity:1; transform:scale(1.2) }} }}
.card {{ background:linear-gradient(180deg, var(--card), var(--card2)); border:1px solid var(--line);
  border-radius:10px; padding:16px 20px; margin:12px 0; animation:rise .5s ease both;
  transition:transform .25s ease, border-color .25s ease, box-shadow .25s ease }}
.card:hover {{ transform:translateY(-2px); border-color:#3b4c41; box-shadow:0 10px 26px rgba(0,0,0,.35) }}
@keyframes rise {{ from {{ opacity:0; transform:translateY(10px) }} to {{ opacity:1; transform:none }} }}
.card h3 {{ font-size:.72em; text-transform:uppercase; letter-spacing:.16em; color:var(--sage);
  font-weight:700; margin:0 0 10px }}
.card p {{ margin:0 }}
.quote {{ font-family:Fraunces,Georgia,serif; font-style:italic; font-size:1.06em; color:#d9d3c3;
  border-left:2px solid var(--amber); padding-left:14px; white-space:pre-line }}
ul {{ margin:0; padding-left:20px }} li {{ margin:3px 0 }}
.muted {{ color:var(--muted) }}
.scene b {{ color:var(--sage) }}
table {{ width:100%; border-collapse:collapse; font-size:.88em }}
th {{ font-size:.68em; text-transform:uppercase; letter-spacing:.12em; color:var(--muted);
  font-weight:400; text-align:left; padding:6px 8px; border-bottom:1px solid var(--line) }}
td {{ padding:9px 8px; border-bottom:1px solid rgba(38,51,43,.55); vertical-align:top }}
tbody tr {{ transition:background .2s ease }}
tbody tr:hover {{ background:rgba(232,196,122,.05) }}
.bar {{ height:6px; border-radius:3px; background:#212b25; min-width:70px }}
.bar i {{ display:block; height:100%; border-radius:3px; background:linear-gradient(90deg,#8a6d3b,var(--amber)) }}
.rec {{ color:var(--amber); text-align:right; white-space:nowrap }}
.tag {{ font-size:.7em; padding:1px 8px; border-radius:999px; border:1px solid rgba(147,169,196,.4);
  color:#93a9c4; white-space:nowrap }}
.tag-arch {{ color:var(--muted); border-color:var(--line) }}
footer {{ margin-top:60px; color:var(--muted); font-size:.8em; border-top:1px solid var(--line); padding-top:14px }}
</style></head><body>
<div class='wrap'>
<header class='masthead'>
<h1>The Diary <span class='orn'>✦</span></h1>
<p>{len(chars)} character{'s' if len(chars) != 1 else ''} · {total_pages} page{'s' if total_pages != 1 else ''} on the shelf · updates after each kept reply — refresh anytime</p>
</header>
{''.join(body) if body else "<p class='muted' style='margin-top:34px'>The diary is empty so far. Pages appear after your first kept replies.</p>"}
<footer>BrainEngine 2 · everything above lives in memory.db · delete that file for a fresh start</footer>
</div>
</body></html>"""
    return page

@app.post("/v1/chat/completions")
async def chat_completions(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    raw_messages = data.get("messages", [])

    char_name = extract_char_name(raw_messages)
    turn_start = time.time()
    print(f"\n📨 New turn for {char_name}...")

    # =========================================================
    # OMNISCIENT BYPASS FOR "SETTING" (now with the scene notebook)
    # =========================================================
    if char_name.lower() == "setting":
        print("\n" + "="*75)
        print(f"🌍 OMNISCIENT ENVIRONMENT AGENT TRIGGERED | CHAR: {char_name}")
        print("="*75 + "\n")

        scene_txt = mem.all_scenes()
        setting_messages = copy.deepcopy(raw_messages)
        if scene_txt:
            setting_messages.append({"role": "system", "content": scene_txt})

        if data.get("stream"):
            async def setting_stream():
                full_parts = []
                try:
                    stream = await writer_client.chat.completions.create(
                        model=MODEL_NAME, messages=setting_messages, temperature=0.85,
                        frequency_penalty=0.2, presence_penalty=0.2, max_tokens=2000,
                        stream=True,
                        extra_headers={"HTTP-Referer": "http://localhost:8000", "X-Title": "BrainEngine2"})
                    try:
                        async for part in _stream_with_timeout(stream, STREAM_STALL_TIMEOUT):
                            if not part.choices:
                                continue
                            delta = part.choices[0].delta.content or ""
                            if delta:
                                full_parts.append(delta)
                                yield _sse_chunk(delta)
                    finally:
                        await stream.close()
                except Exception as e:
                    print(f"⚠️ Setting stream failed: {e}")
                if len("".join(full_parts).strip()) < 15:
                    yield _sse_chunk("*The environment shifts...*")
                yield _sse_final()
                yield "data: [DONE]\n\n"
            return StreamingResponse(setting_stream(), media_type="text/event-stream")

        final_text = "*The environment shifts...*"
        for attempt in range(3):
            try:
                response = await writer_client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=setting_messages,
                    temperature=0.85,
                    frequency_penalty=0.2,
                    presence_penalty=0.2,
                    max_tokens=2000,
                    extra_headers={"HTTP-Referer": "http://localhost:8000", "X-Title": "BrainEngine2"}
                )
                final_text = response.choices[0].message.content or ""
                if not final_text:
                    raise ValueError("Empty response")
                break
            except Exception as e:
                print(f"⚠️ Setting API Error on attempt {attempt+1}: {e}")
                await asyncio.sleep(2)

        return {
            "id": "chatcmpl-setting-brain",
            "object": "chat.completion",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": final_text},
                "finish_reason": "stop"
            }]
        }

    # =========================================================
    # SWIPE-SHIELD: confirm or drop the previous turn's diary entry
    # =========================================================
    pending = mem.pop_pending(char_name)
    if pending:
        history_contents = [m.get("content", "") for m in raw_messages if m.get("role") == "assistant"]
        if mem.is_kept(pending["fingerprint"], history_contents):
            background_tasks.add_task(run_chronicler, char_name, pending["payload"])
            print(f"✅ Previous reply kept — Chronicler will write {char_name}'s diary page.")
        else:
            print(f"🌀 Previous reply was swiped/edited — no diary page written for {char_name}.")

    # =========================================================
    # BUILD THE MEMORY PACKET (search is instant, no AI call)
    # =========================================================
    last_user_text = ""
    for m in reversed(raw_messages):
        if m.get("role") == "user":
            last_user_text = str(m.get("content", ""))
            break

    state = mem.get_state(char_name)
    # Smarter search: the moment + what the character was feeling (worried minds recall worried memories)
    query = (last_user_text[:600] + " " + state["last_emotion"]).strip()
    packet = mem.build_packet(char_name, query, diary_k=DIARY_PAGES_PER_TURN)
    memory_block = mem.format_packet(packet)
    scene_block = mem.format_scene(packet["scene"])

    # =========================================================
    # PREPARE THE DUAL MESSAGE STREAMS
    # =========================================================
    messages_mind, messages_synth = prepare_message_streams(raw_messages, char_name)

    # =========================================================
    # PHASE 1: SUBCONSCIOUS
    # =========================================================
    agent_temp = 0.3

    task_1_messages = build_agent_messages(window_messages(messages_mind, WINDOW_A1_BODY), AGENT_1_SOMATIC, additional_context=memory_block, is_json=True)
    res_1 = await async_llm_call(full_messages=task_1_messages, temp=agent_temp)
    a1_data = parse_or_fallback(res_1, {"valence": "Neutral", "arousal_level": "5.0", "dominance_level": "5.0", "physical_symptoms": "stillness"}, "A1_Somatic", char_name)

    try:
        arousal = float(a1_data.get("arousal_level", "5.0"))
    except:
        arousal = 5.0
    try:
        dominance = float(a1_data.get("dominance_level", "5.0"))
    except:
        dominance = 5.0

    valence = safe_get(a1_data, "valence", "Neutral")
    symptoms = safe_get(a1_data, "physical_symptoms", "stillness")

    body_context = f"CURRENT BODILY STATE: Arousal is {arousal}/10. Dominance is {dominance}/10. Valence is {valence}. Symptoms: {symptoms}. Let this physiological state heavily influence your analysis."

    msg_2 = build_agent_messages(window_messages(messages_mind, WINDOW_A2_DRIVES), AGENT_2_NEURO_SCHEMA, additional_context=memory_block + "\n" + body_context, is_json=True)
    msg_3 = build_agent_messages(window_messages(messages_mind, WINDOW_A3_MINDREADER), AGENT_3_TOM, additional_context=memory_block + "\n" + body_context, is_json=True)
    msg_4 = build_agent_messages(window_messages(messages_mind, WINDOW_A4_DAYDREAM), AGENT_4_DMN, additional_context=memory_block + "\n" + body_context, is_json=True)

    res_2, res_3, res_4 = await asyncio.gather(
        staggered_call(async_llm_call(full_messages=msg_2, temp=agent_temp), 0.0),
        staggered_call(async_llm_call(full_messages=msg_3, temp=agent_temp), 0.5),
        staggered_call(async_llm_call(full_messages=msg_4, temp=agent_temp), 1.0)
    )

    a2_data = parse_or_fallback(res_2, {
        "dopamine_target": "Maintaining current stability.",
        "serotonin_status": "Neutral ego.",
        "oxytocin_bond": "Cautious detachment.",
        "core_emotion": "Neutral.",
        "active_schema": "Baseline worldview."
    }, "A2_Neuro", char_name)

    a3_data = parse_or_fallback(res_3, {
        "perceived_user_intent": "Attempting to navigate the interaction.",
        "perceived_power_dynamic": "Analyzing the social dynamics.",
        "user_vulnerability_or_subtext": "Unknown subtext."
    }, "A3_ToM", char_name)

    a4_data = parse_or_fallback(res_4, {
        "intrusive_thought": "Background thought about mundane duties.",
        "current_daily_schedule": "08:00 AM - Wake up, 09:00 AM - 05:00 PM - Work.",
        "weekly_routine_draft": "Standard weekly routine."
    }, "A4_DMN", char_name)

    dopamine = safe_get(a2_data, "dopamine_target", "Maintaining current stability.")
    serotonin = safe_get(a2_data, "serotonin_status", "Neutral ego.")
    oxytocin = safe_get(a2_data, "oxytocin_bond", "Cautious detachment.")
    core_emotion = safe_get(a2_data, "core_emotion", "Neutral.")
    schema_trigger = safe_get(a2_data, "active_schema", "Baseline worldview.")

    tom_intent = safe_get(a3_data, "perceived_user_intent", "Attempting to navigate the interaction.")
    tom_dynamic = safe_get(a3_data, "perceived_power_dynamic", "Analyzing the social dynamics.")
    tom_subtext = safe_get(a3_data, "user_vulnerability_or_subtext", "Unknown subtext.")

    dmn_thought = safe_get(a4_data, "intrusive_thought", "Background thought about mundane duties.")
    dmn_daily_schedule = safe_get(a4_data, "current_daily_schedule", "08:00 AM - Wake up, 09:00 AM - 05:00 PM - Work.")
    dmn_weekly_routine = safe_get(a4_data, "weekly_routine_draft", "Standard weekly routine.")

    background_tasks.add_task(update_state_memory, char_name, dmn_daily_schedule, dmn_weekly_routine)

    # =========================================================
    # PHASE 2: EXECUTIVE
    # =========================================================
    executive_context = f"""
    [PHASE 1 SUBCONSCIOUS DATA]
    - Somatic State: Arousal {arousal}/10, Dominance {dominance}/10, Valence: {valence}. Symptoms: {symptoms}
    - Neurochemical Drives: Dopamine: {dopamine} | Serotonin: {serotonin} | Oxytocin: {oxytocin}
    - Core Emotion: {core_emotion}
    - Active Schema: {schema_trigger}
    - Theory of Mind: User intent '{tom_intent}'. Power dynamic '{tom_dynamic}'. User Subtext '{tom_subtext}'.
    - DMN Intrusive Thought: {dmn_thought}
    - DMN Today's Schedule: {dmn_daily_schedule}
    - DMN Weekly Routine: {dmn_weekly_routine}
    """

    msg_5 = build_agent_messages(window_messages(messages_mind, WINDOW_A5_DIRECTOR), AGENT_5_EXECUTIVE, additional_context=memory_block + "\n" + executive_context, is_json=True)
    res_5 = await async_llm_call(full_messages=msg_5, temp=agent_temp, pres_pen=0.4, is_writer=True)

    a5_data = parse_or_fallback(res_5, {
        "internal_motive": "Proceed logically.",
        "subtext_strategy": "Direct honesty.",
        "speech_intent": "Respond to user.",
        "vocal_delivery": "Neutral.",
        "physical_choreography": "Maintain normal posture."
    }, "A5_Exec", char_name)

    internal_motive = safe_get(a5_data, "internal_motive", "Proceed logically.")
    subtext_strategy = safe_get(a5_data, "subtext_strategy", "Direct honesty.")
    speech_intent = safe_get(a5_data, "speech_intent", "Respond to user.")
    vocal_delivery = safe_get(a5_data, "vocal_delivery", "Neutral.")
    physical_choreography = safe_get(a5_data, "physical_choreography", "Maintain normal posture.")

    print("\n" + "="*75)
    print(f"🧠 BRAINENGINE2 HIERARCHY | CHAR: {char_name}")
    print("="*75)
    print(f"🩸 A1 (Somatic): {valence} | Arousal {arousal}/10 | Dominance {dominance}/10 | {symptoms}")
    print(f"🧪 A2 (Neuro)  : Emotion [{_short(core_emotion, 120)}]")
    print(f"👁️ A3 (ToM)    : Intent [{_short(tom_intent, 80)}] | Subtext [{_short(tom_subtext, 80)}]")
    print(f"🌫️ A4 (DMN)    : {_short(dmn_thought, 100)}")
    print(f"📖 Memory      : {len(packet['diary_pages'])} diary pages recalled | Life story: {'yes' if packet['life_story'] else 'not yet'} | Threads: {len(packet['unresolved_threads'])}")
    print(f"⚖️ A5 (Exec)   : Motive [{_short(internal_motive, 80)}] | Strategy [{_short(subtext_strategy, 80)}]")
    print(f"🎬 A5 (Direct) : Speech [{_short(speech_intent, 80)}] | Choreo [{_short(physical_choreography, 100)}]")
    print("="*75)
    for i, pg in enumerate(packet["diary_pages"], 1):
        print(f"   📄 Recalled {i}: {_short(pg, 100)}")
    if packet["diary_pages"]:
        print("="*75)
    print()

    # =========================================================
    # PHASE 3: SYNTHESIS (THE CAMERA)
    # =========================================================
    synthesis_context = f"""
    [EXECUTE THIS CHOREOGRAPHY - SCREENPLAY STYLE]
    - Subtext Strategy: {subtext_strategy}
    - Speech Intent: {speech_intent}
    - Vocal Delivery: {vocal_delivery}
    - Physical Choreography: {physical_choreography}

    {scene_block}

    INSTRUCTIONS: Write the next response as a script. Use the choreography and props to convey the subtext strategy. Short, punchy, macroscopic actions. Do NOT pad the length. Play Conversational Tennis (say a few words and stop).
    """

    task_6 = build_agent_messages(window_messages(messages_synth, WINDOW_A6_WRITER), AGENT_6_SYNTHESIS, additional_context=synthesis_context, is_json=False)

    # =========================================================
    # THOUGHT BLOCK: 3-line essence + full deep dive (for your eyes).
    # Everything after [DEEP DIVE] is display-only: when the server feeds
    # the last 3 thoughts back to the agents next turn, it cuts the dive
    # and keeps only the essence — so the models never re-read the wall.
    # =========================================================
    snapshot_text = (
        f"{_short(core_emotion, 220)}\n"
        f"{_short(subtext_strategy, 140)} {_short(speech_intent, 140)}\n"
        f"On my mind: {_short(dmn_thought, 160)}"
    )
    thought_block = (
        f"<think>\n{snapshot_text}\n"
        f"\n[DEEP DIVE]\n"
        f"🩸 Somatic: {valence}, Arousal {arousal}/10, Dominance {dominance}/10 — {symptoms}\n"
        f"🧪 Neuro: Emotion [{core_emotion}]\n   Schema [{schema_trigger}]\n"
        f"   Dopamine [{dopamine}]\n   Serotonin [{serotonin}]\n   Oxytocin [{oxytocin}]\n"
        f"👁️ ToM: Intent [{tom_intent}]\n   Dynamic [{tom_dynamic}]\n   Subtext [{tom_subtext}]\n"
        f"🌫️ DMN: {dmn_thought}\n   Today: {dmn_daily_schedule}\n   Week: {dmn_weekly_routine}\n"
        f"⚖️ Exec: Motive [{internal_motive}]\n   Strategy [{subtext_strategy}]\n"
        f"🎬 Directing: Speech [{speech_intent}] | Vocal [{vocal_delivery}]\n   Choreo [{physical_choreography}]\n"
        f"[/DEEP DIVE]\n</think>\n\n"
    )

    analysis_summary = (
        f"Somatic: {valence}, arousal {arousal}/10, dominance {dominance}/10. Symptoms: {symptoms}\n"
        f"Emotion: {core_emotion}\nSchema: {_short(schema_trigger, 400)}\n"
        f"ToM: intent '{_short(tom_intent, 300)}', dynamic '{_short(tom_dynamic, 300)}', subtext '{_short(tom_subtext, 300)}'\n"
        f"DMN: {_short(dmn_thought, 300)} | Today: {_short(dmn_daily_schedule, 400)} | Week: {_short(dmn_weekly_routine, 300)}\n"
        f"Executive: motive '{internal_motive}' | strategy '{subtext_strategy}' | speech '{speech_intent}' | choreo '{physical_choreography}'"
    )

    # =========================================================
    # STREAMING PATH (SillyTavern asked for stream=true)
    # The thought snapshot streams first, then the prose as it is written.
    # =========================================================
    if data.get("stream"):
        print(f"✍️ A6 (Writer)  : streaming reply...")
        turn_payload = {
            "user_msg": last_user_text[:2000],
            "reply": "",  # filled after the stream completes
            "analysis": analysis_summary
        }

        async def event_stream():
            full_parts = []
            a6_start = time.time()
            try:
                yield _sse_chunk(thought_block)
                stream = await writer_client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=task_6,
                    temperature=0.85,
                    frequency_penalty=0.3,
                    presence_penalty=0.3,
                    max_tokens=2000,
                    stream=True,
                    extra_headers={"HTTP-Referer": "http://localhost:8000", "X-Title": "BrainEngine2"}
                )
                try:
                    async for part in _stream_with_timeout(stream, STREAM_STALL_TIMEOUT):
                        if not part.choices:
                            continue
                        delta = part.choices[0].delta.content or ""
                        if delta:
                            full_parts.append(delta)
                            yield _sse_chunk(delta)
                finally:
                    await stream.close()
            except Exception as e:
                print(f"⚠️ A6 stream failed: {e}")
            if len("".join(full_parts).strip()) < 15:
                fallback = "*The character grimaces, struggling to process their thoughts.*"
                full_parts.append(fallback)
                yield _sse_chunk(fallback)
            final_text = "".join(full_parts)
            yield _sse_final()
            yield "data: [DONE]\n\n"
            turn_payload["reply"] = final_text[:2000]
            mem.stash_turn(char_name, mem.reply_fingerprint(final_text), turn_payload)
            mem.set_last_thought(char_name, snapshot_text)
            print(f"📤 Reply streamed to SillyTavern for {char_name} "
                  f"({time.time()-a6_start:.0f}s, {len(final_text)} chars, turn took {time.time()-turn_start:.0f}s total)")

        return StreamingResponse(event_stream(), media_type="text/event-stream", background=background_tasks)

    # =========================================================
    # CLASSIC PATH (stream off)
    # =========================================================
    print(f"✍️ A6 (Writer)  : composing reply...")
    a6_start = time.time()
    final_roleplay_text = await async_llm_call(
        full_messages=task_6,
        expect_json=False,
        temp=0.85,
        freq_pen=0.3,
        pres_pen=0.3,
        max_tokens=2000,
        is_writer=True
    )
    print(f"✍️ A6 (Writer)  : reply composed in {time.time()-a6_start:.0f}s ({len(final_roleplay_text)} chars)")

    # =========================================================
    # STASH THE TURN (diary page written only if the user KEEPS this reply)
    # =========================================================
    mem.stash_turn(char_name, mem.reply_fingerprint(final_roleplay_text), {
        "user_msg": last_user_text[:2000],
        "reply": final_roleplay_text[:2000],
        "analysis": analysis_summary
    })
    mem.set_last_thought(char_name, snapshot_text)

    print(f"📤 Reply sent to SillyTavern for {char_name} (turn took {time.time()-turn_start:.0f}s total)")

    return {
        "id": "chatcmpl-brainengine2",
        "object": "chat.completion",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": thought_block + final_roleplay_text},
            "finish_reason": "stop"
        }]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8001, reload=True)

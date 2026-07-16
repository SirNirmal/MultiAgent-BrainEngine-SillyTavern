import asyncio
import json
import re
import copy
import os
import threading
from fastapi import FastAPI, Request, BackgroundTasks
from openai import AsyncOpenAI

app = FastAPI()

# =========================================================
# CONFIGURATION
# =========================================================
# ⚠️ USER: INSERT YOUR API CREDENTIALS AND MODELS HERE ⚠️

# --- MAIN SETTINGS (Required) ---
API_KEY = "INSERT_YOUR_API_KEY_HERE" 
MODEL_NAME = "INSERT_YOUR_MODEL_NAME_HERE"      # e.g., "anthropic/claude-3.5-sonnet"
BASE_URL = "INSERT_YOUR_PROVIDER_URL_HERE"      # e.g., "https://openrouter.ai/api/v1"

# --- ADVANCED: DUAL-PROVIDER SETUP (Optional, saves money) ---
# Want to run the backend logic (Agents 1-5) on a cheap or free local model?
# Put those credentials here. 
# IF YOU LEAVE THESE BLANK (""), THE SCRIPT WILL JUST USE YOUR MAIN SETTINGS FOR EVERYTHING!
LOGIC_API_KEY = ""   # e.g., "lm-studio" for local, or an OpenRouter key
LOGIC_BASE_URL = ""  # e.g., "http://127.0.0.1:1234/v1" for local
LOGIC_MODEL = ""     # e.g., "qwen/qwen-2.5-72b-instruct"

# =========================================================
# SMART CLIENT ROUTING (Auto-detects if you are using Dual Setup)
# =========================================================
writer_client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)

# Fallback to Main Settings if Advanced Settings are left blank
active_logic_api = LOGIC_API_KEY if LOGIC_API_KEY.strip() != "" else API_KEY
active_logic_url = LOGIC_BASE_URL if LOGIC_BASE_URL.strip() != "" else BASE_URL
ACTIVE_LOGIC_MODEL = LOGIC_MODEL if LOGIC_MODEL.strip() != "" else MODEL_NAME

logic_client = AsyncOpenAI(base_url=active_logic_url, api_key=active_logic_api)

STATE_DB_FILE = "biopsychosocial_state.json"
state_lock = threading.Lock()  # Added to prevent file corruption from race conditions

# =========================================================
# BULLETPROOF JSON PARSING & STATE MANAGEMENT
# =========================================================
def load_all_states():
    with state_lock:
        if os.path.exists(STATE_DB_FILE):
            try:
                with open(STATE_DB_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
    return {}

def save_all_states(states):
    with state_lock:
        with open(STATE_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(states, f, indent=4)

def get_current_state(character_name="default"):
    states = load_all_states()
    return states.get(character_name, {
        "character_name": character_name,
        "cognitive_fatigue": 20,
        "last_known_dmn_daily": "08:00 AM - Wake up, 09:00 AM - 05:00 PM - Work.",
        "last_known_dmn_weekly": "Standard weekly routine."
    })

def update_state_memory(char_name, daily_sched, weekly_sched):
    states = load_all_states()
    state = states.get(char_name, {"character_name": char_name, "cognitive_fatigue": 20})
    
    default_daily = "08:00 AM - Wake up, 09:00 AM - 05:00 PM - Work."
    default_weekly = "Standard weekly routine."
    
    if daily_sched and daily_sched != default_daily:
        state["last_known_dmn_daily"] = daily_sched
    if weekly_sched and weekly_sched != default_weekly:
        state["last_known_dmn_weekly"] = weekly_sched
        
    states[char_name] = state
    save_all_states(states)

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
        parsed = json.loads(cleaned)
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
# DUAL-STREAM MEMORY ENGINE (Short-Term Thought Retention)
# =========================================================
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
            # SYNTHESIS (Agent 6): 100% blind to ALL thoughts.
            msg_synth['content'] = re.sub(r'<think>.*?</think>\s*', '', content, flags=re.DOTALL)
            
            # MIND (Agents 1-5): Keep thoughts ONLY for this character's last 3 messages.
            if i not in recent_own_indices:
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
    
    # Select the correct client and model based on the agent type!
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
                extra_headers={"HTTP-Referer": "http://localhost:8000", "X-Title": "Biopsychosocial Brain"}
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
  "physical_symptoms": "Describe heart rate, tension, etc."
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
- PROXEMICS & PROPS: Since you can only choreograph macroscopic actions, use SPACE and OBJECTS to show emotion.
- BEHAVIORAL VOLATILITY: Humans shift tactics. DO NOT repeat the exact same subtext strategy or physical choreography from previous turns. Keep them dynamic.

RULES FOR ATTENTION:
- DMN LEAK: If Arousal is LOW (< 5.0), allow the DMN intrusive thought to distract you.
- TUNNEL VISION: If Arousal is HIGH (> 6.5), strictly ignore the DMN/schedule. Focus entirely on the immediate threat or scene.
- HIJACK: If Cognitive Fatigue is HIGH (> 70) OR Arousal is explosive (> 8.5), you suffer Ego Depletion. You snap, lash out, or surrender. 

CRITICAL RULE FOR STAGE DIRECTIONS:
- You MUST only choreograph macroscopic stage directions (e.g., Walks away, crosses arms, leans on the desk, slams a book).
- DO NOT choreograph biological micro-movements (e.g., breathing, swallowing, heartbeats, muscles clenching).

Output strict JSON format:
{
  "hijack_occurred": false,
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

CONVERSATIONAL TENNIS & PACING:
- NO SPEECHES / NO MONOLOGUES: Real humans do not deliver theatrical speeches. They say a few sentences and then STOP to let the other person react. Hand the microphone back to the User quickly.
- ACTION-ONLY TURNS: If the 'Speech Intent' is 'Silence / Action Only', DO NOT WRITE ANY DIALOGUE. Just write the physical stage directions and end the turn. This is highly encouraged for realism.

Output plain narrative text with dialogue. Keep the prose sparse, punchy, and conversational. Do not return JSON here."""

# =========================================================
# BACKGROUND TASK & ENDPOINTS
# =========================================================
async def staggered_call(coro, delay_seconds):
    if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)
    return await coro

async def update_cognitive_load(char_name, arousal, valence):
    print("🔄 [BACKGROUND] Updating Cognitive Fatigue...")
    state = get_current_state(char_name)
    fatigue = state.get("cognitive_fatigue", 20)
    
    if arousal >= 7.5 or valence.lower() == "negative":
        fatigue += 15
    elif arousal <= 4.0 and valence.lower() == "positive":
        fatigue -= 20
    else:
        fatigue -= 5 
        
    fatigue = max(0, min(100, fatigue))
    state["cognitive_fatigue"] = fatigue
    save_all_states({**load_all_states(), char_name: state})
    print(f"✅ [BACKGROUND] {char_name} Fatigue is now {fatigue}/100")

@app.get("/v1/models")
async def get_models():
    return {"object": "list", "data": [{"id": "frankenstein-biopsychosocial", "object": "model", "owned_by": "custom"}]}

@app.post("/v1/chat/completions")
async def chat_completions(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    raw_messages = data.get("messages", [])
    
    # 1. EXTRACT CHARACTER NAME SAFELY
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

    # =========================================================
    # OMNISCIENT BYPASS FOR "SETTING"
    # =========================================================
    if char_name.lower() == "setting":
        print("\n" + "="*75)
        print(f"🌍 OMNISCIENT ENVIRONMENT AGENT TRIGGERED | CHAR: {char_name}")
        print("="*75)
        print("Setting is reading all internal thoughts and generating standard response...\n")
        
        for attempt in range(3):
            try:
                response = await writer_client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=raw_messages, # Raw messages contain ALL hidden <think> blocks
                    temperature=0.85,
                    frequency_penalty=0.2,
                    presence_penalty=0.2,
                    max_tokens=2000,
                    extra_headers={"HTTP-Referer": "http://localhost:8000", "X-Title": "Biopsychosocial Brain"}
                )
                final_text = response.choices[0].message.content
                if not final_text:
                    raise ValueError("Empty response")
                break
            except Exception as e:
                print(f"⚠️ Setting API Error on attempt {attempt+1}: {e}")
                await asyncio.sleep(2)
                final_text = "*The environment shifts...*"
                
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
    # 2. PREPARE THE DUAL MESSAGE STREAMS
    # =========================================================
    messages_mind, messages_synth = prepare_message_streams(raw_messages, char_name)

    state = get_current_state(char_name)
    fatigue = state.get("cognitive_fatigue", 20)
        
    # =========================================================
    # PHASE 1: SUBCONSCIOUS (STAGGERED CONCURRENT)
    # =========================================================
    agent_temp = 0.3 
    
    task_1_messages = build_agent_messages(messages_mind, AGENT_1_SOMATIC, is_json=True)
    res_1 = await async_llm_call(full_messages=task_1_messages, temp=agent_temp)
    a1_data = parse_or_fallback(res_1, {"valence": "Neutral", "arousal_level": "5.0", "physical_symptoms": "stillness"}, "A1_Somatic", char_name)
    
    try:
        arousal = float(a1_data.get("arousal_level", "5.0"))
    except:
        arousal = 5.0
        
    valence = safe_get(a1_data, "valence", "Neutral")
    symptoms = safe_get(a1_data, "physical_symptoms", "stillness")

    body_context = f"CURRENT BODILY STATE: Arousal is {arousal}/10. Valence is {valence}. Symptoms: {symptoms}. Let this physiological state heavily influence your analysis."

    msg_2 = build_agent_messages(messages_mind, AGENT_2_NEURO_SCHEMA, additional_context=body_context, is_json=True)
    msg_3 = build_agent_messages(messages_mind, AGENT_3_TOM, additional_context=body_context, is_json=True)
    msg_4 = build_agent_messages(messages_mind, AGENT_4_DMN, additional_context=body_context, is_json=True)
    
    # Run Agents 2, 3, and 4 simultaneously but stagger to prevent OpenRouter API drops
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
    - Somatic State: Arousal {arousal}/10, Valence: {valence}. Symptoms: {symptoms}
    - Neurochemical Drives: Dopamine: {dopamine} | Serotonin: {serotonin} | Oxytocin: {oxytocin}
    - Core Emotion: {core_emotion}
    - Active Schema: {schema_trigger}
    - Theory of Mind: User intent '{tom_intent}'. Power dynamic '{tom_dynamic}'. User Subtext '{tom_subtext}'.
    - DMN Intrusive Thought: {dmn_thought}
    - DMN Today's Schedule: {dmn_daily_schedule}
    - DMN Weekly Routine: {dmn_weekly_routine}
    - COGNITIVE FATIGUE: {fatigue}/100.
    """
    
    msg_5 = build_agent_messages(messages_mind, AGENT_5_EXECUTIVE, additional_context=executive_context, is_json=True)
    res_5 = await async_llm_call(full_messages=msg_5, temp=agent_temp, pres_pen=0.4)
    
    a5_data = parse_or_fallback(res_5, {
        "hijack_occurred": False, 
        "internal_motive": "Proceed logically.",
        "subtext_strategy": "Direct honesty.",
        "speech_intent": "Respond to user.",
        "vocal_delivery": "Neutral.",
        "physical_choreography": "Maintain normal posture."
    }, "A5_Exec", char_name)
    
    hijack = a5_data.get("hijack_occurred", False)
    internal_motive = safe_get(a5_data, "internal_motive", "Proceed logically.")
    subtext_strategy = safe_get(a5_data, "subtext_strategy", "Direct honesty.")
    speech_intent = safe_get(a5_data, "speech_intent", "Respond to user.")
    vocal_delivery = safe_get(a5_data, "vocal_delivery", "Neutral.")
    physical_choreography = safe_get(a5_data, "physical_choreography", "Maintain normal posture.")

    print("\n" + "="*75)
    print(f"🧠 BIOPSYCHOSOCIAL HIERARCHY | FATIGUE: {fatigue}/100 | CHAR: {char_name}")
    print("="*75)
    print(f"🩸 A1 (Somatic): {valence} | Arousal {arousal}/10 | {symptoms}")
    print(f"🧪 A2 (Neuro)  : Emotion [{core_emotion}] | Schema [{schema_trigger[:40]}...]")
    print(f"👁️ A3 (ToM)    : Sees User Dynamic [{tom_dynamic[:40]}...] | Subtext [{tom_subtext[:40]}...]")
    print(f"🌫️ A4 (DMN)    : Thought -> {dmn_thought[:60]}...")
    print(f"📅 A4 (Sched)  : Today [{dmn_daily_schedule[:40]}...] | Week [{dmn_weekly_routine[:40]}...]")
    print(f"⚖️ A5 (Exec)   : Motive [{internal_motive}] | Strategy [{subtext_strategy}]")
    print(f"🎬 A5 (Direct) : Speech [{speech_intent}] | Vocal [{vocal_delivery}]")
    print(f"🎬 A5 (Choreo) : {physical_choreography}")
    print("="*75 + "\n")

    # =========================================================
    # PHASE 3: SYNTHESIS (THE CAMERA)
    # =========================================================
    synthesis_context = f"""
    [EXECUTE THIS CHOREOGRAPHY - SCREENPLAY STYLE]
    - Subtext Strategy: {subtext_strategy}
    - Speech Intent: {speech_intent}
    - Vocal Delivery: {vocal_delivery}
    - Physical Choreography: {physical_choreography}
    
    INSTRUCTIONS: Write the next response as a script. Use the choreography and props to convey the subtext strategy. Short, punchy, macroscopic actions. Do NOT pad the length. Play Conversational Tennis (say a few words and stop).
    """
    
    task_6 = build_agent_messages(messages_synth, AGENT_6_SYNTHESIS, additional_context=synthesis_context, is_json=False)
    
    final_roleplay_text = await async_llm_call(
        full_messages=task_6, 
        expect_json=False, 
        temp=0.85, 
        freq_pen=0.3, 
        pres_pen=0.3,
        max_tokens=2000,
        is_writer=True 
    )
    
    thought_block = f"<think>\n🩸 Somatic: {valence}, Arousal {arousal}/10\n🧪 Neuro: Emotion [{core_emotion}] | Schema [{schema_trigger}]\n👁️ ToM: Intent [{tom_intent}] | User Subtext [{tom_subtext}]\n🌫️ DMN: {dmn_thought} | Today: {dmn_daily_schedule} | Week: {dmn_weekly_routine}\n⚖️ Exec (Fatigue {fatigue}): Motive [{internal_motive}] | Strategy [{subtext_strategy}]\n🎬 Directing: Speech [{speech_intent}] | Choreo [{physical_choreography}]\n</think>\n\n"
    
    background_tasks.add_task(update_cognitive_load, char_name, arousal, valence)
    
    return {
        "id": "chatcmpl-biopsych-brain",
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

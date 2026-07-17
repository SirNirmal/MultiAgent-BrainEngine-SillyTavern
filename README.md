**[CLICK TO DOWNLOAD MultiAgent BrainEngine](https://github.com/DonBananas/MultiAgent-BrainEngine-SillyTavern/archive/refs/heads/main.zip) - Read [How to Install & Use](https://github.com/DonBananas/MultiAgent-BrainEngine-SillyTavern/tree/main#how-to-install--use)**
# MultiAgent-BrainEngine-SillyTavern

### Stop roleplaying with puppets. Give them a mind and a life.

If you’ve spent any time doing AI roleplay, you’ve probably noticed what I call the "puppet problem." Most characters exist in a total vacuum. They have zero agency, sitting passively in a blank room, waiting for you to type and ready to agree with whatever you say. They don't have a complex inner life and they certainly don't have a schedule. 

I wanted to change that. 

This project is a Python proxy server that intercepts SillyTavern's prompts and routes them through a 6-agent brain simulation. It divides the character's cognition into two equally important halves: a deep internal world and an active life outside of your conversation.

#### Part 1: A deep internal world (The Brain)
Real humans don't just process text; we process experience. Before the character decides what to say, the simulation routes the prompt through their subconscious:
*   **The Somatic Core:** Calculates their body's physical reflexes first (heart rate, muscle tension, tensing up) because human biology reacts before the conscious mind does.
*   **The Neurochemical Engine:** Tracks their ego , goals  and bonding.
*   **Core Schemas:** Filters your words through their past traumas, worldviews and memories.
*   **Theory of Mind:** Actively reads between the lines, trying to figure out your hidden subtext and vulnerabilities instead of just taking your words at face value.
*   **Background noise:** Even during intense moments, their mind will flash to random new thoughts, flash of memories, random associations. This adds humanity to the characters, they are not just deterministc machines.


#### Part 2: An active life outside the scene (The Routine)
I also wanted to cure the AI's tendency to wait around in a void. Through the Default Mode Network (Agent 4), the character maintains their own daily life:
*   **A flexible hour-by-hour daily schedule:** The character actually knows what time of day it is. If they are talking to you at 11:30 AM, they know they have family lunch at 12:30 PM, or tutoring at 2:00 PM. If you drag out the conversation, they will eventually have to leave because they have places to go.
*   **A weekly calendar:** They know what their obligations are tomorrow, on Thursday, or over the weekend.

This breaks the usual AI sycophancy. The characters don't exist just to cater to you; they have a complex inner world and they have somewhere to be. You are simply stepping into a scene in progress.

---

## How to Install & Use

1.  Install Python (Make sure to check "Add Python to PATH" during installation).
2.  Download and extract the folder to your computer.
3. Open a terminal inside the folder by right-clicking on any empty white space inside the folder and select "Open in Terminal" from the menu. A black or blue command window will pop up (Note: *If you don't see "Open in Terminal", you can also just click the folder's address bar at the very top, type `cmd` and press Enter*). 
   Once the terminal is open, install the requirements by typing the line below, then press Enter: 
   ```bash
   pip install -r requirements.txt
4.  Open `server.py` in a text editor and put your API Key, Model Name, and Provider URL at the top where it says `INSERT_YOUR_...` OPTIONAL: *there's an option for a dual API provider setup, it's explained inside server.py.* 
5.  To run the server: Double click `start_server.bat` (or run `python server.py` in your terminal).
6.  Open SillyTavern. Go to the **API Connections** tab (the plug icon).
7.  Select **Chat Completion** -> **Custom (OpenAI-compatible)**.
8.  Put `http://127.0.0.1:8001/v1` in the Base URL field and hit Connect!
9.  ⚠️ **CRITICAL STEP (THE SCRIPT WILL NOT WORK CORRECTLY WITHOUT THIS):**
    *   Click the **Advanced Formatting** tab (the "A" icon on the top menu bar).
    *   Find the **Reasoning** section and turn on **"Add to prompt"**.
    *   Set the **"Max number of thinking blocks to add"** to a high number (eg. 100). 
    *   *Why?* The Python backend is hardcoded to parse the last 3 thoughts of the active character. Setting this to a high value in SillyTavern allow the memory engine to function. The script will aumatically remove all words that don't belong to the preivous 3 thoughts of our specific character in the chat, so no worry about token consumption here.
10. If Streaming is turned on on SillyTavern, you MUST turn it OFF . Otherwise You won't get the output. Open AI Response Configuration on Sillytavern (the three horizonal lines on the top bar) and uncheck Streaming.  

---

## 🌍 The "Setting" Bypass (Your Omniscient Sandbox)

If you create a character card in SillyTavern named exactly **Setting**, the Python script will recognize it and automatically bypass the 6-agent biopsychosocial brain. 

Instead of treating "Setting" like a human, the script treats it as an **Omniscient Narrator**. It takes the raw, unedited chat history—containing the hidden `<think>` blocks, schedules and emotions of *every single character* in the chat—and feeds it directly to the Setting. 

Unlike standard characthers, who are set to have access only to their own previous thoughts, the Setting bypasses this anti-telepathy firewall, it knows everything And because it runs entirely off the Character Card you build for it in SillyTavern, **you can customize it to do whatever you want.** 

Here are just a few ways you can have fun with the Setting card:

*   **The Master Timekeeper:** Because the Setting reads the internal DMN schedules of every character, you can prompt your Setting card to act as a scene-manager. Ask it to succinctly output the exact location and current activity of every character in the house at a given time based on their routines.
*   **Psychological Mirroring:** You can instruct the Setting card to spawn weather, events or NPCs that deliberately reflect or disrupt the psychological states of the characters. If a character is secretly feeling guilty (hidden in their Neurochemical agent), the Setting can make the room feel claustrophobic or spawn a knock at the door to trigger their paranoia.
*   **The Meta-Tracker:** You can format the Setting card to act as a UI overlay. Tell it to read all the hidden `<think>` blocks and output a clean, formatted summary of  plot points, everyone's current emotional states and stress levels in a single message.
*   **The Dungeon Master:** Let the Setting throw random curveballs into the characters' carefully planned daily routines and watch their Executive agents scramble to adapt.

The Setting agent uses a standard, fast LLM pass (`temp=0.85`), making it a perfect, highly creative sandbox. Build the card however you want and give it whatever rules you like.

---

## 💸 Why use 6 agents?

Running six separate API calls per turn is expensive. If you are roleplaying with a long chat history, this architecture will cost you significantly more in API tokens than a standard single-prompt setup. 

However, standard LLM roleplay suffers from three fundamental architectural flaws that cannot be fixed within a single linear prompt:

#### 1. Replicating real neurological cascade
In the human brain, cognitive processing is a cascade, not a straight line. Before you consciously "think," your autonomic nervous system reacts. 

Our script replicates this exact biological sequence:
1.  **The Amygdala (Agent 1) fires first and fast.** It reads the scene and determines raw physical arousal (heart rate, tensing, breathing). 
2.  **The Subconscious Channels** (Agents 2, 3, and 4) receive this physical context. Just like a real human, their thoughts are *colored* by their physical arousal (e.g., high arousal tenses their Theory of Mind and makes their DMN more anxious).
3.  **Planning and action**: the last steps are planning and action, this is where Agent 5 and 6 come.

#### 2. Preventing domain contamination
While Agents 2, 3, and 4 are all influenced by the Somatic core (A1), **they are kept completely blind to each other's thoughts.** 

In a standard single-prompt LLM, different cognitive domains contaminate each other because the AI is forced to write them in a single, continuous stream of text. 
*   If the AI starts its thought process by writing about its daily schedule (DMN), those words mathematically bias its neural network, warping its subsequent process. 
*   By separating these domains into isolated streams, the **DMN** can worry about its chores, the **Theory of Mind** can analyze social vulnerabilities, and the **Neurochemical Engine** can calculate ego and drives. They all feel the somatic tension (A1), but they process it in their own specialized domains without polluting one another.
*   In a real brain, subconsicous thoughts involve different regions that act simultaneously, not sequentially.

#### 3. Breaking down tasks into smaller parts
If you ask a single LLM to analyze a situation, generate the first instintive reaction, filter it through a character's values, think through a plan of action and generate dialogu,e you wil get subpare results. LLMs response quality decrease ithe more complex their instructions are. Breaking down the instructions and distributing them to different and separate agents addresses this issue. Each Agent is focused on a specific task, this allows them to perform it at their best.

#### 4. Enforcing  "show, don't Tell"
If a single LLM writes both the character's internal thoughts and their external dialogue in one pass, the thoughts will inevitably "bleed" into the dialogue. The character will start acting exactly like they feel, destroying any subtext or masking.

To prevent this, **Agent 6 (the Writer) is kept 100% blind to the thoughts of Agents 1-4.** It only receives the final, physical choreography and dialogue dictated by Agent 5 (The Executive Functions). This strict firewall forces the AI to act like a real human interlocutor  describing only literal, physical reality of the person they are itnreacting with, forcing the emotional subtext to be shown, not told as if through telepathy.

---

## 🧠 How It Works
```
[ST Chat History] 
       │
       ▼
[prepare_message_streams] ──► (Separates Mind and Synthesis histories)
       │
       ▼
 [Agent 1: Somatic] 
       │
       ▼
 [body_context] ──► [Agent 2: Neuro/Schema] 
                ──► [Agent 3: Theory of Mind]   (Runs concurrently, staggered by 0.5s)
                ──► [Agent 4: DMN] 
       │
       ▼
 [executive_context] ──► [Agent 5: Executive] (Conscious Decision Maker)
                               │
                               ▼
                        [Agent 6: Synthesis] (Strict Screenwriter Prose)
```

### Phase 1: The Physiological Trigger
*   **Agent 1 (Somatic Core):** Runs first. It reads the user's prompt and determines the character's raw physical reaction (heart rate, muscle tension, valence, and arousal). Just like human biology, the nervous system reacts before the brain processes what is happening.

### Phase 2: The Subconscious (Staggered Concurrent Execution)
As soon as A1 finishes, the script feeds that bodily data into three other agents. To prevent the API from dropping simultaneous requests, the script staggers their execution by a fraction of a second, running them concurrently:
*   **Agent 2 (Neurochemical Engine):** Calculates dopamine drives, ego (serotonin), bonding (oxytocin), and filters the scene through a core schema based on the physical arousal.
*   **Agent 3 (Theory of Mind):** Reads between the lines of what the user is doing, attempts to guess the user's hidden subtext, and calculates the power dynamic.
*   **Agent 4 (Default Mode Network):** Completely ignores the user and focuses on the character's background life. It generates an intrusive thought, updates their hour-by-hour daily schedule, and drafts their weekly routine.

### Phase 3: The Executive Director
*   **Agent 5 (Executive Cortex):** Gathers all the independent JSON data from Phases 1 and 2, plus the character's current Cognitive Fatigue. It looks at all the contradictory subconscious data and makes a tactical decision: What is my actual motive? Am I going to speak, or just stay silent? What is my physical choreography?
    *(If Cognitive Fatigue or Arousal is are high, Agent 5 first expereinces "Tunnel vision". If levels become too high, Agent 5 suffers  "Ego Depletion Hijack" and loses control of their manners).*

### Phase 4: The Synthesis (The Camera)
*   **Agent 6 (Screenwriter):** Takes the final directions from Agent 5 and translates them into macroscopic stage directions, props, proxemics, and punchy dialogue. It is strictly forced to write pure, objective prose without inner narration.

---

## 💾 The Dual-Stream Memory Engine

To prevent characters from reading each other's minds (Telepathy) and to stop the AI from repeating itself endlessly (Contextual Drift), the script divides the incoming SillyTavern chat history into two separate message streams:

1.  **The Mind Stream (Agents 1-5):** Passes the full chat history to the subconscious agents, but strips out all other characters' `<think>` blocks. It keeps *only* the current active character's thoughts, and *only* from their last 3 messages. This provides short-term emotional continuity without causing infinite loops.
2.  **The Synthesis Stream (Agent 6):** Aggressively strips 100% of all `<think>` blocks from all characters in the history. This ensures that the Screenwriter remains completely blind to the internal monologues, keeping the final output focused strictly on observable actions and dialogue.

---

## 🔄 Background tasks
While sending the reply back to SillyTavern, the server runs quick background tasks to update the character's conversational fatigue and save their active schedules. It also uses thread-safe locking to ensure multiple characters in a group chat never corrupt your local memory file.

## Known issues
*   If the API call is rejected for unsafe content by your chosen provider, the Agents will output  placeholders. With less moderated models,  this usually affect only  1 or 2 agents, dialogue is usually always generated. Still, this will  negatively affect the quality of the chat. More censored models may block more agents and dialogue.

*   API providers with very low rate limits per minute (RPM) may not work with this script, always check the log you can see in server terminal if you face issues. If you experience rate limits, find another provider with higher rate limits per minute that can accomodate the several cascading calls required to run the multi-agent system.

*   The script has been tested using SillyTavern default preset and extensions. Interactions with custom presets and extensions that affect thought and memory processing are unknown.

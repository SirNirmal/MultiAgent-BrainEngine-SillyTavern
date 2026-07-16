# MultiAgent-BrainEngine-SillyTavern

This is a standalone Python proxy server for SillyTavern. Instead of sending your prompt straight to an LLM, this script intercepts the prompt and routes it through a 6-Agent cognitive hierarchy:

*   **Somatic Core**: Simulates physical arousal and symptoms.
*   **Neurochemical Engine**: Tracks dopamine, serotonin, and active schemas.
*   **Theory of Mind**: Analyzes user intent and power dynamics.
*   **Default Mode Network (DMN)**: Generates intrusive thoughts and maintains daily/weekly schedules.
*   **Executive Cortex**: Dictates tactics and conversational intent.
*   **Synthesis**: Formats everything into a punchy, macroscopic roleplay response.

It features dual-stream memory, ego-depletion/fatigue tracking, and active background schedules.

---

## How to Install & Use

1.  Install Python (Make sure to check "Add Python to PATH" during installation).
2.  Download this repository to your computer.
3.  Open a terminal inside the folder and install the requirements by running: 
    ```bash
    pip install -r requirements.txt
    ```
4.  Open `server.py` in a text editor and put your API Key, Model Name, and Provider URL at the top.
5.  To run the server: Double click `start_server.bat` (or run `python server.py` in your terminal).
6.  Open SillyTavern. Go to the **API Connections** tab (the plug icon).
7.  Select **Chat Completion** -> **Custom (OpenAI-compatible)**.
8.  Put `http://127.0.0.1:8001/v1` in the Base URL field and hit Connect!
9.  ⚠️ **CRITICAL STEP (THE SCRIPT WILL NOT WORK CORRECTLY WITHOUT THIS):**
    *   Click the **Advanced Formatting** tab (the "A" icon on the top menu bar).
    *   Find the **Reasoning** section and turn on **"Add to prompt"**.
    *   Set the **"Max number of thinking blocks to add"** to **3** (or up to 5 for larger group chats). 
    *   *Why?* The Python backend is hardcoded to parse the last 3 thoughts of the active character. Setting this to 3 in SillyTavern prevents unnecessary token overhead while allowing the memory engine to function.

---

## 🧠 How It Works Under the Hood (The Architecture)

Rather than forcing a single LLM to think in a linear, biased chain, the proxy uses **Staggered Concurrent Execution** to mimic the human brain's non-sequential, parallel processing. By separating these functions, it prevents later cognitive steps from biasing the raw, initial reactions.

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

## 🔄 Background Tasks (State Management)

While Phase 4 is returning the text to SillyTavern, the script runs non-blocking background tasks:
*   **Stateful Fallback Memory:** Saves the character's generated DMN schedules to a local `biopsychosocial_state.json` file. If the API ever glitches or censors its response, the parser automatically restores the last known schedule so the character never suffers amnesia.
*   **Cognitive Fatigue:** Calculates the somatic stress of the turn and updates the character's cumulative fatigue level (0-100) for the next round.
*   **Race-Condition Protection:** Utilizes thread-safe locking to prevent file corruption during multi-character group chats.

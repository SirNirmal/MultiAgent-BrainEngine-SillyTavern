# MultiAgent-BrainEngine-SillyTavern

This is a standalone Python proxy server for SillyTavern. Instead of sending your prompt straight to an LLM, this script intercepts the prompt and routes it through a 6-Agent cognitive hierarchy:
1. **Somatic Core:** Simulates physical arousal and symptoms.
2. **Neurochemical Engine:** Tracks dopamine, serotonin, and active schemas.
3. **Theory of Mind:** Analyzes user intent and power dynamics.
4. **Default Mode Network (DMN):** Generates intrusive thoughts and maintains daily/weekly schedules.
5. **Executive Cortex:** Dictates tactics and conversational intent.
6. **Synthesis:** Formats everything into a punchy, macroscopic roleplay response.

It features dual-stream memory, ego-depletion/fatigue tracking, and active background schedules.

## How to Install & Use
1. Install [Python](https://www.python.org/downloads/) (Make sure to check "Add Python to PATH" during installation).
2. Download this repository to your computer (Click the green "Code" button -> "Download ZIP" and extract it).
3. Open a terminal inside the folder and install the requirements by running: `pip install -r requirements.txt`
4. Open `server.py` in a text editor (like Notepad) and put your API Key, Model Name, and Provider URL at the top where it says `INSERT_YOUR_...`
5. **To run the server:** Just double click `start_server.bat` (or run `python server.py` in your terminal).
6. Open SillyTavern. Go to the **API Connections** tab (the plug icon).
7. Select **Chat Completion** -> **Custom (OpenAI-compatible)**.
8. Put `http://127.0.0.1:8001/v1` in the Base URL field and hit Connect!
9. ⚠️ **CRITICAL STEP (THE SCRIPT WILL NOT WORK WITHOUT THIS):** Click the **Advanced Formatting** tab (the "A" icon on the top menu bar). 
10. Find the **Reasoning** section, turn on **"Add to prompt"**, and set the number to the right to a reasonably high number (like `1000`, `2000`, or more). **If you do not do this, SillyTavern will delete the agents' internal thoughts and the proxy will fail!**

---

## 🧠 How It Works Under the Hood (The Architecture)

Rather than forcing a single LLM to think in a linear, biased chain, the proxy uses **Asynchronous Staggered Execution** to mimic the human brain's non-sequential, parallel processing. By separating these functions, it prevents later cognitive steps from biasing the raw, initial reactions. The thought process is broken down into 3 distinct phases:

### Phase 1: The Subconscious (Concurrent Execution)
*   **Agent 1 (Somatic Core):** Runs first. It reads the user's prompt and determines the character's raw physical reaction (Heart rate, muscle tension, valence, and arousal).
*   *As soon as A1 finishes, the script feeds that bodily data into three other agents and runs them at the exact same time so they cannot bias one another:*
    *   **Agent 2 (Neurochemical):** Calculates dopamine drives, ego (serotonin), bonding (oxytocin), and filters the scene through a core schema.
    *   **Agent 3 (Theory of Mind):** Reads between the lines of what the user is doing. Attempts to guess the user's hidden subtext and calculates the power dynamic.
    *   **Agent 4 (Default Mode Network):** Completely ignores the user and focuses on the character's background life. It generates an intrusive thought, updates their hour-by-hour daily schedule, and drafts their weekly routine.

### Phase 2: The Executive Director
*   **Agent 5 (Executive Cortex):** Gathers all the independent JSON data from Phase 1, plus the character's current **Cognitive Fatigue**. It looks at all the contradictory subconscious data and makes a tactical decision: *What is my actual motive? Am I going to speak, or just stay silent? What is my physical choreography?*
*   *(If Cognitive Fatigue or Arousal is too high, Agent 5 suffers an "Ego Depletion Hijack" and loses control of their manners).*

### Phase 3: The Synthesis (The Camera)
*   **Agent 6 (Screenwriter):** Takes the final directions from Agent 5. **Agent 6 is completely blind to the thoughts of Agents 1-4.** This is done intentionally so the AI cannot write flowery, poetic internal narration. Agent 6 is strictly forced to translate Agent 5's strategy into macroscopic stage directions, props, proxemics, and punchy dialogue. 

### Background Tasks (Memory Engine)
While Phase 3 is returning the text to SillyTavern, the script quietly runs background tasks to save the character's updated Cognitive Fatigue (which rises and falls based on the stress of the conversation) and their updated DMN schedule into a local `biopsychosocial_state.json` file so it remembers it for the next turn.

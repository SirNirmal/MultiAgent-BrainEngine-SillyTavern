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

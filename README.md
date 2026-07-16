# MultiAgent-BrainEngine-SillyTavern

### Stop roleplaying with puppets. Give them a mind and a life.

If you’ve spent any time doing AI roleplay, you’ve probably noticed what I call the "puppet problem." Most characters exist in a total vacuum. They have zero agency, sitting passively in a blank room, waiting for you to type and ready to agree with whatever you say. They don't have a complex inner life and they certainly don't have a schedule. 

I wanted to change that. 

This project is a Python proxy server that intercepts SillyTavern's prompts and routes them through a 6-agent brain simulation. It divides the character's cognition into two equally important halves: a deep, messy internal world and an active life outside of your conversation.

#### Part 1: A deep internal world (The Brain)
Real humans don't just process text; we process experience. Before the character decides what to say, the simulation routes the prompt through their subconscious:
*   **The Somatic Core:** Calculates their body's physical reflexes first (heart rate, muscle tension, tensing up) because human biology reacts before the conscious mind does.
*   **The Neurochemical Engine:** Tracks their ego (serotonin), goals (dopamine), and bonding (oxytocin).
*   **Core Schemas:** Filters your words through their past traumas, worldviews and memories.
*   **Theory of Mind:** Actively reads between the lines, trying to figure out your hidden subtext and vulnerabilities instead of just taking your words at face value.

#### Part 2: An active life outside the scene (The Routine)
I also wanted to cure the AI's tendency to wait around in a void. Through the Default Mode Network (Agent 4), the character maintains their own daily life:
*   **A flexible hour-by-hour daily schedule:** The character actually knows what time of day it is. If they are talking to you at 11:30 AM, they know they have family lunch at 12:30 PM, or tutoring at 2:00 PM. If you drag out the conversation, they will eventually have to leave because they have places to go.
*   **A weekly calendar:** They know what their obligations are tomorrow, on Thursday, or over the weekend.
*   **Mundane background noise:** Even during intense moments, their mind will flash to random new thoughts, flash of memories, random associations. This add humanity to the characters, they are not just deterministc machines.

This breaks the usual AI sycophancy. The characters don't exist just to cater to you; they have a complex inner world and they have somewhere to be. You are simply stepping into a scene in progress.

---

## How to Install & Use

1.  Install Python (Make sure to check "Add Python to PATH" during installation).
2.  Download this repository to your computer.
3.  Open a terminal inside the folder and install the requirements by running: 
    ```bash
    pip install -r requirements.txt
    ```
4.  Open `server.py` in a text editor and put your API Key, Model Name, and Provider URL at the top where it says `INSERT_YOUR_...`.
5.  To run the server: Double click `start_server.bat` (or run `python server.py` in your terminal).
6.  Open SillyTavern. Go to the **API Connections** tab (the plug icon).
7.  Select **Chat Completion** -> **Custom (OpenAI-compatible)**.
8.  Put `http://127.0.0.1:8001/v1` in the Base URL field and hit Connect!
9.  ⚠️ **CRITICAL STEP (THE SCRIPT WILL NOT WORK CORRECTLY WITHOUT THIS):**
    *   Click the **Advanced Formatting** tab (the "A" icon on the top menu bar).
    *   Find the **Reasoning** section and turn on **"Add to prompt"**.
    *   Set the **"Max number of thinking blocks to add"** to a high number (eg. 100). 
    *   *Why?* The Python backend is hardcoded to parse the last 3 thoughts of the active character. Setting this to 3 in SillyTavern prevents unnecessary token overhead while allowing the memory engine to function.

---

## 💸 Why use 6 agents?

Running six separate API calls per turn is undeniably expensive. If you are roleplaying with a long chat history, this architecture will cost you six times more in API credits than a standard single-prompt setup. 

However, standard LLM roleplay suffers from three fundamental architectural flaws that **cannot be fixed within a single prompt**, no matter how clever the system instructions are. Here is why the cost is justified, and how this multi-agent system accurately mimics human neurology:

### 1. The "Linear Contamination" Problem (Parallel vs. Serial Processing)
When a single LLM does all its thinking in one linear text block (like a standard `<think>` block), early tokens inescapably bias later tokens. If a character is insulted and the AI writes, *"I am furious and humiliated"* in the first sentence of its thought process, the entire rest of its cognitive analysis is warped. It can no longer objectively analyze the user's hidden insecurities (Theory of Mind) or its own values and  long-term goals, because the neural network has locked onto "anger" as the dominant context.

The human brain does not process reality in a straight, linear line. When you are threatened, your amygdala (fear/anger), your medial prefrontal cortex (Theory of Mind/intent) and your default mode network (background anxieties) fire *simultaneously* in parallel circuits. 
By separating the subconscious into independent agents, we prevent LLM cross-contamination. The Somatic core can scream, *"My heart is pounding in terror,"* while the Theory of Mind engine coolly calculates, *"The user is only posturing out of insecurity,"* without one overriding the other.

### 2. Simulating True Cognitive Dissonance
Real humans are messy, contradictory and constantly at war with themselves. We want to run away but our pride anchors us to the floor. We harbor deep resentment, but we desperately crave the other person's validation.

Cognitive dissonance happens because different regions of the brain have competing evolutionary drives. Single-prompt LLMs are terrible at holding these contradictions. Because they are trained to write cohesive, logical paragraphs, they will always try to "smooth out" their thoughts to make them mathematically agree.

By running Agents 2, 3, and 4 in completely isolated parallel streams, we force the AI to generate raw, uncooperative and highly contradictory data. When Agent 5 (the Executive Anterior Cingulate Cortex) gathers this data, it is forced to act like a real human brain: making a messy, flawed choice to resolve the agonizing friction between competing internal voices.

### 3. Enforcing the "Show, Don't Tell" Firewall (The Social Mask)
If a single LLM writes both a character's internal thoughts and their external dialogue in one pass, the thoughts will inevitably "bleed" into the dialogue. The character will start acting exactly like they feel, destroying all subtext, mystery, and conversational masking.

In reality, our external behavior (motor cortex and speech centers) does not broadcast our raw neurochemical soup. Humans are masters of masking. If we feel an meotion, our actions don't necessarily reveal it through subtext like it would happne in a novel. Unless our emotions are very strong, we can hide them. For very emotional and hard situation, there are specific methods I've implemented but they still act upon on a different layer than the external actions, affecting it indirectly. Real life is not a novel.

---

## 🧠 How It Works Under the Hood (The Architecture)
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
While sending the reply back to SillyTavern, the server runs quick background tasks to update the character's conversational fatigue and save their active schedules. It also uses thread-safe locking to ensure multiple characters in a group chat never corrupt your local memory file.

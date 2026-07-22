**[CLICK TO DOWNLOAD MultiAgent BrainEngine 2 (ZIP)](https://github.com/DonBananas/MultiAgent-BrainEngine-SillyTavern/archive/refs/heads/main.zip) — then follow the [install guide below](#installation). Requires [SillyTavern](https://github.com/SillyTavern/SillyTavern)**
# MultiAgent BrainEngine 2

### Stop roleplaying with puppets. Give them a mind, a memory, and a life.

MultiAgent BrainEngine 2 is a an extremely easy to setup and user-friendly Python proxy server for SillyTavern. It sits between SillyTavern and your LLM provider, and routes every reply through a **6-agent biopsychosocial brain** — so characters react with their body first, filter the world through their own psychology, read between your lines, maintain their own daily lives, and only then decide what to say and do. **Two more agents work in the background**, quietly keeping the character's diary after every reply.

**Eight agents in total: six craft the reply you read, two maintain the memory behind it.**

---

## New in version 2 — the quick version

Version 2 builds on the [original MultiAgent BrainEngine](https://github.com/DonBananas/MultiAgent-BrainEngine-SillyTavern) by DonBananas. The 6-agent brain is preserved intact — and finally gets what it needed:

- 📖 **Long-term memory** — every character keeps a private diary: important moments are remembered, trivial ones fade, the right memory resurfaces exactly when something reminds them of it, and old pages compress into a life story
- 🌍 **Scene awareness** — characters know where they are, what time it is, and where every object is
- 💭 **Beliefs about you** — that change slowly, like a real person's
- 🧠 **Sharp reasoning even in very long chats** — the degradation is gone
- ✍️ **Streaming** works on or off, plus a friendly launcher and a visual diary viewer
- **Kept from v1:** the dual-provider setup, the anti-telepathy firewall, the omniscient "Setting" card

The rest of this page: first, *why* a multi-agent brain at all — then everything v2 adds in detail — then installation.

---

## Why a multi-agent brain?

Standard LLM roleplay asks one model to do everything in a single pass: react, psychoanalyze, read your subtext, plan a response, and write the prose. That is exactly what LLMs are bad at. Splitting the mind into specialized agents fixes four structural flaws that **no prompt can fix**:

### 1. Short tasks make the model sharper

An LLM's output quality degrades the more you ask of it at once. Tell one model to *"feel this, analyze that, guess my motives, decide what to do, and write it beautifully"* in a single instruction, and every part comes out mediocre — the instructions compete with each other inside one generation.

Give six agents **one narrow job each** — feel, analyze, read, daydream, decide, write — and every one of those jobs gets the model's full capacity. Small, focused tasks are simply where LLMs perform best.

### 2. No contamination between domains

In a single stream of thought, everything biases everything that comes after it. If the model starts by writing the character's daily schedule, those words mathematically drag the emotion off course; if it writes the emotion first, the mind-reading gets contaminated by it. One continuous stream cannot keep cognitive domains apart.

Here, the subconscious agents — drives, mind-reading, daydreaming — think **in parallel, completely blind to each other**. Each processes the scene in its own domain without polluting the others, the way separate brain regions do. And the agents never re-read their own old walls of analysis — only a 3-line essence travels through the chat — so the character doesn't anchor to yesterday's conclusions and parrot them forever.

### 3. Show, don't tell — enforced, not requested

If one model writes both the inner thoughts *and* the dialogue, the thoughts inevitably bleed into the words: the character announces exactly what it feels, and subtext dies. Telling the model "don't do that" never fully works — the thoughts are right there in its context.

Here the Writer agent is kept **100% blind to every thought**. It receives only the Director's decision — the motive, the line to deliver, the choreography. Feelings can therefore only surface through action, props, distance, and timing. Real subtext, guaranteed by architecture instead of requested by prompt.

### 4. The body decides first

Real cognition is a cascade, not a checklist: your nervous system reacts *before* your mind interprets. Agent 1 (the body) fires first and alone — and its reading of arousal, tension, and valence **colors everything that follows**. A pounding heart makes the mind-reader more suspicious and the daydreamer more anxious, exactly as it would in a person. Order matters, and a single-pass prompt cannot reproduce it.

---

## The problem version 2 solves

The multi-agent brain gives a character a mind — but a mind without a memory still rots. Most AI characters exist in a total vacuum: they forget what happened thirty messages ago, they have no idea where they are, objects vanish from their hands, and their feelings about you reset every few messages. The longer the chat, the worse it gets — the character slowly flattens back into a sycophantic puppet.

Version 2 fixes this the way a real mind works: important moments are written down, unimportant ones fade, the right memory resurfaces exactly when something reminds the character of it, and the world around them stays put.

---

## What version 2 adds — in detail

### 📖 A real long-term memory — the Diary

In v1, a character remembered only their daily schedule and their last three thoughts. In v2, every kept moment of the story is written into a private diary:

- **Diary pages** — what happened, with an *importance score* (promises and betrayals rank high, small talk low) and the *feeling* attached to it
- **Smart recall** — each turn, the server searches the diary (full-text search blended with importance and recency) and hands the character only the few memories that matter *right now*. Mention her sister → the memories about her sister surface
- **Plasticity** — memories behave like real ones: they get **stronger every time they're recalled** and slowly **fade when neglected** (Ebbinghaus-style decay). Watch the recall counter grow on the memories that keep mattering
- **A life story** — once ~40 pages accumulate, the background *Archivist* compresses old pages into a flowing autobiographical summary, plus a list of **unresolved threads** — open promises, grudges, and questions that stay alive until they're actually resolved
- **Swipe-proof** — a diary page is only written once your *next* message proves you kept the reply. Swipe or edit a reply away and it was never remembered

### 🌍 Scene awareness & object permanence

Each character keeps a **scene notebook**: where they are, what time it is, the atmosphere, **every object and where it is** ("the letter — in her jacket pocket"), and their plans for the day and week.

- The body feels the cold room; the director moves through the place; the writer describes what's actually there
- Objects stay where they were put — no more picking up a letter that was burned five messages ago
- Plans are checked against the real clock — characters actually leave when they have somewhere to be

### 💭 Beliefs that change slowly

Each character keeps a **belief page**: what they currently believe about you, and how strongly. Like a real person: first impressions stick, deep beliefs resist a single event (one kind dinner won't erase old distrust), and unreinforced beliefs slowly fade. No more personality whiplash between messages.

### 🧠 Sharp reasoning in long chats

Two fixes for the degradation that creeps into long roleplays:

- **Per-agent chat windows** — each agent reads only the slice of the chat it needs; the diary carries everything older, so nothing important is ever lost
- **Compact thought snapshots** — the chat history carries only a 3-line essence of recent thoughts, so the agents never drown re-reading their own old analysis. The **full deep dive** (every agent's complete reasoning) is still there — expand the thought bubble in SillyTavern to read it

### ✍️ Streaming & robustness

- Works with SillyTavern **streaming on or off** (v1 required streaming off) — replies type themselves out live
- A watchdog cuts dead provider streams after 90 seconds instead of hanging forever

### 🖥️ A friendly launcher & the Diary viewer

- A **setup window** for your API settings — no code editing — with a *Test connection* button and a built-in SillyTavern guide that opens automatically on first run
- The **Diary viewer** at `http://127.0.0.1:8001/diary` — see, per character: their life story, unresolved threads, what they believe about you, their scene notebook, and their newest diary pages with importance and recall counts

### Kept from version 1

- The **6-agent hierarchy**: Somatic (body) → Neuro/Schema (drives & core beliefs) → Theory of Mind (reading your subtext) → Default Mode Network (daydreams & schedule) → Executive (the decision) → Writer (the prose)
- The **dual-provider setup**: run the background thinking on a cheap or local model, keep the good model for decisions and prose
- The **anti-telepathy firewall**: a character only ever sees their *own* last three thoughts. They never read another character's thoughts, diary, beliefs, or scene — they only witness each other's words and actions, like real people
- The **"Setting" card bypass**: a character card named exactly `Setting` becomes an omniscient narrator — in v2 it reads *every* character's scene notebook, so it knows where everyone is and what's around them

---

## How it works

The first six agents run while you wait and produce the reply. The last two run *afterwards*, in the background on the cheap model — you never wait for them, and they never influence what the character says; they only record it.

```
[SillyTavern chat history]
        │
        ▼
[Memory packet]  ← diary search + life story + beliefs + scene   (instant, local, free)
        │
        ▼
[Agent 1 · Somatic]        → the body reacts first
        │
        ▼
[Agents 2–4 · Neuro · Theory of Mind · Daydream]   (in parallel, colored by the body)
        │
        ▼
[Agent 5 · Executive]      → the decision: speak, act, or stay silent
        │
        ▼
[Agent 6 · Writer]         → the reply you read  (kept 100% blind to all thoughts)
        │
        ▼   after the reply, in the background, on the cheap model:
[Agent 7 · Chronicler]     → writes diary pages · updates scene & beliefs  (kept replies only)
[Agent 8 · Archivist]      → compresses old pages into the life story      (rare)
```

---

## Installation

### Requirements

- **Windows** (for Linux/macOS note below)
- **Python 3.10+** — during installation, tick **"Add Python to PATH"**
- **SillyTavern**
- An **OpenAI-compatible API key** — OpenRouter, any compatible provider, or a local model server (LM Studio, etc.)

### Steps

1. **Download** the project (the ZIP link at the top, or clone it).

2. **Double-click `Install Requirements.bat`** — installs everything the engine needs, once.

3. **Double-click `Start BrainEngine.bat`** — the setup window opens.
   - Enter your **API key**, **model name** and **base URL** for the main provider (used for decisions and writing).
   - Optionally tick the box to use a second, cheaper model for the background thinking.
   - Press **Continue** — the window closes and the server starts in that same console.
   - *First run:* the SillyTavern guide opens by itself on top of the setup window.

4. **In SillyTavern**, go to the **API Connections** tab (the plug icon) → **Chat Completion** → **Custom (OpenAI-compatible)** → put `http://127.0.0.1:8001/v1` in the **Base URL** field → **Connect**.

5. ⚠️ **Critical step — the engine needs this:**
   - Open the **Advanced Formatting** tab (the "A" icon).
   - In the **Reasoning** section, turn on **"Add to prompt"**.
   - Set **"Max number of thinking blocks to add"** high (e.g. **100**).
   - *Why:* after every reply, SillyTavern tucks the character's hidden thoughts away; this setting hands them back to the engine, which is how the character keeps the thread of its inner voice. Without it the engine still runs, but that continuity is lost. (No token worry — the engine keeps only the character's own last three thoughts and erases the rest.)

6. **Chat.** Open `http://127.0.0.1:8001/diary` anytime to watch the minds at work.

**Linux / macOS:** run `pip install -r engine/requirements.txt`, then `python engine/launcher.py`.

### The rhythm of memory — what to expect

- Diary pages appear **one turn after** a kept reply (the swipe-proof design at work)
- The **life story** appears after ~40 pages
- The console shows the memory machinery live: `📄 Recalled …` (which memories were handed over), `📖 Chronicler: diary updated`, `📚 Archivist: compressed …`

---

## Cost & providers

Like the original, the engine makes several API calls per turn — that's the price of the cascade. To keep it affordable:

- Agents 1–4 and both background agents (Chronicler, Archivist) can run on a **cheap or local model** via the optional second provider in the setup window; the main provider is used only for the decision and the prose you read
- Providers with very low per-minute rate limits may struggle with the concurrent calls — check the console if replies fail
- Heavily content-filtered providers may return placeholders for some agents (dialogue usually survives)

---

## Folder structure

```
MultiAgent BrainEngine 2/
├── Start BrainEngine.bat        ← launch (setup window → Continue → server)
├── Install Requirements.bat     ← run once on a new machine
├── Uninstall Requirements.bat   ← removes the engine's packages
└── engine/
    ├── launcher.py              ← setup window + SillyTavern guide
    ├── server.py                ← the proxy server (8 agents)
    ├── memory_engine.py         ← the diary (local SQLite)
    ├── requirements.txt
    ├── config.example.json      ← settings template
    ├── config.json              ← your settings (created by the setup window)
    └── memory.db                ← your characters' diaries (created on first run)
```

Your API keys and diaries live only on your machine, in `engine/config.json` and `engine/memory.db`. Delete `memory.db` anytime for a fresh start.

---

## Credits & thanks

- Built on the [MultiAgent BrainEngine for SillyTavern](https://github.com/DonBananas/MultiAgent-BrainEngine-SillyTavern) by **DonBananas** — the 6-agent biopsychosocial hierarchy, the anti-telepathy dual streams, and the Setting bypass are his design.
- The memory system follows the research line of modern agent-memory work: episodic memory streams with reflection and salience-based retrieval (Park et al., *Generative Agents*, 2023; Packer et al., *MemGPT*, 2023), hybrid retrieval with Reciprocal Rank Fusion (Cormack et al., 2009) and BM25, diversity re-ranking with Maximal Marginal Relevance (Carbonell & Goldstein, 1998), Ebbinghaus-style forgetting (1885), and source monitoring for memory provenance (Johnson et al., 1993).

### Special thanks

- **[N0819](https://github.com/N0819)** — creator of the Sonder Engine (MIT). Not a single line of his code was copied here, but his research-driven approach to agent memory — salience-scored episodes, hybrid retrieval, autobiographical consolidation, belief plasticity — was the direct inspiration for this project's memory system.
- **Freaky Frankestein** — whose SillyTavern presets sparked ideas that grew into this engine.

## License

[MIT](LICENSE)

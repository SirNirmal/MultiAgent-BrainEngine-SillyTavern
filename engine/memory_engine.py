# --- START OF FILE memory_engine.py ---
"""
memory_engine.py — The Diary.

Long-term memory for the SillyMind server, adapted from the Sonder Engine's
research-based memory system (salience-scored episodic memories, provenance,
Ebbinghaus-style decay with strengthening-on-recall, autobiographical
consolidation with unresolved threads).

Storage is a single local file: memory.db (SQLite, created automatically).
No external services. Everything is per character name.

Three kinds of state live here:
  1. Diary pages (memories)   — what happened, how important, how it felt.
  2. Character sheet of self  — life story, unresolved threads, belief page.
  3. Scene notebook           — place, time, atmosphere, objects, plans.

Plus the swipe-shield: a "pending turn" is only written into the diary once
the NEXT request proves the user kept the reply (no swipe / no delete).
"""

import sqlite3
import json
import os
import re
import math
import time
import hashlib
import threading

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.db")
_lock = threading.Lock()

RECENCY_HALF_LIFE = 14 * 86400      # diary pages fade from "fresh" over ~2 weeks
STRENGTH_HALF_LIFE = 30 * 86400     # unrecalled pages weaken over ~a month (Ebbinghaus)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories(
  id INTEGER PRIMARY KEY,
  char_name TEXT NOT NULL,
  content TEXT NOT NULL,
  salience REAL NOT NULL DEFAULT 0.5,
  provenance TEXT NOT NULL DEFAULT 'witnessed',
  emotion TEXT NOT NULL DEFAULT '',
  access_count INTEGER NOT NULL DEFAULT 0,
  last_accessed REAL NOT NULL DEFAULT 0,
  created REAL NOT NULL,
  archived INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS char_state(
  char_name TEXT PRIMARY KEY,
  life_story TEXT NOT NULL DEFAULT '',
  unresolved_threads TEXT NOT NULL DEFAULT '[]',
  belief_page TEXT NOT NULL DEFAULT '',
  scene_json TEXT NOT NULL DEFAULT '{}',
  last_emotion TEXT NOT NULL DEFAULT '',
  updated REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pending_turn(
  char_name TEXT PRIMARY KEY,
  reply_fingerprint TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created REAL NOT NULL
);
"""

_FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
  USING fts5(content, content='memories', content_rowid='id');
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
  INSERT INTO memories_fts(rowid, content) VALUES (new.id, new.content);
END;
CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
  INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.id, old.content);
END;
"""

DEFAULT_SCENE = {
    "place": "", "time": "", "atmosphere": "",
    "objects": [], "today_plan": "", "week_draft": ""
}


def _connect():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the database file and tables on server startup. Safe to call every boot."""
    with _lock, _connect() as conn:
        conn.executescript(_SCHEMA)
        try:
            conn.executescript(_FTS_SCHEMA)
        except sqlite3.Error as e:
            print(f"⚠️ Diary full-text search unavailable (falling back to recency): {e}")
        # gentle migrations for existing diaries
        for col, ddl in (("last_thought", "ALTER TABLE char_state ADD COLUMN last_thought TEXT NOT NULL DEFAULT ''"),):
            try:
                conn.execute(ddl)
            except sqlite3.Error:
                pass  # column already there


def _clamp(v, lo=0.0, hi=1.0):
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return 0.5


# =========================================================
# CHARACTER STATE (life story, threads, beliefs, scene)
# =========================================================
def get_state(char_name):
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM char_state WHERE char_name=?", (char_name,)).fetchone()
        if row is None:
            conn.execute("INSERT INTO char_state(char_name, updated) VALUES(?,?)",
                         (char_name, time.time()))
            row = conn.execute("SELECT * FROM char_state WHERE char_name=?", (char_name,)).fetchone()
    scene = dict(DEFAULT_SCENE)
    try:
        scene.update(json.loads(row["scene_json"] or "{}"))
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        threads = json.loads(row["unresolved_threads"] or "[]")
        if not isinstance(threads, list):
            threads = []
    except (json.JSONDecodeError, TypeError):
        threads = []
    return {
        "life_story": row["life_story"] or "",
        "unresolved_threads": threads,
        "belief_page": row["belief_page"] or "",
        "scene": scene,
        "last_emotion": row["last_emotion"] or "",
        "last_thought": row["last_thought"] or "",
    }


def set_last_thought(char_name, thought):
    with _lock, _connect() as conn:
        conn.execute("UPDATE char_state SET last_thought=? WHERE char_name=?",
                     ((thought or "")[:800], char_name))


# =========================================================
# DIARY RETRIEVAL (search + salience + recency, with plasticity)
# =========================================================
def _fts_candidates(conn, char_name, query_text, limit=25):
    words = []
    for w in re.findall(r"[a-zA-Z']{4,}", (query_text or "").lower()):
        if w not in words:
            words.append(w)
        if len(words) >= 12:
            break
    if not words:
        return []
    fts_q = " OR ".join(words)
    try:
        return conn.execute(
            """SELECT m.*, bm25(memories_fts) AS rank
               FROM memories m JOIN memories_fts f ON m.id = f.rowid
               WHERE memories_fts MATCH ? AND m.char_name=? AND m.archived=0
               ORDER BY rank LIMIT ?""",
            (fts_q, char_name, limit)).fetchall()
    except sqlite3.Error:
        return []


def search_diary(char_name, query_text, k=6):
    """Find the diary pages relevant right now. Recalled pages get STRONGER
    (access_count bump) — memory that is used is memory that survives."""
    now = time.time()
    with _lock, _connect() as conn:
        rows = _fts_candidates(conn, char_name, query_text)
        if not rows:
            rows = conn.execute(
                """SELECT *, 0.0 AS rank FROM memories
                   WHERE char_name=? AND archived=0 AND salience>=0.5
                   ORDER BY created DESC LIMIT 3""", (char_name,)).fetchall()

        scored = []
        for r in rows:
            relevance = 1.0 / (1.0 + abs(r["rank"]))
            recency = math.exp(-(now - r["created"]) / RECENCY_HALF_LIFE)
            # Ebbinghaus: salience decays unless the page has been recalled;
            # every recall leaves the page a little stronger.
            strength = (r["salience"] * (0.5 + 0.5 * math.exp(-(now - r["last_accessed"]) / STRENGTH_HALF_LIFE))
                        + 0.1 * math.log1p(r["access_count"]))
            scored.append((0.55 * relevance + 0.45 * strength + 0.30 * recency, r))

        scored.sort(key=lambda x: -x[0])
        top = scored[:k]
        for _, r in top:
            conn.execute("UPDATE memories SET access_count=access_count+1, last_accessed=? WHERE id=?",
                         (now, r["id"]))
        return [r["content"] for _, r in top]


# =========================================================
# THE MEMORY PACKET (built fresh at the start of every turn)
# =========================================================
def build_packet(char_name, query_text, diary_k=6):
    state = get_state(char_name)
    return {
        "life_story": state["life_story"],
        "unresolved_threads": state["unresolved_threads"],
        "belief_page": state["belief_page"],
        "scene": state["scene"],
        "last_emotion": state["last_emotion"],
        "diary_pages": search_diary(char_name, query_text, k=diary_k),
    }


def format_scene(scene):
    """The scene notebook, for agents that only get observable reality (A6, Setting)."""
    lines = []
    pt = " · ".join(x for x in [scene.get("place", ""), scene.get("time", "")] if x)
    if pt:
        lines.append(f"Place & time: {pt}")
    if scene.get("atmosphere"):
        lines.append(f"Atmosphere: {scene['atmosphere']}")
    objects = [o for o in (scene.get("objects") or []) if o]
    if objects:
        lines.append("Objects: " + " | ".join(objects))
    if scene.get("today_plan"):
        lines.append(f"Today's plan: {scene['today_plan']}")
    if scene.get("week_draft"):
        lines.append(f"This week: {scene['week_draft']}")
    if not lines:
        return ""
    return "[SCENE NOTEBOOK — persistent physical reality. Stay consistent with it.]\n" + "\n".join(lines)


def format_packet(packet):
    """The full memory packet for the thinking agents (A1–A5)."""
    parts = []
    if packet["life_story"]:
        parts.append(f"MY LIFE STORY: {packet['life_story']}")
    threads = [t for t in packet["unresolved_threads"] if t]
    if threads:
        parts.append("UNRESOLVED THREADS (still on my mind):\n- " + "\n- ".join(threads))
    if packet["belief_page"]:
        parts.append(f"WHAT I BELIEVE ABOUT THE USER: {packet['belief_page']}")
    if packet["diary_pages"]:
        parts.append("RELEVANT MEMORIES:\n- " + "\n- ".join(packet["diary_pages"]))
    scene_txt = format_scene(packet["scene"])
    if scene_txt:
        parts.append(scene_txt)
    if not parts:
        return ""
    return "[LONG-TERM MEMORY — these are my own recalled memories. Let them color everything.]\n" + "\n\n".join(parts)


# =========================================================
# SWIPE-SHIELD (pending turn confirmation)
# =========================================================
def reply_fingerprint(reply_text):
    """A distinctive snippet of the prose. If it's still in the chat next turn,
    the user kept the reply; if it's gone, they swiped/edited it away."""
    text = re.sub(r"\s+", " ", (reply_text or "").strip())
    return text[:100]


def stash_turn(char_name, fingerprint, payload):
    with _lock, _connect() as conn:
        conn.execute(
            "REPLACE INTO pending_turn(char_name, reply_fingerprint, payload_json, created) VALUES(?,?,?,?)",
            (char_name, fingerprint, json.dumps(payload, ensure_ascii=False), time.time()))


def pop_pending(char_name):
    """Fetch and clear the stashed turn. The server decides kept-vs-swiped."""
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM pending_turn WHERE char_name=?", (char_name,)).fetchone()
        if row:
            conn.execute("DELETE FROM pending_turn WHERE char_name=?", (char_name,))
    if not row:
        return None
    try:
        return {"fingerprint": row["reply_fingerprint"],
                "payload": json.loads(row["payload_json"])}
    except json.JSONDecodeError:
        return None


def is_kept(fingerprint, history_contents):
    if not fingerprint:
        return False
    for content in history_contents:
        text = re.sub(r"\s+", " ", (content or ""))
        if fingerprint in text:
            return True
    return False


def all_scenes():
    """Every character's scene notebook, labeled — for the omniscient Setting."""
    with _lock, _connect() as conn:
        rows = conn.execute("SELECT char_name, scene_json FROM char_state").fetchall()
    out = []
    for r in rows:
        try:
            scene = dict(DEFAULT_SCENE)
            scene.update(json.loads(r["scene_json"] or "{}"))
        except (json.JSONDecodeError, TypeError):
            continue
        txt = format_scene(scene)
        if txt:
            out.append(f"--- {r['char_name']} ---\n{txt}")
    return "\n\n".join(out)


# =========================================================
# CHRONICLER OUTPUT APPLICATION
# =========================================================
def apply_chronicler(char_name, result):
    """Write the Chronicler's JSON into the diary, scene, beliefs."""
    now = time.time()
    memories = result.get("memories") or []
    if isinstance(memories, list):
        with _lock, _connect() as conn:
            for m in memories[:3]:
                if not isinstance(m, dict):
                    continue
                content = str(m.get("content") or "").strip()
                if not content:
                    continue
                prov = str(m.get("provenance") or "witnessed")
                if prov not in ("witnessed", "heard", "told", "inferred", "remembered"):
                    prov = "witnessed"
                conn.execute(
                    """INSERT INTO memories(char_name, content, salience, provenance, emotion,
                                            access_count, last_accessed, created, archived)
                       VALUES(?,?,?,?,?,0,?,?,0)""",
                    (char_name, content, _clamp(m.get("salience", 0.5)), prov,
                     str(m.get("emotion") or "")[:300], now, now))

    updates, args = {}, []

    scene_in = result.get("scene")
    if isinstance(scene_in, dict):
        scene = get_state(char_name)["scene"]
        for key in ("place", "time", "atmosphere", "today_plan", "week_draft"):
            val = scene_in.get(key)
            if isinstance(val, str) and val.strip():
                scene[key] = val.strip()
        objects = scene_in.get("objects")
        if isinstance(objects, list) and objects:
            scene["objects"] = [str(o)[:200] for o in objects[:12] if o]
        updates["scene_json"] = json.dumps(scene, ensure_ascii=False)

    belief = result.get("belief_page")
    if isinstance(belief, str) and belief.strip():
        updates["belief_page"] = belief.strip()[:1500]

    emotion = result.get("last_emotion")
    if isinstance(emotion, str) and emotion.strip():
        updates["last_emotion"] = emotion.strip()[:300]

    if updates:
        updates["updated"] = now
        with _lock, _connect() as conn:
            cols = ", ".join(f"{k}=?" for k in updates)
            conn.execute(f"UPDATE char_state SET {cols} WHERE char_name=?",
                         (*updates.values(), char_name))


# =========================================================
# ARCHIVIST (consolidation)
# =========================================================
def list_characters():
    with _lock, _connect() as conn:
        rows = conn.execute("SELECT char_name, updated FROM char_state ORDER BY updated DESC").fetchall()
    return [(r["char_name"], r["updated"]) for r in rows]


def get_pages(char_name, limit=30):
    """Latest diary pages for the viewer page."""
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM memories WHERE char_name=? ORDER BY created DESC LIMIT ?",
            (char_name, limit)).fetchall()
    return [dict(r) for r in rows]


def count_unarchived(char_name):
    with _lock, _connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) AS c FROM memories WHERE char_name=? AND archived=0",
            (char_name,)).fetchone()["c"]


def get_unarchived(char_name, limit=40):
    with _lock, _connect() as conn:
        rows = conn.execute(
            """SELECT * FROM memories WHERE char_name=? AND archived=0
               ORDER BY created ASC LIMIT ?""", (char_name, limit)).fetchall()
    return [{"id": r["id"], "content": r["content"], "salience": r["salience"],
             "emotion": r["emotion"], "created": r["created"]} for r in rows]


def apply_consolidation(char_name, life_story, threads, archived_ids):
    with _lock, _connect() as conn:
        conn.execute(
            "UPDATE char_state SET life_story=?, unresolved_threads=?, updated=? WHERE char_name=?",
            ((life_story or "")[:4000], json.dumps(threads or [], ensure_ascii=False),
             time.time(), char_name))
        if archived_ids:
            conn.execute(
                f"UPDATE memories SET archived=1 WHERE char_name=? AND id IN ({','.join('?' * len(archived_ids))})",
                (char_name, *archived_ids))

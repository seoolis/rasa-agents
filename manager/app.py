# manager/app.py
import os
import json
import subprocess
import threading
from pathlib import Path
from typing import Optional
import time

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
AGENTS_DIR = BASE_DIR / "agents"
DB_FILE = Path(__file__).resolve().parent / "agents_db.json"

app = FastAPI(title="Rasa Agents Manager")

# --- helpers for db ---
def load_db():
    if DB_FILE.exists():
        return json.loads(DB_FILE.read_text(encoding='utf-8'))
    return {}

def save_db(db):
    DB_FILE.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')

# --- models ---
class CreateAgentReq(BaseModel):
    name: str
    port: Optional[int] = None
    action_port: Optional[int] = None

# --- utils: manage rasa processes ---
def run_subprocess(cmd, cwd=None):
    return subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# trains rasa model in agent folder (blocking)
def train_agent(agent_path: Path):
    cmd = ["rasa", "train", "--quiet"]
    subprocess.check_call(cmd, cwd=str(agent_path))

# start rasa run --enable-api
def start_rasa_server(agent_path: Path, port: int):
    cmd = ["rasa", "run", "--enable-api", "-p", str(port), "--cors", "*"]
    # Keep process handle
    return run_subprocess(cmd, cwd=str(agent_path))

# start actions server
def start_actions_server(agent_path: Path, action_port: int):
    cmd = ["rasa", "run", "actions", "-p", str(action_port)]
    return run_subprocess(cmd, cwd=str(agent_path))

# send message to agent (Rasa HTTP API)
def send_to_agent(port: int, conversation_id: str, text: str):
    url = f"http://localhost:{port}/conversations/{conversation_id}/respond"
    r = requests.post(url, json={"text": text}, timeout=10)
    return r.json()

def get_tracker(port: int, conversation_id: str):
    url = f"http://localhost:{port}/conversations/{conversation_id}/tracker"
    r = requests.get(url, timeout=10)
    return r.json()

# --- API --- #
@app.get("/api/agents")
def list_agents():
    return load_db()

@app.post("/api/agents")
def create_agent(req: CreateAgentReq):
    db = load_db()
    if req.name in db:
        raise HTTPException(status_code=400, detail="Agent already exists")
    agent_dir = AGENTS_DIR / req.name
    agent_dir.mkdir(parents=True, exist_ok=True)
    # create minimal files if absent
    sample_files = {
        "config.yml": SAMPLE_CONFIG,
        "domain.yml": SAMPLE_DOMAIN,
        "endpoints.yml": SAMPLE_ENDPOINTS,
    }
    data_dir = agent_dir / "data"
    data_dir.mkdir(exist_ok=True)
    if not (data_dir / "nlu.yml").exists():
        (data_dir / "nlu.yml").write_text(SAMPLE_NLU, encoding='utf-8')
    if not (data_dir / "stories.yml").exists():
        (data_dir / "stories.yml").write_text(SAMPLE_STORIES, encoding='utf-8')
    for fname, text in sample_files.items():
        p = agent_dir / fname
        if not p.exists():
            p.write_text(text, encoding='utf-8')
    actions_py = agent_dir / "actions.py"
    if not actions_py.exists():
        actions_py.write_text(SAMPLE_ACTIONS, encoding='utf-8')

    # default ports if not provided
    port = req.port or (5005 + len(db)*2)
    action_port = req.action_port or 5055

    db[req.name] = {
        "path": str(agent_dir),
        "port": port,
        "action_port": action_port,
        "rasa_pid": None,
        "actions_pid": None,
        "status": "created"
    }
    save_db(db)
    return {"ok": True, "agent": req.name, "port": port, "action_port": action_port}

@app.post("/api/agents/{agent}/train")
def train(agent: str):
    db = load_db()
    if agent not in db:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent_path = Path(db[agent]["path"])
    def _train_and_update():
        try:
            db_local = load_db()
            db_local[agent]["status"] = "training"
            save_db(db_local)
            train_agent(agent_path)
            db_local = load_db()
            db_local[agent]["status"] = "trained"
            save_db(db_local)
        except Exception as e:
            db_local = load_db()
            db_local[agent]["status"] = f"train_error: {e}"
            save_db(db_local)
    threading.Thread(target=_train_and_update).start()
    return {"ok": True, "status": "training started"}

@app.post("/api/agents/{agent}/start")
def start(agent: str):
    db = load_db()
    if agent not in db:
        raise HTTPException(status_code=404, detail="Agent not found")
    info = db[agent]
    agent_path = Path(info["path"])
    # start actions if not started
    if not info.get("actions_pid"):
        proc_actions = start_actions_server(agent_path, info["action_port"])
        info["actions_pid"] = proc_actions.pid
        time.sleep(0.5)
    # start rasa server
    if not info.get("rasa_pid"):
        proc = start_rasa_server(agent_path, info["port"])
        info["rasa_pid"] = proc.pid
        info["status"] = "running"
    save_db(db)
    return {"ok": True, "rasa_pid": info["rasa_pid"], "actions_pid": info["actions_pid"]}

@app.post("/api/agents/{agent}/stop")
def stop(agent: str):
    db = load_db()
    if agent not in db:
        raise HTTPException(status_code=404, detail="Agent not found")
    info = db[agent]
    # try to kill processes
    for key in ("rasa_pid", "actions_pid"):
        pid = info.get(key)
        if pid:
            try:
                os.kill(pid, 9)
            except Exception:
                pass
            info[key] = None
    info["status"] = "stopped"
    save_db(db)
    return {"ok": True}

class ChatReq(BaseModel):
    text: str
    conversation_id: Optional[str] = "default"

@app.post("/api/agents/{agent}/chat")
def chat(agent: str, req: ChatReq):
    db = load_db()
    if agent not in db:
        raise HTTPException(status_code=404, detail="Agent not found")
    info = db[agent]
    port = info["port"]
    cid = req.conversation_id or "default"
    # send to agent
    try:
        resp = send_to_agent(port, cid, req.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent request failed: {e}")
    # after respond, check tracker for transfer slot
    try:
        tracker = get_tracker(port, cid)
        # look for slot transfer_to
        slots = tracker.get("slots", {})
        transfer_target = slots.get("transfer_to")
        if transfer_target:
            # ensure target exists
            if transfer_target in db:
                target_info = db[transfer_target]
                target_port = target_info["port"]
                # forward message to target agent with same conversation id
                forwarded = send_to_agent(target_port, cid, req.text)
                return {"transferred": True, "from": agent, "to": transfer_target, "forwarded_response": forwarded, "original_response": resp, "tracker": tracker}
            else:
                return {"transferred": False, "error": f"transfer target {transfer_target} not found", "tracker": tracker, "original_response": resp}
        else:
            return {"transferred": False, "response": resp, "tracker": tracker}
    except Exception:
        return {"transferred": False, "response": resp}
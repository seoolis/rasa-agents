# utils/rasa_utils.py
import subprocess
import requests
import os
from pathlib import Path
import time
import json

def train_agent_model(agent_path: str):
    agent_path = Path(agent_path)
    # запускаем rasa train в каталоге агента
    cmd = ["rasa", "train", "--quiet"]
    subprocess.check_call(cmd, cwd=str(agent_path))

def get_agent_port(agent_path: Path):
    # по соглашению: порт указывается в agents_db.json; но если нет — дефолт 5005
    # простой fallback:
    return 5005

def parse_message(agent_path: Path, text: str):
    port = get_agent_port(agent_path)
    url = f"http://localhost:{port}/model/parse"
    r = requests.post(url, json={"text": text})
    return r.json()

def send_message_to_agent(agent_path: Path, text: str, conversation_id=None):
    port = get_agent_port(agent_path)
    url = f"http://localhost:{port}/conversations/{conversation_id or 'default'}/respond"
    r = requests.post(url, json={"text": text})
    try:
        return r.json()
    except:
        return {"error": "no response from agent", "status_code": r.status_code, "text": r.text}

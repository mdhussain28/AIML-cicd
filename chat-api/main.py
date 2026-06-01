from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import socket
import shutil
import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT = os.getenv("BOT_NAME", "BankBot")
APP_ENV = os.getenv("APP_ENV", "production")
DATA_DIR = os.getenv("MODEL_DIR", "/data")

os.makedirs(DATA_DIR, exist_ok=True)

IMAGE_KNOWLEDGE = "/app/knowledge.json"
PVC_KNOWLEDGE = f"{DATA_DIR}/knowledge.json"
UNANSWERED_FILE = f"{DATA_DIR}/unanswered.txt"

if not os.path.exists(PVC_KNOWLEDGE):
    shutil.copy(IMAGE_KNOWLEDGE, PVC_KNOWLEDGE)
    print("Created knowledge base from image")

if not os.path.exists(UNANSWERED_FILE):
    open(UNANSWERED_FILE, "w").close()
    print("Created unanswered file")

with open(PVC_KNOWLEDGE, "r", encoding="utf-8") as f:
    KNOWLEDGE = json.load(f)


def find_answer(question: str):
    question = question.lower()

    for item in KNOWLEDGE:
        for keyword in item["keywords"]:
            if keyword.lower() in question:
                return item

    return None


def save_unanswered(question: str):
    with open(UNANSWERED_FILE, "a", encoding="utf-8") as f:
        f.write(
            f"{datetime.datetime.now()} | {question}\n"
        )


@app.get("/chat")
def chat(message: str = ""):

    msg = message.lower().strip()

    greetings = [
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening"
    ]

    if msg in greetings:
        return {
            "bot": BOT,
            "reply": "I'm BankBot, specialized in banking support only. Please ask me about your accounts, cards, loans, or transactions.",
            "intent": "greeting",
            "served_by": socket.gethostname(),
            "llm_used": False
        }

    result = find_answer(msg)

    if result:
        return {
            "bot": BOT,
            "reply": result["answer"],
            "intent": result["category"],
            "served_by": socket.gethostname(),
            "llm_used": False
        }

    save_unanswered(message)

    return {
        "bot": BOT,
        "reply": "This question has been noted and saved. Our team will contact you shortly.",
        "intent": "unanswered",
        "served_by": socket.gethostname(),
        "llm_used": False
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "bot": BOT,
        "env": APP_ENV
    }


@app.get("/knowledge")
def knowledge():
    return {
        "entries": len(KNOWLEDGE),
        "categories": [x["category"] for x in KNOWLEDGE]
    }


@app.get("/unanswered")
def unanswered():

    try:
        with open(UNANSWERED_FILE, "r") as f:
            questions = f.readlines()

        return {
            "count": len(questions),
            "questions": questions[-100:]
        }

    except Exception as e:
        return {
            "error": str(e)
        }


@app.get("/config")
def config():
    return {
        "bot": BOT,
        "env": APP_ENV,
        "data_dir": DATA_DIR,
        "knowledge_file": PVC_KNOWLEDGE,
        "unanswered_file": UNANSWERED_FILE
    }

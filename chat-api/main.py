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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

IMAGE_KNOWLEDGE = os.path.join(BASE_DIR, "knowledge.json")
PVC_KNOWLEDGE = os.path.join(DATA_DIR, "knowledge.json")
UNANSWERED_FILE = os.path.join(DATA_DIR, "unanswered.txt")

# ------------------------------------------------------------------
# Initialize files
# ------------------------------------------------------------------

if not os.path.exists(PVC_KNOWLEDGE):

    if os.path.exists(IMAGE_KNOWLEDGE):

        shutil.copy(
            IMAGE_KNOWLEDGE,
            PVC_KNOWLEDGE
        )

        print("Knowledge base copied to PVC")

    else:

        with open(PVC_KNOWLEDGE, "w") as f:
            json.dump([], f)

        print("Created empty knowledge base")

if not os.path.exists(UNANSWERED_FILE):

    open(
        UNANSWERED_FILE,
        "w",
        encoding="utf-8"
    ).close()

    print("Created unanswered file")

# ------------------------------------------------------------------
# Load knowledge base
# ------------------------------------------------------------------

try:

    with open(
        PVC_KNOWLEDGE,
        "r",
        encoding="utf-8"
    ) as f:

        KNOWLEDGE = json.load(f)

    print(f"Loaded {len(KNOWLEDGE)} knowledge entries")

except Exception as e:

    print("Knowledge load error:", e)

    KNOWLEDGE = []

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def find_answer(question: str):

    question = question.lower().strip()

    for item in KNOWLEDGE:

        keywords = item.get("keywords", [])

        for keyword in keywords:

            if keyword.lower() in question:

                return {
                    "category": item.get("category", "general"),
                    "answer": item.get("answer", "")
                }

    return None


def save_unanswered(question: str):

    try:

        with open(
            UNANSWERED_FILE,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(
                f"{datetime.datetime.now()} | {question}\n"
            )

    except Exception as e:

        print("Unable to save unanswered question:", e)

# ------------------------------------------------------------------
# Chat endpoint
# ------------------------------------------------------------------

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
            "reply": (
                "I'm BankBot, specialized in banking support only. "
                "Please ask me about your accounts, cards, loans, or transactions."
            ),
            "intent": "greeting",
            "risk_score": "N/A",
            "risk_flag": "N/A",
            "served_by": socket.gethostname(),
            "llm_used": False
        }

    result = find_answer(msg)

    if result:

        return {
            "bot": BOT,
            "reply": result["answer"],
            "intent": result["category"],
            "risk_score": "N/A",
            "risk_flag": "N/A",
            "served_by": socket.gethostname(),
            "llm_used": False
        }

    save_unanswered(message)

    return {
        "bot": BOT,
        "reply": (
            "This question has been noted and saved. "
            "Our team will contact you shortly."
        ),
        "intent": "unanswered",
        "risk_score": "N/A",
        "risk_flag": "N/A",
        "served_by": socket.gethostname(),
        "llm_used": False
    }

# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

@app.get("/health")
def health():

    return {
        "status": "ok",
        "bot": BOT,
        "env": APP_ENV
    }

# ------------------------------------------------------------------
# Knowledge Info
# ------------------------------------------------------------------

@app.get("/knowledge")
def knowledge():

    return {
        "entries": len(KNOWLEDGE),
        "categories": [
            item.get("category")
            for item in KNOWLEDGE
        ]
    }

# ------------------------------------------------------------------
# Unanswered Questions
# ------------------------------------------------------------------

@app.get("/unanswered")
def unanswered():

    try:

        with open(
            UNANSWERED_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            questions = f.readlines()

        return {
            "count": len(questions),
            "questions": questions[-100:]
        }

    except Exception as e:

        return {
            "error": str(e)
        }

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------

@app.get("/config")
def config():

    return {
        "bot": BOT,
        "env": APP_ENV,
        "data_dir": DATA_DIR,
        "knowledge_file": PVC_KNOWLEDGE,
        "unanswered_file": UNANSWERED_FILE
    }

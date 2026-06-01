from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import socket
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

KNOWLEDGE_FILE = f"{DATA_DIR}/knowledge.txt"
UNANSWERED_FILE = f"{DATA_DIR}/unanswered.txt"

DEFAULT_KNOWLEDGE = [
    (
        "what is upi",
        "UPI (Unified Payments Interface) enables instant bank-to-bank transfers."
    ),
    (
        "what is neft",
        "NEFT is a nationwide electronic funds transfer system."
    ),
    (
        "what is rtgs",
        "RTGS enables real-time transfer of large-value funds."
    ),
    (
        "what is imps",
        "IMPS provides instant 24x7 fund transfer services."
    ),
    (
        "how to block my debit card",
        "You can block your debit card through internet banking, mobile banking, or customer care."
    ),
    (
        "how to reset atm pin",
        "ATM PIN can be reset through internet banking, mobile banking, or an ATM."
    ),
    (
        "how to check account balance",
        "Account balance can be checked through mobile banking, internet banking, ATM, or passbook."
    ),
    (
        "what is a savings account",
        "A savings account helps customers save money while earning interest."
    ),
    (
        "what is a current account",
        "A current account is designed for businesses and frequent transactions."
    ),
    (
        "how to download bank statement",
        "Bank statements can be downloaded from internet banking or mobile banking."
    )
]


def initialize_files():

    if not os.path.exists(KNOWLEDGE_FILE):

        with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:

            for q, a in DEFAULT_KNOWLEDGE:
                f.write(f"{q}|{a}\n")

        print("Created default knowledge base")

    if not os.path.exists(UNANSWERED_FILE):

        with open(UNANSWERED_FILE, "w", encoding="utf-8") as f:
            pass

        print("Created unanswered file")


initialize_files()


def search_knowledge(question: str):

    try:

        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:

            for line in f:

                line = line.strip()

                if "|" not in line:
                    continue

                q, a = line.split("|", 1)

                if q.lower().strip() == question.lower().strip():
                    return a

    except Exception as e:

        print("Knowledge lookup error:", e)

    return None


def save_unanswered(question: str):

    try:

        with open(UNANSWERED_FILE, "a", encoding="utf-8") as f:

            f.write(
                f"{datetime.datetime.now()} | {question}\n"
            )

    except Exception as e:

        print("Unable to save unanswered:", e)


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
            "served_by": socket.gethostname(),
            "llm_used": False
        }

    answer = search_knowledge(msg)

    if answer:

        return {
            "bot": BOT,
            "reply": answer,
            "intent": "knowledge",
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

    try:

        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:

            lines = f.readlines()

        return {
            "count": len(lines),
            "entries": lines
        }

    except Exception as e:

        return {
            "error": str(e)
        }


@app.get("/unanswered")
def unanswered():

    try:

        with open(UNANSWERED_FILE, "r", encoding="utf-8") as f:

            lines = f.readlines()

        return {
            "count": len(lines),
            "questions": lines[-100:]
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
        "knowledge_file": KNOWLEDGE_FILE,
        "unanswered_file": UNANSWERED_FILE
    }

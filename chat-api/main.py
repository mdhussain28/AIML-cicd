from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests, socket, os, json, datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PROMPT       = os.getenv("SYSTEM_PROMPT",  "You are a banking support assistant.")
RISK_URL     = os.getenv("RISK_API_URL",   "http://risk-service:8001")
BOT          = os.getenv("BOT_NAME",       "BankBot")
APP_ENV      = os.getenv("APP_ENV",        "dev")
LOG_DIR      = os.getenv("LOG_DIR",        "/shared/logs")
MODEL_DIR    = os.getenv("MODEL_DIR",      "/model")
OLLAMA_URL   = os.getenv("OLLAMA_URL",     "http://ollama.default.svc.cluster.local:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL",   "llama3")

# Load memory from volume on startup
try:
    conversation_memory = json.load(open(f"{MODEL_DIR}/memory.json"))
    print(f"Loaded {len(conversation_memory)} memory entries")
except:
    conversation_memory = []
    print("No existing memory — starting fresh")

# ─── Banking Keywords ─────────────────────────────────────────────────────────
BANKING_KEYWORDS = [
    "account", "balance", "card", "loan", "transfer", "payment",
    "fraud", "stolen", "lost", "transaction", "bank", "credit",
    "debit", "atm", "interest", "mortgage", "deposit", "withdrawal",
    "unauthorized", "blocked", "statement", "pin", "limit", "fee",
    "cheque", "swift", "iban", "overdraft", "savings", "current"
]

def is_banking_related(message: str) -> bool:
    msg = message.lower()
    return any(k in msg for k in BANKING_KEYWORDS)

# ─── Intent Detection ─────────────────────────────────────────────────────────
def detect_intent(message: str) -> str:
    msg = message.lower()
    if "balance" in msg:                          return "balance_check"
    if "lost" in msg and "card" in msg:           return "lost_card"
    if "card" in msg:                             return "card_issue"
    if "loan" in msg or "mortgage" in msg:        return "loan_query"
    if "fraud" in msg or "stolen" in msg:         return "fraud_alert"
    if "transfer" in msg or "payment" in msg:     return "payment_query"
    if "unauthorized" in msg:                     return "fraud_alert"
    if "block" in msg or "locked" in msg:         return "account_blocked"
    if "statement" in msg:                        return "statement_request"
    if "interest" in msg:                         return "interest_query"
    if "deposit" in msg or "withdrawal" in msg:   return "transaction_query"
    if "atm" in msg:                              return "atm_query"
    return "general_banking"

# ─── Ollama LLM Call ──────────────────────────────────────────────────────────
def call_ollama(message: str, intent: str, risk_flag: str):
    system_prompt = f"""You are BankBot, a professional banking support assistant.
You ONLY answer questions related to banking, finance, and financial services.
If a question is not related to banking, politely decline.

Current context:
- Customer intent: {intent}
- Risk assessment: {risk_flag}
- If risk is high_risk, always recommend immediate action and escalate.

Keep responses concise, professional, and helpful.
Never share passwords or sensitive account details.
Always recommend official channels for sensitive requests."""

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": f"{system_prompt}\n\nCustomer: {message}\nBankBot:",
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 150
                }
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get("response", "").strip()
    except Exception as e:
        print(f"Ollama error: {e}")
    return None

# ─── Fallback Response ────────────────────────────────────────────────────────
def fallback_reply(intent: str, risk_flag: str) -> str:
    if risk_flag == "high_risk":
        return " High-risk activity detected. Your case has been escalated to our fraud team immediately. Please call our 24/7 helpline."
    responses = {
        "balance_check":      "Your balance request is being processed securely. Please use our secure app or visit a branch.",
        "lost_card":          "We're sorry to hear your card is lost. We'll block it immediately and arrange a replacement within 3-5 business days.",
        "card_issue":         "Our card support team is reviewing your issue. Expected resolution within 24 hours.",
        "loan_query":         "Our loan advisors are available Monday–Friday, 9 AM–6 PM. Shall I arrange a callback?",
        "fraud_alert":        "Your fraud alert has been registered. Our security team will contact you within 1 hour.",
        "payment_query":      "Payment queries are handled by our 24/7 support. We'll review your transaction history.",
        "account_blocked":    "Account blocks are reviewed immediately. Please verify your identity at any branch.",
        "statement_request":  "Your account statement can be downloaded from our mobile app or requested at a branch.",
        "interest_query":     "Our current interest rates are available on our website or speak to an advisor.",
        "transaction_query":  "Your recent transactions can be viewed securely in our mobile app.",
        "atm_query":          "Our ATM locator is available on our website and mobile app.",
        "general_banking":    "Our banking support team is here to help. How can I assist you today?"
    }
    return responses.get(intent, "Our support team will assist you shortly.")

# ─── Chat Endpoint ────────────────────────────────────────────────────────────
@app.get("/chat")
def chat(message: str = "hello"):
    timestamp = str(datetime.datetime.now())
    intent    = detect_intent(message)

    # Out of scope check
    if not is_banking_related(message):
        return {
            "bot":           BOT,
            "reply":         "I'm BankBot, specialized in banking support only. Please ask me about your accounts, cards, loans, or transactions.",
            "intent":        "out_of_scope",
            "risk_score":    0,
            "risk_flag":     "none",
            "model_version": "N/A",
            "memory_size":   len(conversation_memory),
            "environment":   APP_ENV,
            "served_by":     socket.gethostname(),
            "llm_used":      False
        }

    # Load model metadata
    model_ver = "not-loaded"
    try:
        model     = json.load(open(f"{MODEL_DIR}/risk_model.json"))
        model_ver = model.get("model_version", "unknown")
    except:
        pass

    # Call Risk API
    try:
        risk = requests.get(
            f"{RISK_URL}/risk",
            params={"message": message},
            timeout=3
        ).json()
    except:
        risk = {"risk_score": 0, "flag": "unknown"}

    risk_flag = risk.get("flag", "unknown")

    # Try Ollama — fallback to canned response
    llm_reply = call_ollama(message, intent, risk_flag)
    reply     = llm_reply if llm_reply else fallback_reply(intent, risk_flag)
    llm_used  = llm_reply is not None

    # Store in memory
    conversation_memory.append({
        "time":    timestamp,
        "message": message,
        "intent":  intent,
        "risk":    risk_flag,
        "reply":   reply[:100]
    })

    # Persist memory to volume
    try:
        os.makedirs(MODEL_DIR, exist_ok=True)
        with open(f"{MODEL_DIR}/memory.json", "w") as f:
            json.dump(conversation_memory[-100:], f)
    except:
        pass

    # Write log
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        log = f"{timestamp} | intent={intent} | risk={risk_flag} | llm={llm_used} | msg={message}\n"
        open(f"{LOG_DIR}/chat.log", "a").write(log)
    except:
        pass

    return {
        "bot":           BOT,
        "reply":         reply,
        "intent":        intent,
        "risk_score":    risk.get("risk_score"),
        "risk_flag":     risk_flag,
        "model_version": model_ver,
        "memory_size":   len(conversation_memory),
        "environment":   APP_ENV,
        "served_by":     socket.gethostname(),
        "llm_used":      llm_used
    }

# ─── Health ───────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "bot": BOT, "env": APP_ENV}

# ─── Readiness ────────────────────────────────────────────────────────────────
@app.get("/ready")
def ready():
    try:
        r = requests.get(f"{RISK_URL}/health", timeout=2)
        if r.status_code == 200:
            return {"ready": True, "risk_api": "reachable"}
    except:
        pass
    return {"ready": False, "risk_api": "unreachable"}

# ─── Memory ───────────────────────────────────────────────────────────────────
@app.get("/memory")
def memory():
    return {
        "total":   len(conversation_memory),
        "last_10": conversation_memory[-10:]
    }

# ─── Config ───────────────────────────────────────────────────────────────────
@app.get("/config")
def config():
    return {
        "bot":          BOT,
        "env":          APP_ENV,
        "risk_url":     RISK_URL,
        "ollama_url":   OLLAMA_URL,
        "ollama_model": OLLAMA_MODEL,
        "log_dir":      LOG_DIR,
        "model_dir":    MODEL_DIR
    }

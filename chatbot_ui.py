import streamlit as st
import requests
import uuid

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hospital Chatbot Tester",
    page_icon="🏥",
    layout="centered",
)

# ─────────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu, footer, header {visibility: hidden;}

.bubble-user {
    background: #2563eb;
    color: white;
    padding: 10px 15px;
    border-radius: 18px 18px 4px 18px;
    margin: 6px 0;
    max-width: 75%;
    margin-left: auto;
    word-wrap: break-word;
}

.bubble-assistant {
    background: #f1f5f9;
    color: #1e293b;
    padding: 10px 15px;
    border-radius: 18px 18px 18px 4px;
    margin: 6px 0;
    max-width: 75%;
    margin-right: auto;
    word-wrap: break-word;
}

.bubble-wrapper-user { display: flex; justify-content: flex-end; }
.bubble-wrapper-assistant { display: flex; justify-content: flex-start; }

.chat-label {
    font-size: 11px;
    color: #94a3b8;
    margin-bottom: 2px;
}

.chat-label-user { text-align: right; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────
def init_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    if "health" not in st.session_state:
        st.session_state.health = None


init_state()


# ─────────────────────────────────────────────────────────────
# API CONFIG (FROM SECRETS ONLY)
# ─────────────────────────────────────────────────────────────
BASE_URL = st.secrets.get("API_BASE_URL", "http://externalapi:8000")


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Configuration")
    st.divider()


    session_id_input = st.text_input(
        "Session ID",
        value=st.session_state.session_id
    )
    st.session_state.session_id = session_id_input.strip() or st.session_state.session_id

    st.divider()

    # Health check
    if st.button("Check API Health"):
        try:
            res = requests.get(BASE_URL.rstrip("/") + "/health", timeout=5)
            st.session_state.health = res.json()
        except Exception as e:
            st.session_state.health = {"status": "error", "detail": str(e)}

    if st.session_state.health:
        status = st.session_state.health.get("status", "unknown")

        if status == "ok":
            st.success("API Healthy")
        elif status == "degraded":
            st.warning("API Degraded")
        else:
            st.error("API Down")

    st.divider()

    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()


# ─────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────
st.title("🏥 Hospital Chatbot Tester")
st.caption("Production-grade Streamlit client")


# ─────────────────────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────────────────────
def validate(session_id: str) -> bool:
    if not session_id.strip():
        st.error("Session ID cannot be empty")
        return False
    if not BASE_URL.startswith("http"):
        st.error("Invalid API URL in secrets")
        return False
    return True


# ─────────────────────────────────────────────────────────────
# CHAT HISTORY
# ─────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown('<div class="chat-label chat-label-user">You</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="bubble-wrapper-user"><div class="bubble-user">{msg["content"]}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="chat-label">Assistant</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="bubble-wrapper-assistant"><div class="bubble-assistant">{msg["content"]}</div></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# CHAT INPUT
# ─────────────────────────────────────────────────────────────
user_input = st.chat_input("Type your message...")

if user_input:

    if not validate(st.session_state.session_id):
        st.stop()

    hospital_id = "hospital_knowledge"

    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    history = st.session_state.messages[:-1]

    payload = {
        "hospital_id": hospital_id,
        "session_id": st.session_state.session_id,
        "message": user_input,
        "history": history,
    }

    url = BASE_URL.rstrip("/") + "/chat"

    with st.spinner("Thinking..."):
        try:
            res = requests.post(url, json=payload, timeout=30)

            if res.status_code == 200:
                reply = res.json().get("reply", "No response")
            elif res.status_code == 422:
                reply = f"Validation error: {res.text}"
            else:
                reply = f"Error {res.status_code}: {res.text}"

        except requests.exceptions.Timeout:
            reply = "Request timed out"
        except requests.exceptions.ConnectionError:
            reply = "Cannot connect to API"
        except Exception as e:
            reply = f"Error: {str(e)}"

    st.session_state.messages.append({
        "role": "assistant",
        "content": reply
    })

    st.rerun()
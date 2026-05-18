import streamlit as st
import requests
import uuid
import re

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hospital Chatbot Tester",
    page_icon="🏥",
    layout="centered",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
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

.bubble-wrapper-user {
    display: flex;
    justify-content: flex-end;
    margin: 4px 0;
}

.bubble-wrapper-assistant {
    display: flex;
    justify-content: flex-start;
    margin: 4px 0;
}

.chat-label {
    font-size: 11px;
    color: #94a3b8;
    margin-bottom: 2px;
}

.chat-label-user {
    text-align: right;
}

.health-dot-ok {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #22c55e;
    margin-right: 6px;
}

.health-dot-error {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #ef4444;
    margin-right: 6px;
}

.health-dot-unknown {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #94a3b8;
    margin-right: 6px;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "health_status" not in st.session_state:
    st.session_state.health_status = None

if "health_data" not in st.session_state:
    st.session_state.health_data = {}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Config")
    st.divider()

    import os

    DEFAULT_API_URL = (
    st.secrets.get("API_BASE_URL")
    or os.getenv("API_BASE_URL")
    or "http://localhost:8000"
)

base_url = st.text_input(
    "API Base URL",
    value=DEFAULT_API_URL,
    help="Loaded from Streamlit secrets or environment"
)

    hospital_id = st.text_input(
        "Hospital ID",
        value="",
        placeholder="e.g. city-hospital"
    )

    session_id = st.text_input(
        "Session ID",
        value=st.session_state.session_id
    )
    st.session_state.session_id = session_id

    st.divider()

    # Health check
    if st.button("Check Health", use_container_width=True):
        try:
            resp = requests.get(f"{base_url}/health", timeout=5)
            data = resp.json()
            st.session_state.health_status = data.get("status", "error")
            st.session_state.health_data = data
        except Exception:
            st.session_state.health_status = "error"
            st.session_state.health_data = {}

    status = st.session_state.health_status

    if status == "ok":
        st.markdown('<span class="health-dot-ok"></span> API Online', unsafe_allow_html=True)
    elif status in ("degraded", "error"):
        st.markdown('<span class="health-dot-error"></span> API Offline / Degraded', unsafe_allow_html=True)
    else:
        st.markdown('<span class="health-dot-unknown"></span> Not checked yet', unsafe_allow_html=True)

    # Component breakdown
    components = st.session_state.health_data.get("components", {})
    for k, v in components.items():
        icon = "✅" if v == "ok" else "❌"
        st.caption(f"{icon} {k}: {v}")

    st.divider()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

# ── Helpers ───────────────────────────────────────────────────────────────────
def strip_session_state(text: str) -> str:
    return re.sub(
        r'\n\n\[SESSION_STATE\].*?\[/SESSION_STATE\]',
        '',
        text,
        flags=re.DOTALL
    ).strip()

def validate_config():
    if not hospital_id.strip():
        st.error("Please enter Hospital ID")
        return False
    if not base_url.startswith("http"):
        st.error("Invalid API URL")
        return False
    return True

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🏥 Hospital Chatbot Tester")
st.caption("Local testing interface for FastAPI chatbot")
st.divider()

# ── Chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown('<div class="chat-label chat-label-user">You</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="bubble-wrapper-user"><div class="bubble-user">{msg["content"]}</div></div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown('<div class="chat-label">Assistant</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="bubble-wrapper-assistant"><div class="bubble-assistant">{msg["content"]}</div></div>',
            unsafe_allow_html=True
        )

# ── Chat input ────────────────────────────────────────────────────────────────
user_input = st.chat_input("Type your message...")

if user_input:

    if not validate_config():
        st.stop()

    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    history = st.session_state.messages[:-1]

    payload = {
        "hospital_id": hospital_id.strip(),
        "session_id": st.session_state.session_id,
        "message": user_input,
        "history": history,
    }

    with st.spinner("Thinking..."):
        try:
            resp = requests.post(
                f"{base_url}/chat",
                json=payload,
                timeout=30
            )

            if resp.status_code == 200:
                reply = resp.json().get("reply", "(no reply)")
            elif resp.status_code == 422:
                reply = f"Validation error: {resp.json().get('detail', resp.text)}"
            else:
                reply = f"Error {resp.status_code}: {resp.text}"

        except requests.exceptions.ConnectionError:
            reply = "Cannot connect to API"
        except requests.exceptions.Timeout:
            reply = "Request timed out"
        except Exception as e:
            reply = f"Unexpected error: {str(e)}"

    # Store assistant reply
    st.session_state.messages.append({
        "role": "assistant",
        "content": strip_session_state(reply)
    })

    st.rerun()

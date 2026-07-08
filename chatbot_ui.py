#===============
import streamlit as st
import requests
import uuid

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EMRChains affiliated doctors",
    layout="centered",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Hide default streamlit chrome */
    #MainMenu, footer, header {visibility: hidden;}

    /* Chat bubbles */
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
        width: 10px; height: 10px;
        border-radius: 50%;
        background: #22c55e;
        margin-right: 6px;
    }
    .health-dot-error {
        display: inline-block;
        width: 10px; height: 10px;
        border-radius: 50%;
        background: #ef4444;
        margin-right: 6px;
    }
    .health-dot-unknown {
        display: inline-block;
        width: 10px; height: 10px;
        border-radius: 50%;
        background: #94a3b8;
        margin-right: 6px;
    }
</style>
""", unsafe_allow_html=True)


# ── Secrets: API base URL / chat endpoint ────────────────────────────────────
# Expect .streamlit/secrets.toml to contain something like:
#
#   API_BASE_URL = "https://your-ngrok-or-prod-url.com"
#
# or, if you prefer to store the full chat endpoint directly:
#
#   CHAT_ENDPOINT = "https://your-ngrok-or-prod-url.com/chat/stream"
#
def resolve_base_url_and_endpoint():
    """
    Pulls the API base URL (and optionally a fully-qualified chat endpoint)
    out of st.secrets. Falls back gracefully with a clear error if missing.
    """
    base_url = None
    chat_endpoint = None

    try:
        base_url = st.secrets.get("API_BASE_URL")
    except Exception:
        base_url = None

    try:
        chat_endpoint = st.secrets.get("CHAT_ENDPOINT")
    except Exception:
        chat_endpoint = None

    return base_url, chat_endpoint


base_url, chat_endpoint_override = resolve_base_url_and_endpoint()

if not base_url and not chat_endpoint_override:
    st.error(
        "No API URL configured. Add `API_BASE_URL` (and optionally "
        "`CHAT_ENDPOINT`) to your `.streamlit/secrets.toml` file."
    )
    st.stop()

# Derive endpoints from base_url unless an explicit override is given
health_endpoint = f"{base_url}/health" if base_url else None
chat_stream_endpoint = chat_endpoint_override or f"{base_url}/chat/stream"


# ── Session state defaults ────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []          # list of {"role": ..., "content": ...}
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "health_status" not in st.session_state:
    st.session_state.health_status = None   # None | "ok" | "degraded" | "error"


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Config")
    st.divider()

    # API URL is now sourced from secrets, not user input — shown read-only.
    st.caption("API URL (from secrets)")
    st.code(base_url or chat_endpoint_override, language=None)

    hospital_id = st.text_input(
        "Hospital ID",
        value="",
        placeholder="e.g. city-hospital",
        help="Maps to your Qdrant collection name"
    )

    session_id = st.text_input(
        "Session ID",
        value=st.session_state.session_id,
        help="Auto-generated UUID. Edit if you want a custom session."
    )
    # Sync edits back to session state
    st.session_state.session_id = session_id

    st.divider()

    # Health check
    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("Check Health", use_container_width=True, disabled=not health_endpoint):
            try:
                resp = requests.get(health_endpoint, timeout=5)
                data = resp.json()
                st.session_state.health_status = data.get("status", "error")
                st.session_state.health_data = data
            except Exception:
                st.session_state.health_status = "error"
                st.session_state.health_data = {}

    # Health dot
    status = st.session_state.health_status
    if status == "ok":
        st.markdown('<span class="health-dot-ok"></span> **API Online**', unsafe_allow_html=True)
    elif status in ("degraded", "error"):
        st.markdown('<span class="health-dot-error"></span> **API Degraded / Offline**', unsafe_allow_html=True)
    else:
        st.markdown('<span class="health-dot-unknown"></span> *Not checked yet*', unsafe_allow_html=True)

    # Show component breakdown if available
    if st.session_state.health_status and hasattr(st.session_state, "health_data"):
        components = st.session_state.health_data.get("components", {})
        if components:
            for k, v in components.items():
                icon = "✅" if v == "ok" else "❌"
                st.caption(f"{icon} {k}: {v}")

    st.divider()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()


# ── Main area ─────────────────────────────────────────────────────────────────
st.markdown("## EMRChains Chatbot Tester")
st.caption("A local dev interface for your FastAPI chatbot. API URL is loaded from secrets — just fill in Hospital ID and start chatting.")
st.divider()


import re

def strip_session_state(text: str) -> str:
    return re.sub(r'\n\n\[SESSION_STATE\].*?\[/SESSION_STATE\]', '', text, flags=re.DOTALL).strip()

# Render chat history
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="chat-label chat-label-user">You</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="bubble-wrapper-user"><div class="bubble-user">{msg["content"]}</div></div>', unsafe_allow_html=True)
    else:
        clean_content = strip_session_state(msg["content"])
        st.markdown(f'<div class="chat-label">Assistant</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="bubble-wrapper-assistant"><div class="bubble-assistant">{clean_content}</div></div>', unsafe_allow_html=True)

# Input box always at bottom
user_input = st.chat_input("Type your message...")

if user_input:
    # Validate config
    if not hospital_id.strip():
        st.error("Please enter a Hospital ID in the sidebar before chatting.")
        st.stop()

    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Build payload — send full history EXCLUDING current message (it's in `message`)
    history_for_api = st.session_state.messages[:-1]  # all except the just-added user msg

    payload = {
        "hospital_id": hospital_id.strip(),
        "session_id": st.session_state.session_id,
        "message": user_input,
        "history": history_for_api,
    }

    # Call streaming API (endpoint resolved from secrets)
    reply_chunks = []
    placeholder = st.empty()
    display_so_far = ""

    try:
        with requests.post(
            chat_stream_endpoint,
            json=payload,
            timeout=60,
            stream=True,
        ) as resp:
            if resp.status_code == 200:
                for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
                    if chunk:
                        reply_chunks.append(chunk)
                        display_so_far = strip_session_state("".join(reply_chunks))
                        placeholder.markdown(
                            f'<div class="bubble-wrapper-assistant"><div class="bubble-assistant">{display_so_far}</div></div>',
                            unsafe_allow_html=True
                        )
            elif resp.status_code == 422:
                reply_chunks.append(f"⚠️ Validation Error (422): {resp.text}")
            else:
                reply_chunks.append(f"⚠️ Error {resp.status_code}: {resp.text}")
    except requests.exceptions.ConnectionError:
        reply_chunks.append("❌ Could not connect to the API. Is your FastAPI server running?")
    except requests.exceptions.Timeout:
        reply_chunks.append("❌ Request timed out.")
    except Exception as e:
        reply_chunks.append(f"❌ Unexpected error: {str(e)}")

    reply = "".join(reply_chunks)  # full reply including SESSION_STATE — stored in history

    # Store FULL reply in history (SESSION_STATE included — needed for next turn)
    st.session_state.messages.append({"role": "assistant", "content": reply})

    # Display CLEAN reply to patient (SESSION_STATE hidden)
    display_reply = strip_session_state(reply)
    st.rerun()

#================

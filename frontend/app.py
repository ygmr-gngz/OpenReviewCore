import streamlit as st
import requests

st.set_page_config(
    page_title="OpenReviewCore",
    page_icon="🛡️",
    layout="wide",
)

st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #0f1117 !important; }
[data-testid="stSidebar"] * { color: #c0c0d8 !important; }
[data-testid="stSidebar"] .stSelectbox label { color: #6b6f8a !important; font-size: 10px !important; text-transform: uppercase; letter-spacing: .6px; }
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 0.5px solid #2a2d3e; }
.stTabs [data-baseweb="tab"] { background: transparent; border-radius: 6px; padding: 5px 14px; color: #6b6f8a; font-size: 12px; }
.stTabs [aria-selected="true"] { background: #EEEDFE !important; color: #534AB7 !important; border-color: #AFA9EC !important; }
div[data-testid="metric-container"] { background: #1a1d2e; border: 0.5px solid #2a2d3e; border-radius: 10px; padding: 12px 16px; }
div[data-testid="metric-container"] label { font-size: 10px !important; text-transform: uppercase; letter-spacing: .5px; color: #6b6f8a !important; }
div[data-testid="metric-container"] [data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 500 !important; }
.stTextArea textarea { background: #1a1d2e !important; color: #e0e0e0 !important; font-family: monospace; border: 0.5px solid #2a2d3e !important; }
.stTextInput input { background: #1a1d2e !important; color: #e0e0e0 !important; border: 0.5px solid #2a2d3e !important; }
.stButton button { background: #EEEDFE !important; color: #534AB7 !important; border: 0.5px solid #AFA9EC !important; border-radius: 6px !important; }
.stButton button:hover { background: #CECBF6 !important; }
.block-container { padding-top: 1.5rem !important; }
</style>
""", unsafe_allow_html=True)

API_URL = st.secrets.get("API_URL", "https://openreviewcore-production.up.railway.app")


def call_analyze(payload: dict) -> dict:
    try:
        r = requests.post(f"{API_URL}/analyze", json=payload, timeout=120)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def call_chat(payload: dict) -> dict:
    try:
        r = requests.post(f"{API_URL}/chat", json=payload, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def risk_color(level: str) -> str:
    return {"low": "#3B6D11", "medium": "#854F0B", "high": "#A32D2D", "critical": "#791F1F"}.get(level, "#6b6f8a")


def risk_bg(level: str) -> str:
    return {"low": "#EAF3DE", "medium": "#FAEEDA", "high": "#FCEBEB", "critical": "#FCEBEB"}.get(level, "#f5f5f5")


def risk_bar_color(level: str) -> str:
    return {"low": "#639922", "medium": "#EF9F27", "high": "#E24B4A", "critical": "#A32D2D"}.get(level, "#888")


def risk_emoji(level: str) -> str:
    return {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "🔴"}.get(level, "⚪")


def render_file_item(path: str, score: float, level: str):
    bar_color = risk_bar_color(level)
    txt_color = risk_color(level)
    bg_color  = risk_bg(level)
    bar_width = min(int(score), 100)
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;padding:9px 12px;
     background:#1a1d2e;border:0.5px solid #2a2d3e;border-radius:8px;margin-bottom:5px">
  <div style="width:24px;height:24px;border-radius:6px;background:{bg_color};
       display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:13px">
    📄
  </div>
  <span style="font-size:11px;font-family:monospace;color:#c0c0d8;flex:1;
        overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{path}</span>
  <div style="width:48px;height:4px;background:#2a2d3e;border-radius:2px;overflow:hidden;flex-shrink:0">
    <div style="width:{bar_width}%;height:100%;background:{bar_color};border-radius:2px"></div>
  </div>
  <span style="font-size:13px;font-weight:500;color:{txt_color};flex-shrink:0">{score:.1f}</span>
  <span style="font-size:10px;color:#6b6f8a;flex-shrink:0">/ 100</span>
  <span style="font-size:10px;padding:2px 8px;border-radius:20px;font-weight:500;
        background:{bg_color};color:{txt_color};flex-shrink:0">{level}</span>
</div>
""", unsafe_allow_html=True)


def render_llm_box(title: str, explanation: str):
    st.markdown(f"""
<div style="background:#1a1d2e;border:0.5px solid #2a2d3e;border-radius:10px;padding:12px 16px;margin:8px 0">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
    <span style="font-size:13px">✨</span>
    <span style="font-size:10px;padding:2px 8px;border-radius:20px;background:#EEEDFE;
          color:#534AB7;font-weight:500">{title}</span>
  </div>
  <div style="font-size:12px;color:#a0a0c0;line-height:1.7">{explanation}</div>
</div>
""", unsafe_allow_html=True)


for key, default in [
    ("history", []),
    ("last_result", None),
    ("last_analysis_id", None),
    ("chat_messages", []),
    ("chat_lang", "tr"),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────

with st.sidebar:
    st.markdown("""
<div style="display:flex;align-items:center;gap:8px;padding-bottom:12px;
     border-bottom:0.5px solid #2a2d3e;margin-bottom:4px">
  <div style="width:28px;height:28px;border-radius:6px;background:#EEEDFE;
       display:flex;align-items:center;justify-content:center;font-size:16px">🛡️</div>
  <div>
    <div style="font-size:13px;font-weight:500;color:#e0e0f0">OpenReviewCore</div>
    <div style="font-size:10px;color:#6b6f8a">v0.1.0</div>
  </div>
</div>
""", unsafe_allow_html=True)

    analysis_mode = st.selectbox("Analiz modu", ["static", "hybrid", "llm"], index=0)
    llm_provider  = st.selectbox("LLM sağlayıcı", ["none", "openai", "ollama", "auto"], index=0)
    max_files     = st.selectbox("Dosya limiti (repo)", [10, 25, 50], index=1)

    st.divider()

    if st.session_state.history:
        st.markdown("<div style='font-size:10px;color:#6b6f8a;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px'>Son analizler</div>", unsafe_allow_html=True)
        for item in st.session_state.history[-5:][::-1]:
            level = item.get("risk_level", "?")
            name  = item.get("name", "analiz")
            bg    = risk_bg(level)
            clr   = risk_color(level)
            st.markdown(f"""
<div style="padding:6px 0;border-bottom:0.5px solid #1e2130">
  <div style="font-size:11px;color:#c0c0d8;margin-bottom:4px;white-space:nowrap;
       overflow:hidden;text-overflow:ellipsis">{name}</div>
  <span style="font-size:10px;padding:2px 8px;border-radius:20px;font-weight:500;
        background:{bg};color:{clr}">güvenlik: {level}</span>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# SEKMELER
# ─────────────────────────────────────────

tab1, tab2, tab3 = st.tabs(["💻 Kod analizi", "🐙 Repo analizi", "💬 Sohbet"])


# ── TAB 1: KOD ANALİZİ ──────────────────
with tab1:
    code_input = st.text_area(
        "Python kodunu yapıştır",
        height=180,
        placeholder="def foo(x):\n    return eval(x)",
    )

    if st.button("🔍 Analiz et", key="analyze_code"):
        if not code_input.strip():
            st.warning("Kod boş olamaz.")
        else:
            with st.spinner("Analiz ediliyor..."):
                data = call_analyze({
                    "input_type":    "code",
                    "code":          code_input,
                    "analysis_mode": analysis_mode,
                    "llm_provider":  llm_provider,
                })

            if "error" in data:
                st.error(f"Hata: {data['error']}")
            else:
                st.session_state.last_result      = data
                st.session_state.last_analysis_id = data.get("analysis_id")
                st.session_state.chat_messages    = []
                risk = data.get("result", {}).get("static_result", {}).get("risk_analysis", {})
                st.session_state.history.append({
                    "name":       "kod analizi",
                    "risk_level": risk.get("risk_level", "?"),
                })

    if st.session_state.last_result and "result" in st.session_state.last_result:
        result = st.session_state.last_result["result"]
        if "repo_summary" not in result:
            static    = result.get("static_result", {})
            risk      = static.get("risk_analysis", {})
            breakdown = risk.get("risk_breakdown", {})
            metrics   = static.get("metrics", {})
            llm_res   = result.get("llm_result", {})

            st.divider()

            score = risk.get("final_risk_score", 0)
            level = risk.get("risk_level", "?")

            col1, col2, col3 = st.columns(3)
            col1.metric("🛡️ Risk skoru", f"{score:.1f} / 100", delta=f"{risk_emoji(level)} {level}")
            col2.metric("⚡ Cyclomatic CC", f"{metrics.get('complexity', {}).get('average_complexity', 0):.1f}")
            col3.metric("🔍 Güvenlik bulgusu", metrics.get("security_patterns", {}).get("security_issue_count", 0))

            st.markdown("<div style='font-size:10px;color:#6b6f8a;text-transform:uppercase;letter-spacing:.5px;margin:12px 0 8px'>Risk dağılımı</div>", unsafe_allow_html=True)
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Güvenlik",   f"{breakdown.get('security_risk', 0):.1f}")
            c2.metric("Maintain.",  f"{breakdown.get('maintainability_risk', 0):.1f}")
            c3.metric("Complexity", f"{breakdown.get('complexity_risk', 0):.1f}")
            c4.metric("Bandit",     f"{breakdown.get('bandit_risk', 0):.1f}")
            c5.metric("Ruff",       f"{breakdown.get('ruff_risk', 0):.1f}")

            if llm_res and llm_res.get("status") == "success":
                render_llm_box("LLM analizi", llm_res.get("explanation", ""))


# ── TAB 2: REPO ANALİZİ ─────────────────
with tab2:
    github_url = st.text_input(
        "GitHub repo URL",
        placeholder="https://github.com/kullanici/repo",
    )

    if st.button("🔍 Analiz et", key="analyze_repo"):
        if not github_url.strip():
            st.warning("URL boş olamaz.")
        else:
            with st.spinner("Repo taranıyor..."):
                data = call_analyze({
                    "input_type":      "github_repo",
                    "github_url":      github_url,
                    "max_files":       max_files,
                    "file_extensions": [".py"],
                    "analysis_mode":   analysis_mode,
                    "llm_provider":    llm_provider,
                })

            if "error" in data:
                st.error(f"Hata: {data['error']}")
            else:
                st.session_state.last_result      = data
                st.session_state.last_analysis_id = data.get("analysis_id")
                st.session_state.chat_messages    = []
                repo_summary = data.get("result", {}).get("repo_summary", {})
                repo_name    = github_url.rstrip("/").split("/")[-1]
                st.session_state.history.append({
                    "name":       f"github.com/.../{repo_name}",
                    "risk_level": repo_summary.get("repo_risk_level", "?"),
                })

    if st.session_state.last_result and "result" in st.session_state.last_result:
        result       = st.session_state.last_result["result"]
        repo_summary = result.get("repo_summary", {})

        if repo_summary:
            st.divider()

            level = repo_summary.get("repo_risk_level", "?")
            col1, col2, col3 = st.columns(3)
            col1.metric("🛡️ Risk seviyesi",    f"{risk_emoji(level)} {level}")
            col2.metric("📊 Ortalama skor",    f"{repo_summary.get('average_risk_score', 0):.1f} / 100")
            col3.metric("📁 Analiz edilen",    f"{repo_summary.get('total_files', 0)} dosya")

            repo_llm = result.get("repo_llm_summary", {})
            if repo_llm and repo_llm.get("status") == "success":
                render_llm_box("Repo LLM analizi", repo_llm.get("explanation", ""))

            st.markdown("<div style='font-size:10px;color:#6b6f8a;text-transform:uppercase;letter-spacing:.5px;margin:12px 0 8px'>⚠️ En riskli dosyalar</div>", unsafe_allow_html=True)
            for f in repo_summary.get("riskiest_files", []):
                render_file_item(f["path"], f["risk_score"], f["risk_level"])


# ── TAB 3: SOHBET ───────────────────────
with tab3:
    if not st.session_state.last_analysis_id:
        st.info("Önce bir analiz yap, sonra sohbet edebilirsin.")
    else:
        col_lang1, col_lang2, _ = st.columns([1, 1, 4])
        if col_lang1.button("🇹🇷 Türkçe", use_container_width=True):
            st.session_state.chat_lang = "tr"
        if col_lang2.button("🇬🇧 English", use_container_width=True):
            st.session_state.chat_lang = "en"

        lang = st.session_state.chat_lang
        st.caption(f"Analiz ID: `{st.session_state.last_analysis_id}` · {'Türkçe 🇹🇷' if lang == 'tr' else 'English 🇬🇧'}")

        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        placeholder = "Bu kod neden riskli?" if lang == "tr" else "Why is this code risky?"

        if prompt := st.chat_input(placeholder):
            lang_instruction = (
                "\n\n[Lütfen Türkçe cevap ver.]"
                if lang == "tr"
                else "\n\n[Please respond in English.]"
            )
            full_prompt = prompt + lang_instruction

            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Yanıt üretiliyor..." if lang == "tr" else "Generating response..."):
                    response = call_chat({
                        "analysis_id":  st.session_state.last_analysis_id,
                        "message":      full_prompt,
                        "llm_provider": llm_provider if llm_provider != "none" else "openai",
                    })

                if "error" in response:
                    st.error(response["error"])
                else:
                    reply = response.get("response", "")
                    st.markdown(reply)
                    st.session_state.chat_messages.append({"role": "assistant", "content": reply})
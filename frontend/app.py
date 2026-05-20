import streamlit as st
import requests

# ─────────────────────────────────────────
# SAYFA AYARLARI
# ─────────────────────────────────────────

st.set_page_config(
    page_title="OpenReviewCore",
    page_icon="🛡️",
    layout="wide",
)

API_URL = st.secrets.get("API_URL", "https://openreviewcore-production.up.railway.app")


# ─────────────────────────────────────────
# API FONKSİYONLARI
# ─────────────────────────────────────────

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


# ─────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────

if "history" not in st.session_state:
    st.session_state.history = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "last_analysis_id" not in st.session_state:
    st.session_state.last_analysis_id = None
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []


# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🛡️ OpenReviewCore")
    st.divider()

    analysis_mode = st.selectbox(
        "Analiz modu",
        ["static", "hybrid", "llm"],
        index=0,
    )

    llm_provider = st.selectbox(
        "LLM sağlayıcı",
        ["none", "openai", "ollama", "auto"],
        index=0,
    )

    max_files = st.selectbox(
        "Dosya limiti (repo)",
        [10, 25, 50],
        index=1,
    )

    st.divider()

    if st.session_state.history:
        st.markdown("**Son analizler**")
        for item in st.session_state.history[-5:][::-1]:
            level   = item.get("risk_level", "?")
            name    = item.get("name", "analiz")
            color   = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "🔴"}.get(level, "⚪")
            sec     = item.get("security_level", level)
            sec_clr = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "🔴"}.get(sec, "⚪")
            st.markdown(f"`{name}`  \n{sec_clr} güvenlik: **{sec}**")


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

    if st.button("Analiz et", key="analyze_code"):
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
                    "name":           "kod analizi",
                    "risk_level":     risk.get("risk_level", "?"),
                    "security_level": risk.get("risk_level", "?"),
                })

    if st.session_state.last_result and "result" in st.session_state.last_result:
        result     = st.session_state.last_result["result"]
        static     = result.get("static_result", {})
        risk       = static.get("risk_analysis", {})
        breakdown  = risk.get("risk_breakdown", {})
        metrics    = static.get("metrics", {})
        llm_result = result.get("llm_result", {})

        st.divider()

        # Üst metrik kartları
        col1, col2, col3 = st.columns(3)
        score = risk.get("final_risk_score", 0)
        level = risk.get("risk_level", "?")
        color = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "🔴"}.get(level, "⚪")

        col1.metric("Risk skoru", f"{score:.1f} / 100", delta=f"{color} {level}")
        col2.metric("Cyclomatic CC", f"{metrics.get('complexity', {}).get('average_complexity', 0):.1f}")
        col3.metric("Güvenlik bulgusu", metrics.get("security_patterns", {}).get("security_issue_count", 0))

        # Risk dağılımı
        st.markdown("**Risk dağılımı**")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Güvenlik",       f"{breakdown.get('security_risk', 0):.1f}")
        c2.metric("Maintain.",      f"{breakdown.get('maintainability_risk', 0):.1f}")
        c3.metric("Complexity",     f"{breakdown.get('complexity_risk', 0):.1f}")
        c4.metric("Bandit",         f"{breakdown.get('bandit_risk', 0):.1f}")
        c5.metric("Ruff",           f"{breakdown.get('ruff_risk', 0):.1f}")

        # LLM açıklaması
        if llm_result and llm_result.get("status") == "success":
            st.divider()
            st.markdown("**🤖 LLM analizi**")
            st.markdown(llm_result.get("explanation", ""))


# ── TAB 2: REPO ANALİZİ ─────────────────
with tab2:
    github_url = st.text_input(
        "GitHub repo URL",
        placeholder="https://github.com/kullanici/repo",
    )

    if st.button("Analiz et", key="analyze_repo"):
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
                    "name":           f"github.com/.../{repo_name}",
                    "risk_level":     repo_summary.get("repo_risk_level", "?"),
                    "security_level": repo_summary.get("repo_risk_level", "?"),
                })

    if st.session_state.last_result and "result" in st.session_state.last_result:
        result       = st.session_state.last_result["result"]
        repo_summary = result.get("repo_summary", {})

        if repo_summary:
            st.divider()

            col1, col2, col3 = st.columns(3)
            level = repo_summary.get("repo_risk_level", "?")
            color = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "🔴"}.get(level, "⚪")

            col1.metric("Repo risk seviyesi",  f"{color} {level}")
            col2.metric("Ortalama risk skoru", f"{repo_summary.get('average_risk_score', 0):.1f}")
            col3.metric("Analiz edilen dosya", repo_summary.get("total_files", 0))

            st.markdown("**En riskli dosyalar**")
            for f in repo_summary.get("riskiest_files", []):
                lvl = f.get("risk_level", "?")
                clr = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "🔴"}.get(lvl, "⚪")
                st.markdown(f"{clr} `{f['path']}` — **{f['risk_score']:.1f}** / 100")


# ── TAB 3: SOHBET ───────────────────────
with tab3:
    if not st.session_state.last_analysis_id:
        st.info("Önce bir analiz yap, sonra sohbet edebilirsin.")
    else:
        st.caption(f"Analiz ID: `{st.session_state.last_analysis_id}`")

        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Bu kod neden riskli?"):
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Yanıt üretiliyor..."):
                    response = call_chat({
                        "analysis_id":  st.session_state.last_analysis_id,
                        "message":      prompt,
                        "llm_provider": llm_provider if llm_provider != "none" else "openai",
                    })

                if "error" in response:
                    st.error(response["error"])
                else:
                    reply = response.get("response", "")
                    st.markdown(reply)
                    st.session_state.chat_messages.append({"role": "assistant", "content": reply})
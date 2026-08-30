"""CodeLens AI - Streamlit Code Explainer."""

from __future__ import annotations

import re
import textwrap
import time
from pathlib import Path

import streamlit as st

from code_runner import ExecutionResult, run_code
import gemini_client
from gemini_client import GeminiClientError, generate, is_configured
from prompts import SUPPORTED_LANGUAGES, Mode, build_prompt
import runtime_manager
import setup_manager

APP_DIR = Path(__file__).resolve().parent
STYLES_PATH = APP_DIR / "styles.css"

SAMPLE_SNIPPETS = {
    "Python": "def two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i\n    return []\n",
    "C++": "#include <vector>\n#include <unordered_map>\nusing namespace std;\n\nvector<int> twoSum(vector<int>& nums, int target) {\n    unordered_map<int, int> seen;\n    for (int i = 0; i < nums.size(); i++) {\n        int need = target - nums[i];\n        if (seen.count(need)) return {seen[need], i};\n        seen[nums[i]] = i;\n    }\n    return {};\n}\n",
    "Java": "import java.util.HashMap;\n\nclass Solution {\n    public int[] twoSum(int[] nums, int target) {\n        HashMap<Integer, Integer> seen = new HashMap<>();\n        for (int i = 0; i < nums.length; i++) {\n            int need = target - nums[i];\n            if (seen.containsKey(need)) return new int[] {seen.get(need), i};\n            seen.put(nums[i], i);\n        }\n        return new int[] {};\n    }\n}\n",
    "JavaScript": "function twoSum(nums, target) {\n  const seen = new Map();\n  for (let i = 0; i < nums.length; i++) {\n    const need = target - nums[i];\n    if (seen.has(need)) return [seen.get(need), i];\n    seen.set(nums[i], i);\n  }\n  return [];\n}\n",
}

MODE_LABELS = {
    "explain": "Explain",
    "improve": "Improve",
    "optimize": "Optimize",
}


@st.cache_data(show_spinner=False)
def get_cached_css() -> str:
    """Read and cache CSS stylesheet content from disk."""
    if STYLES_PATH.exists():
        return STYLES_PATH.read_text(encoding="utf-8")
    return ""


def load_css() -> None:
    css = get_cached_css()
    if css:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


@st.cache_data(ttl=4, show_spinner=False)
def check_system_status() -> dict:
    """Query system readiness with a lightweight TTL cache."""
    return setup_manager.get_system_status()


def render_html(html_str: str) -> None:
    """Render raw HTML safely in Streamlit without markdown indentation artifacts."""
    cleaned = "\n".join(line.strip() for line in html_str.strip().splitlines())
    st.markdown(cleaned, unsafe_allow_html=True)


def render_onboarding_wizard(status: dict) -> None:
    """Render the setup wizard & onboarding screen."""
    render_html(
        """
        <div class="setup-container">
          <div class="setup-header-card">
            <div class="setup-header-top">
              <div class="setup-brand">
                <div class="ide-logo-icon">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="m18 16 4-4-4-4"></path>
                    <path d="m6 8-4 4 4 4"></path>
                    <path d="m14.5 4-5 16"></path>
                  </svg>
                </div>
                <div>
                  <h1 class="setup-title">CodeLens AI Setup</h1>
                  <div class="setup-subtitle">Zero-Friction Cloud AI Onboarding • Setup</div>
                </div>
              </div>
              <div class="ide-chips-section">
                <div class="ide-chip chip-online">
                  <span class="status-indicator dot-online"></span>
                  <span>Cloud AI</span>
                </div>
                <div class="ide-chip chip-model">
                  <span class="chip-tag">MODEL</span>
                  <span>Gemini 3.6 Flash</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        """
    )

    col_center = st.columns([0.08, 0.84, 0.08])[1]

    with col_center:
        # Step 1: CodeLens AI Application Card
        render_html(
            """
            <div class="setup-card setup-card-passed">
              <div class="setup-card-header">
                <div class="setup-card-left">
                  <span class="setup-card-icon">🧠</span>
                  <span class="setup-card-title">1. CodeLens AI Core Engine</span>
                </div>
                <span class="setup-card-badge badge-pass">✓ Ready</span>
              </div>
              <div class="setup-card-desc">
                Application core, sandboxed multi-language runners, and IDE workspace are verified.
              </div>
              <div class="setup-meta-row">
                <span class="setup-meta-item">Runtime: <span class="setup-meta-highlight">Python 3.11+ • Streamlit</span></span>
                <span>•</span>
                <span class="setup-meta-item">Release: <span class="setup-meta-highlight">Gemini 3.6 Edition</span></span>
              </div>
            </div>
            """
        )

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # Step 2: Gemini API Configuration Card
        api_configured = status["api_key_configured"]

        if api_configured:
            badge_cls = "badge-pass"
            badge_text = "✓ Connected"
            card_cls = "setup-card-passed"
            desc_text = "Google Gemini 3.6 Flash API is configured via Streamlit secrets or <code>.env</code> and ready for cloud inference."
        else:
            badge_cls = "badge-fail"
            badge_text = "❌ Missing API Key"
            card_cls = "setup-card-active"
            desc_text = "A Google Gemini API key is required to analyze, explain, and optimize code. Set <code>GEMINI_API_KEY</code> in Streamlit secrets or <code>.env</code> file, or enter it below."

        render_html(
            f"""
            <div class="setup-card {card_cls}">
              <div class="setup-card-header">
                <div class="setup-card-left">
                  <span class="setup-card-icon">⚡</span>
                  <span class="setup-card-title">2. Google Gemini API Backend</span>
                </div>
                <span class="setup-card-badge {badge_cls}">{badge_text}</span>
              </div>
              <div class="setup-card-desc">{desc_text}</div>
              <div class="setup-meta-row">
                <span class="setup-meta-item">Model: <span class="setup-meta-highlight">gemini-3.6-flash</span></span>
                <span>•</span>
                <span class="setup-meta-item">Provider: <span class="setup-meta-highlight">Google GenAI</span></span>
                <span>•</span>
                <span class="setup-meta-item">Backend: <span class="setup-meta-highlight">Cloud AI</span></span>
              </div>
            </div>
            """
        )

        if not api_configured:
            st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
            new_key = st.text_input(
                "Gemini API Key",
                type="password",
                placeholder="Enter your GEMINI_API_KEY (e.g. AIzaSy...)",
                key="input_gemini_api_key",
                label_visibility="collapsed",
            )
            if st.button("💾 Save API Key to .env", type="primary", use_container_width=True):
                if new_key.strip():
                    ok, msg = setup_manager.save_api_key(new_key.strip())
                    if ok:
                        st.success(msg)
                        check_system_status.clear()
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Please enter a valid API key.")

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # Step 3: Multi-Language Runtimes Card
        runtimes = runtime_manager.detect_all_runtimes()
        all_rt_ok = all(r.installed for r in runtimes.values())
        rt_badge_cls = "badge-pass" if all_rt_ok else "badge-warn"
        rt_badge_text = "✓ Ready" if all_rt_ok else "⚡ Active"

        rt_items_html = []
        for r_name, r_info in runtimes.items():
            r_dot = "dot-online" if r_info.installed else "dot-fail"
            r_status_text = r_info.version if r_info.installed else "Not Installed"
            rt_items_html.append(
                f'<div class="runtime-health-row">'
                f'<span class="status-indicator {r_dot}"></span>'
                f'<span class="runtime-health-name">{r_name}:</span>'
                f'<span class="runtime-health-val">{r_status_text}</span>'
                f'</div>'
            )

        render_html(
            f"""
            <div class="setup-card setup-card-passed">
              <div class="setup-card-header">
                <div class="setup-card-left">
                  <span class="setup-card-icon">⚡</span>
                  <span class="setup-card-title">3. Multi-Language Sandboxes</span>
                </div>
                <span class="setup-card-badge {rt_badge_cls}">{rt_badge_text}</span>
              </div>
              <div class="setup-card-desc">
                Sandboxed execution compilers and runtimes detected on your machine.
              </div>
              <div class="runtime-health-grid">
                {''.join(rt_items_html)}
              </div>
            </div>
            """
        )

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        # Action / Continue Button
        if status["ready"]:
            st.success("🎉 All components are verified and operational! CodeLens AI is powered by Gemini 3.6 Flash.")
            if st.button("🚀 Launch CodeLens AI Workspace", type="primary", use_container_width=True):
                st.session_state.show_setup_wizard = False
                st.rerun()
        else:
            c_check1, c_check2 = st.columns([1, 1], gap="small")
            with c_check1:
                if st.button("🔄 Recheck Environment", use_container_width=True):
                    check_system_status.clear()
                    st.rerun()
            with c_check2:
                if st.button("⚙️ Skip to Workspace (Manual Mode)", use_container_width=True):
                    st.session_state.show_setup_wizard = False
                    st.rerun()


def render_hero() -> None:
    c_hero, c_settings = st.columns([0.96, 0.04], gap="small")
    with c_hero:
        render_html(
            """
            <header class="ide-header">
              <div class="ide-header-main">
                <div class="ide-brand-section">
                  <div class="ide-logo-icon">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="m18 16 4-4-4-4"></path>
                      <path d="m6 8-4 4 4 4"></path>
                      <path d="m14.5 4-5 16"></path>
                    </svg>
                  </div>
                  <div class="ide-title-block">
                    <div class="ide-title-row">
                      <h1 class="ide-title">CodeLens AI</h1>
                      <span class="ide-badge">IDE</span>
                    </div>
                    <div class="ide-subtitle">Cloud AI • Gemini 3.6 Flash</div>
                  </div>
                </div>
                <div class="ide-chips-section">
                  <div class="ide-chip chip-online">
                    <span class="status-indicator dot-online"></span>
                    <span>Online</span>
                  </div>
                  <div class="ide-chip chip-model">
                    <span class="chip-tag">MODEL</span>
                    <span>Gemini 3.6 Flash</span>
                  </div>
                  <div class="ide-chip chip-cloud">
                    <span class="status-indicator dot-online"></span>
                    <span>Cloud AI</span>
                  </div>
                </div>
              </div>
              <div class="ide-status-strip">
                <div class="strip-left">
                  <span class="strip-pulse-dot"></span>
                  <span class="strip-text">Gemini Inference Engine Ready</span>
                </div>
                <div class="strip-right">
                  <span class="strip-langs">Python • C++ • Java • JavaScript</span>
                </div>
              </div>
            </header>
            """
        )
    with c_settings:
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        if st.button("⚙️", key="open_setup_wizard_btn", help="Setup & API Key Health"):
            check_system_status.clear()
            st.session_state.saved_runtime = st.session_state.get("selected_runtime", "Python")
            st.session_state.saved_code = st.session_state.get("code_input", "")
            st.session_state.show_setup_wizard = True
            st.rerun()


def render_runtime_install_card(language: str) -> None:
    """Render a contextual one-click installer card when a required toolchain is missing."""
    info = runtime_manager.detect_runtime(language)

    render_html(
        f"""
        <div class="setup-card setup-card-active" style="margin-bottom: 0.85rem;">
          <div class="setup-card-header">
            <div class="setup-card-left">
              <span class="setup-card-icon">⚡</span>
              <span class="setup-card-title">{info.name} Toolchain Not Detected</span>
            </div>
            <span class="setup-card-badge badge-fail">🔴 Missing</span>
          </div>
          <div class="setup-card-desc">{info.display_desc}</div>
          <div class="setup-meta-row">
            <span class="setup-meta-item">Package: <span class="setup-meta-highlight">{info.winget_package or 'Manual'}</span></span>
            <span>•</span>
            <span class="setup-meta-item">Target: <span class="setup-meta-highlight">Required to compile & run {info.name}</span></span>
          </div>
        </div>
        """
    )

    c_inst1, c_inst2, c_inst3 = st.columns([1.2, 1, 1], gap="small")
    with c_inst1:
        if info.winget_package:
            is_msys2_pacman = info.name == "C++" and Path(r"C:\msys64\usr\bin\pacman.exe").is_file()
            btn_label = "📥 Install UCRT64 Toolchain" if is_msys2_pacman else f"📥 Install {info.name} (winget)"
            spinner_msg = (
                "Installing UCRT64 C++ GCC toolchain via MSYS2 pacman..."
                if is_msys2_pacman
                else f"Installing {info.name} via Windows Package Manager (winget)..."
            )
            if st.button(btn_label, type="primary", key=f"btn_install_{info.name}", use_container_width=True):
                with st.spinner(spinner_msg):
                    success, msg = runtime_manager.install_runtime_winget(info.name)
                    if success:
                        st.success(msg)
                        time.sleep(1.0)
                        st.session_state.run_result = None
                        st.rerun()
                    else:
                        st.error(msg)
        else:
            if st.button(f"📥 Download {info.name}", type="primary", key=f"btn_install_{info.name}", use_container_width=True):
                runtime_manager.open_official_download(info.name)
                st.info(f"Opened official download portal for {info.name}.")

    with c_inst2:
        if st.button("🔄 Refresh Detection", key=f"btn_refresh_{info.name}", use_container_width=True):
            runtime_manager.refresh_system_path()
            runtime_manager.clear_runtime_cache()
            post_check = runtime_manager.detect_runtime(info.name, use_cache=False)
            if post_check.installed:
                st.success(f"🎉 {info.name} detected successfully ({post_check.version})!")
                st.session_state.run_result = None
            else:
                st.info(f"Refreshed. {info.name} is still not detected in system PATH.")
            st.rerun()

    with c_inst3:
        if st.button("🌐 Official Download", key=f"btn_download_{info.name}", use_container_width=True):
            runtime_manager.open_official_download(info.name)
            st.info(f"Opened official download website for {info.name}.")


def extract_optimized_code(markdown_text: str) -> str | None:
    """Extract code block from the ## Optimized code section or general markdown."""
    pattern = re.compile(
        r"##\s*Optimized code.*?\n```(?:[a-zA-Z0-9_+#-]+)?\r?\n([\s\S]*?)\r?\n```",
        re.IGNORECASE,
    )
    match = pattern.search(markdown_text)
    if match:
        return match.group(1)

    blocks = re.findall(r"```(?:[a-zA-Z0-9_+#-]+)?\r?\n([\s\S]*?)\r?\n```", markdown_text)
    if blocks:
        return max(blocks, key=len)

    return None


def run_analysis(mode: Mode, language: str, code: str) -> None:
    st.session_state.last_result = None
    st.session_state.run_result = None
    st.session_state.api_error = None

    if not code.strip():
        st.toast("⚠️ Paste some code before running an analysis.", icon="⚠️")
        return
    if not is_configured():
        msg = "GEMINI_API_KEY is not configured. Please set your key in Streamlit secrets, .env, or open Setup (⚙️)."
        st.toast("⚠️ GEMINI_API_KEY is not configured. Open Setup (⚙️) to configure.", icon="🔑")
        st.session_state.api_error = msg
        return

    prompt = build_prompt(mode, language, code)
    with st.spinner(f"🧠 Gemini is analyzing your code ({mode})..."):
        try:
            result = generate(prompt)
        except GeminiClientError as exc:
            st.toast(f"API Error: {exc}", icon="⚠️")
            st.session_state.api_error = str(exc)
            return
        except Exception as exc:
            st.toast(f"Unexpected error: {exc}", icon="❌")
            st.session_state.api_error = f"Unexpected error: {exc}"
            return

    st.session_state.last_result = result
    st.session_state.last_mode = mode
    st.session_state.last_language = language

    if mode == "optimize":
        optimized_code = extract_optimized_code(result)
        if optimized_code and optimized_code.strip():
            st.session_state.previous_code = code
            st.session_state.pending_code_update = optimized_code.strip()
            st.rerun()


def execute_code_action(language: str, code: str) -> None:
    st.session_state.last_result = None
    st.session_state.run_result = None
    st.session_state.api_error = None

    if not code.strip():
        st.toast("⚠️ Paste some code before running.", icon="⚠️")
        return

    with st.spinner(f"⚡ Running {language} code..."):
        result = run_code(language, code, timeout=5.0)

    st.session_state.run_result = result


FILE_NAMES = {
    "Python": "main.py",
    "C++": "main.cpp",
    "Java": "Main.java",
    "JavaScript": "main.js",
}

FILE_ICONS = {
    "Python": "🐍",
    "C++": "⚡",
    "Java": "☕",
    "JavaScript": "🟨",
}


def init_workspace_state() -> None:
    """Ensure all required workspace state keys exist on every workspace render."""
    saved_runtime = st.session_state.pop("saved_runtime", None)
    if "selected_runtime" not in st.session_state:
        st.session_state.selected_runtime = (
            saved_runtime if saved_runtime in SUPPORTED_LANGUAGES else "Python"
        )

    if "prev_runtime" not in st.session_state:
        st.session_state.prev_runtime = st.session_state.selected_runtime

    saved_code = st.session_state.pop("saved_code", None)
    if "code_input" not in st.session_state:
        if saved_code is not None:
            st.session_state.code_input = saved_code
        else:
            st.session_state.code_input = SAMPLE_SNIPPETS.get(
                st.session_state.selected_runtime, SAMPLE_SNIPPETS["Python"]
            )

    if "explorer_open" not in st.session_state:
        st.session_state.explorer_open = True

    if "pending_code_update" in st.session_state:
        st.session_state.code_input = st.session_state.pop("pending_code_update")


def main() -> None:
    t_rerun_start = time.perf_counter()

    st.set_page_config(
        page_title="CodeLens AI",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    t_css_0 = time.perf_counter()
    load_css()
    t_css_ms = (time.perf_counter() - t_css_0) * 1000

    # Check environment status with fast TTL cache
    t_stat_0 = time.perf_counter()
    sys_status = check_system_status()
    t_stat_ms = (time.perf_counter() - t_stat_0) * 1000

    # Judge-First Startup: If key exists in st.secrets or .env -> open IDE immediately
    has_key = gemini_client.is_configured()
    show_wizard = st.session_state.get("show_setup_wizard", False) if has_key else True

    if show_wizard:
        render_onboarding_wizard(sys_status)
        return

    # Initialize / restore workspace state keys on every workspace render
    init_workspace_state()

    t_ui_0 = time.perf_counter()
    render_hero()

    # Single Source of Truth for active runtime and file
    runtime = st.session_state.selected_runtime
    active_filename = FILE_NAMES.get(runtime, "main.py")
    file_icon = FILE_ICONS.get(runtime, "📄")

    # IDE Workspace Shell (Sidebar ~20% + Editor ~80%)
    col_sidebar, col_editor = st.columns([1, 4], gap="small")

    with col_sidebar:
        with st.container(border=True):
            render_html(
                """
                <div class="sidebar-header">
                  <span class="sidebar-header-icon">📂</span>
                  <span class="sidebar-header-title">EXPLORER</span>
                </div>
                <div class="sidebar-section-title">PROJECT</div>
                """
            )

            chevron = "▼" if st.session_state.explorer_open else "▶"
            if st.button(
                f"{chevron} 📁 CODELENS-WORKSPACE",
                key="toggle_explorer_btn",
                use_container_width=True,
            ):
                st.session_state.explorer_open = not st.session_state.explorer_open
                st.rerun()

            if st.session_state.explorer_open:
                files_html = []
                for lang, fname in FILE_NAMES.items():
                    icon = FILE_ICONS.get(lang, "📄")
                    is_active = (lang == runtime)
                    active_cls = "active" if is_active else ""
                    active_dot = '<span class="file-active-dot"></span>' if is_active else ""
                    files_html.append(
                        f'<div class="sidebar-file-item {active_cls}">'
                        f'<span class="file-icon">{icon}</span>'
                        f'<span class="file-name">{fname}</span>'
                        f'{active_dot}'
                        f'</div>'
                    )
                render_html(f'<div class="tree-children">{"".join(files_html)}</div>')

            render_html('<div class="sidebar-section-title">SWITCH RUNTIME</div>')

            def on_runtime_change() -> None:
                new_lang = st.session_state.selected_runtime
                prev_lang = st.session_state.get("prev_runtime", "Python")
                if new_lang != prev_lang:
                    current_code = st.session_state.get("code_input", "")
                    if current_code.strip() in {"", SAMPLE_SNIPPETS.get(prev_lang, "").strip()}:
                        st.session_state.code_input = SAMPLE_SNIPPETS[new_lang]
                    st.session_state.prev_runtime = new_lang

            lang_index = SUPPORTED_LANGUAGES.index(runtime) if runtime in SUPPORTED_LANGUAGES else 0
            st.selectbox(
                "Language",
                SUPPORTED_LANGUAGES,
                index=None if "selected_runtime" in st.session_state else lang_index,
                key="selected_runtime",
                on_change=on_runtime_change,
                label_visibility="collapsed",
                help="Choose the language of the snippet.",
            )

            render_html(
                """
                <div class="sidebar-section-title">SESSION</div>
                <div class="sidebar-session-card">
                  <div class="session-status-row">
                    <span class="session-pulse"></span>
                    <span class="session-text">Gemini Engine Ready</span>
                  </div>
                  <div class="session-sub">Model: Gemini 3.6 Flash</div>
                </div>

                <div class="sidebar-section-title">SHORTCUTS & TIPS</div>
                <div class="sidebar-tip-box">
                  <div class="tip-row"><span class="tip-kbd">Ctrl+Enter</span> <span class="tip-text">Quick Analyze</span></div>
                  <div class="tip-row"><span class="tip-bullet">💡</span> <span class="tip-text">Keep snippets focused</span></div>
                </div>
                """
            )

    with col_editor:
        with st.container(border=True):
            undo_available = bool(st.session_state.get("previous_code"))

            # Editor Tab Bar & Toolbar
            col_tab, col_undo = st.columns([3, 1], gap="small")
            with col_tab:
                render_html(
                    f"""
                    <div class="editor-tab-bar">
                      <div class="editor-tab active-tab">
                        <span class="tab-icon">{file_icon}</span>
                        <span class="tab-filename">{active_filename}</span>
                        <span class="tab-lang-badge">{runtime}</span>
                      </div>
                    </div>
                    """
                )
            with col_undo:
                if undo_available:
                    if st.button("↩ Undo Optimize", key="undo_optimize_btn", use_container_width=True):
                        st.session_state.pending_code_update = st.session_state.pop("previous_code")
                        st.rerun()

            current_code = st.session_state.get("code_input", "")
            if not current_code.strip():
                render_html(
                    """
                    <div class="editor-welcome-screen">
                      <div class="welcome-icon">⚡</div>
                      <div class="welcome-title">Welcome to CodeLens AI</div>
                      <div class="welcome-subtitle">Paste code or start typing to explain, improve, optimize, or run.</div>
                      <div class="welcome-runtimes">
                        <span class="runtime-tag">Python</span>
                        <span class="runtime-tag">JavaScript</span>
                        <span class="runtime-tag">C++</span>
                        <span class="runtime-tag">Java</span>
                      </div>
                    </div>
                    """
                )

            # Editor Frame with Fake Gutter + Textarea
            lines = current_code.splitlines() if current_code else []
            line_count = max(24, len(lines) if lines else 1)
            gutter_lines = "<br>".join(str(i) for i in range(1, line_count + 1))

            col_gutter, col_text = st.columns([0.045, 0.955], gap="small")
            with col_gutter:
                render_html(f'<div class="editor-gutter">{gutter_lines}</div>')
            with col_text:
                code = st.text_area(
                    "Code editor",
                    height=440,
                    key="code_input",
                    placeholder="Start typing or paste your code. Supported • Python • JavaScript • C++ • Java",
                    label_visibility="collapsed",
                )

            # Editor Status Bar
            current_lines = code.splitlines() if code else []
            active_line_count = len(current_lines) if current_lines else 1
            rt_info = runtime_manager.detect_runtime(runtime)
            rt_badge_text = rt_info.version_display
            rt_dot_cls = "dot-online" if rt_info.installed else "dot-fail"

            render_html(
                f"""
                <div class="editor-status-bar">
                  <div class="status-bar-left">
                    <span class="status-bullet">⚡</span>
                    <span class="status-bar-item">Powered by Gemini 3.6 Flash</span>
                    <span class="status-bar-divider">•</span>
                    <span class="status-bar-item">UTF-8</span>
                    <span class="status-bar-divider">•</span>
                    <span class="status-bar-item">Spaces: 4</span>
                  </div>
                  <div class="status-bar-right">
                    <span class="status-bar-item">Ln {active_line_count}, Col 1</span>
                    <span class="status-bar-divider">•</span>
                    <span class="status-indicator {rt_dot_cls}"></span>
                    <span class="status-bar-item lang-item">{rt_badge_text}</span>
                  </div>
                </div>
                """
            )

            # Command Bar (Action Buttons)
            cmd_col1, cmd_col2, cmd_col3, cmd_col4 = st.columns(4, gap="small")
            with cmd_col1:
                if st.button("Explain", type="primary", use_container_width=True):
                    run_analysis("explain", runtime, code)
            with cmd_col2:
                if st.button("Improve", use_container_width=True):
                    run_analysis("improve", runtime, code)
            with cmd_col3:
                if st.button("Optimize", use_container_width=True):
                    run_analysis("optimize", runtime, code)
            with cmd_col4:
                if st.button("▶ Run", use_container_width=True):
                    execute_code_action(runtime, code)

    # Output Dock (Terminal & Analysis Output)
    run_result: ExecutionResult | None = st.session_state.get("run_result")
    result = st.session_state.get("last_result")
    api_error: str | None = st.session_state.get("api_error")

    with st.container(border=True):
        if run_result:
            status_label = "Success" if run_result.is_success else "Failed"
            exit_str = f"exit code: {run_result.exit_code}" if run_result.exit_code is not None else "error"
            render_html(
                f"""
                <div class="dock-header">
                  <div class="dock-title-group">
                    <span class="dock-icon">▶</span>
                    <span class="dock-title">Execution Terminal</span>
                    <span class="chip status-{status_label.lower()}">{status_label} ({exit_str})</span>
                    <span class="chip metric-chip">⏱ {run_result.execution_time_ms:.1f}ms</span>
                  </div>
                </div>
                """
            )

            if run_result.is_missing_toolchain:
                render_runtime_install_card(runtime)
            elif run_result.is_timeout:
                st.error(f"⏱️ {run_result.error_message}")
            elif run_result.error_message and not run_result.stdout and not run_result.stderr:
                st.error(f"❌ {run_result.error_message}")
            else:
                if run_result.stderr:
                    st.markdown("**Errors / stderr:**")
                    st.code(run_result.stderr, language="text")
                if run_result.stdout:
                    st.markdown("**Output / stdout:**")
                    st.code(run_result.stdout, language="text")
                if not run_result.stdout and not run_result.stderr and run_result.is_success:
                    st.info("Code executed successfully with no output to stdout or stderr.")

        elif result:
            mode = st.session_state.get("last_mode", "explain")
            render_html(
                f"""
                <div class="dock-header">
                  <div class="dock-title-group">
                    <span class="dock-icon">⚡</span>
                    <span class="dock-title">Analysis Output</span>
                    <span class="chip mode-chip">{MODE_LABELS[mode]}</span>
                  </div>
                </div>
                """
            )
            render_html('<div class="dock-content">')
            st.markdown(result)
            render_html('</div>')
            st.download_button(
                "Export Result",
                data=result,
                file_name="codelens-result.md",
                mime="text/markdown",
                use_container_width=True,
            )
        elif api_error:
            render_html(
                f"""
                <div class="dock-header">
                  <div class="dock-title-group">
                    <span class="dock-icon">⚠️</span>
                    <span class="dock-title">API Notice</span>
                    <span class="chip status-failed">Attention</span>
                  </div>
                </div>
                <div class="dock-content terminal-prompt-view">
                  <div class="terminal-line terminal-system">Gemini API Notification</div>
                  <div class="terminal-line" style="color: #f87171;">⚠️ {api_error}</div>
                  <div class="terminal-line terminal-hint">The code editor remains fully interactive and usable above.</div>
                </div>
                """
            )
        else:
            render_html(
                """
                <div class="dock-header">
                  <div class="dock-title-group">
                    <span class="dock-icon">▶</span>
                    <span class="dock-title">Terminal & Dock</span>
                    <span class="chip mode-chip">Ready</span>
                  </div>
                </div>
                <div class="dock-content terminal-prompt-view">
                  <div class="terminal-line terminal-system">CodeLens AI [Workspace Terminal v2.5]</div>
                  <div class="terminal-line terminal-ready">⚡ Inference engine ready (Gemini 3.6 Flash) • All runtimes active</div>
                  <div class="terminal-line terminal-hint">Select code and click [Explain], [Improve], [Optimize], or [▶ Run] to view output.</div>
                  <div class="terminal-prompt-row">
                    <span class="terminal-ps1">codelens@workspace:~$</span>
                    <span class="terminal-cursor">█</span>
                  </div>
                </div>
                """
            )

    render_html('<p class="app-footer">CodeLens AI • Powered by Gemini 3.6 Flash • Cloud AI</p>')

    t_total_ms = (time.perf_counter() - t_rerun_start) * 1000
    t_ui_ms = (time.perf_counter() - t_ui_0) * 1000
    print(
        f"[Perf] Total rerun: {t_total_ms:.1f} ms | get_system_status: {t_stat_ms:.1f} ms | CSS: {t_css_ms:.1f} ms | UI render: {t_ui_ms:.1f} ms",
        flush=True,
    )


if __name__ == "__main__":
    main()

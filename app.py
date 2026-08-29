"""CodeLens AI - Streamlit Code Explainer."""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

import streamlit as st

from code_runner import ExecutionResult, run_code
from ollama_client import OllamaClientError, generate, is_running
from prompts import SUPPORTED_LANGUAGES, Mode, build_prompt

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


def load_css() -> None:
    if STYLES_PATH.exists():
        st.markdown(
            f"<style>{STYLES_PATH.read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
        )


def render_html(html_str: str) -> None:
    """Render raw HTML safely in Streamlit without markdown indentation artifacts."""
    cleaned = "\n".join(line.strip() for line in html_str.strip().splitlines())
    st.markdown(cleaned, unsafe_allow_html=True)


def render_hero() -> None:
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
                <div class="ide-subtitle">Offline AI • Qwen2.5-Coder 7B</div>
              </div>
            </div>
            <div class="ide-chips-section">
              <div class="ide-chip chip-online">
                <span class="status-indicator dot-online"></span>
                <span>Online</span>
              </div>
              <div class="ide-chip chip-model">
                <span class="chip-tag">MODEL</span>
                <span>Qwen 7B</span>
              </div>
              <div class="ide-chip chip-offline">
                <span class="status-indicator dot-offline"></span>
                <span>Offline Ready</span>
              </div>
            </div>
          </div>
          <div class="ide-status-strip">
            <div class="strip-left">
              <span class="strip-pulse-dot"></span>
              <span class="strip-text">Local Inference Engine Ready</span>
            </div>
            <div class="strip-right">
              <span class="strip-langs">Python • C++ • Java • JavaScript</span>
            </div>
          </div>
        </header>
        """
    )



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

    if not code.strip():
        st.warning("Paste some code before running an analysis.")
        return
    if not is_running():
        st.error("Ollama isn't running. Start Ollama and try again.")
        return

    prompt = build_prompt(mode, language, code)
    with st.spinner(f"🧠 Ollama is analyzing your code ({mode})..."):
        try:
            result = generate(prompt)
        except OllamaClientError as exc:
            st.error(str(exc))
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

    if not code.strip():
        st.warning("Paste some code before running.")
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


def main() -> None:
    st.set_page_config(
        page_title="CodeLens AI",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    if "pending_code_update" in st.session_state:
        st.session_state.code_input = st.session_state.pop("pending_code_update")

    load_css()
    render_hero()

    if "code_input" not in st.session_state:
        st.session_state.code_input = SAMPLE_SNIPPETS["Python"]

    if "selected_runtime" not in st.session_state:
        st.session_state.selected_runtime = "Python"
    if "prev_runtime" not in st.session_state:
        st.session_state.prev_runtime = "Python"
    if "explorer_open" not in st.session_state:
        st.session_state.explorer_open = True

    # Single Source of Truth for active runtime and file
    runtime = st.session_state.selected_runtime
    active_filename = FILE_NAMES.get(runtime, "main.py")
    file_icon = FILE_ICONS.get(runtime, "📄")

    # Phase H2 & H2.6: IDE Workspace Shell (Sidebar ~20% + Editor ~80%)
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
                index=lang_index,
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
                    <span class="session-text">Ollama Engine Ready</span>
                  </div>
                  <div class="session-sub">Model: Qwen2.5-Coder 7B</div>
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
            render_html(
                f"""
                <div class="editor-status-bar">
                  <div class="status-bar-left">
                    <span class="status-bar-item"><span class="status-bullet">⚡</span> Local AI Ready</span>
                    <span class="status-bar-divider">•</span>
                    <span class="status-bar-item">UTF-8</span>
                    <span class="status-bar-divider">•</span>
                    <span class="status-bar-item">Spaces: 4</span>
                  </div>
                  <div class="status-bar-right">
                    <span class="status-bar-item">Ln {active_line_count}, Col 1</span>
                    <span class="status-bar-divider">•</span>
                    <span class="status-bar-item lang-item">{runtime}</span>
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
                st.error(f"⚠️ {run_result.error_message}")
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
        else:
            # Default authentic VS Code terminal prompt
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
                  <div class="terminal-line terminal-ready">⚡ Inference engine ready (Qwen2.5-Coder 7B) • All runtimes active</div>
                  <div class="terminal-line terminal-hint">Select code and click [Explain], [Improve], [Optimize], or [▶ Run] to view output.</div>
                  <div class="terminal-prompt-row">
                    <span class="terminal-ps1">codelens@workspace:~$</span>
                    <span class="terminal-cursor">█</span>
                  </div>
                </div>
                """
            )

    render_html('<p class="app-footer">CodeLens AI • Local AI • Qwen2.5-Coder 7B</p>')


if __name__ == "__main__":
    main()


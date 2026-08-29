"""CodeLens AI - Streamlit Code Explainer."""

from __future__ import annotations

import re
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


def render_hero() -> None:
    st.markdown(
        """
        <section class="hero">
          <div class="eyebrow">College tech recruitment · Local AI · Qwen2.5-Coder 7B</div>
          <h1>CodeLens AI</h1>
          <p>
            Paste Python, C++, Java, or JavaScript and get a beginner-friendly explanation,
            a cleaner rewrite, or a faster version - in one click.
          </p>
          <div class="chip-row">
            <span class="chip">Explain</span>
            <span class="chip">Improve</span>
            <span class="chip">Optimize</span>
            <span class="chip">Complexity analysis</span>
            <span class="chip">▶ Run Code</span>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
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

    with st.container(border=True):
        col_lang, col_hint = st.columns([1, 2])
        with col_lang:
            language = st.selectbox(
                "Language",
                SUPPORTED_LANGUAGES,
                index=0,
                help="Choose the language of the pasted snippet.",
            )
            previous = st.session_state.get("prev_language", language)
            if language != previous:
                current = st.session_state.get("code_input", "")
                if current.strip() in {"", SAMPLE_SNIPPETS.get(previous, "").strip()}:
                    st.session_state.code_input = SAMPLE_SNIPPETS[language]
                st.session_state.prev_language = language
            else:
                st.session_state.prev_language = language
        with col_hint:
            if st.session_state.get("previous_code"):
                undo_col1, undo_col2 = st.columns([1.2, 1])
                with undo_col1:
                    st.caption("✨ Editor replaced with optimized code.")
                with undo_col2:
                    if st.button("↩ Undo Optimize", key="undo_optimize_btn", use_container_width=True):
                        st.session_state.pending_code_update = st.session_state.pop("previous_code")
                        st.rerun()
            else:
                st.caption(
                    "Tip: keep snippets focused. Large files work, but smaller functions get sharper answers."
                )

        code = st.text_area(
            "Code editor",
            height=340,
            key="code_input",
            placeholder="Paste your code here...",
            label_visibility="collapsed",
        )

        explain_col, improve_col, optimize_col, run_col = st.columns(4)
        with explain_col:
            if st.button("Explain", type="primary", use_container_width=True):
                run_analysis("explain", language, code)
        with improve_col:
            if st.button("Improve", use_container_width=True):
                run_analysis("improve", language, code)
        with optimize_col:
            if st.button("Optimize", use_container_width=True):
                run_analysis("optimize", language, code)
        with run_col:
            if st.button("▶ Run", use_container_width=True):
                execute_code_action(language, code)

    # Terminal-style output panel for Run Code
    run_result: ExecutionResult | None = st.session_state.get("run_result")
    if run_result:
        with st.container(border=True):
            status_label = "Success" if run_result.is_success else "Failed"
            exit_str = f"exit code: {run_result.exit_code}" if run_result.exit_code is not None else "error"
            st.markdown(
                f'<p class="result-title">▶ Execution Output &nbsp;<span class="chip" style="font-size: 0.76rem;">{status_label} ({exit_str})</span> &nbsp;<span class="chip" style="font-size: 0.76rem;">⏱ {run_result.execution_time_ms:.1f}ms</span></p>',
                unsafe_allow_html=True,
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

    # Analysis result panel for Explain, Improve, Optimize
    result = st.session_state.get("last_result")
    if result:
        mode = st.session_state.get("last_mode", "explain")
        with st.container(border=True):
            st.markdown(
                f'<p class="result-title">{MODE_LABELS[mode]} result</p>',
                unsafe_allow_html=True,
            )
            st.markdown(result)
            st.download_button(
                "Export Result",
                data=result,
                file_name="codelens-result.md",
                mime="text/markdown",
                use_container_width=True,
            )

    st.markdown(
        '<p class="app-footer">CodeLens AI • Local AI • Qwen2.5-Coder 7B</p>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

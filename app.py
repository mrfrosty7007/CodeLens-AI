"""CodeLens AI - Streamlit Code Explainer."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

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
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def run_analysis(mode: Mode, language: str, code: str) -> None:
    st.session_state.last_result = None

    if not code.strip():
        st.warning("Paste some code before running an analysis.")
        return
    if not is_running():
        st.error("Ollama isn't running. Start Ollama and try again.")
        return

    prompt = build_prompt(mode, language, code)
    with st.spinner("🧠 Ollama is analyzing your code..."):
        try:
            result = generate(prompt)
        except OllamaClientError as exc:
            st.error(str(exc))
            return

    st.session_state.last_result = result
    st.session_state.last_mode = mode
    st.session_state.last_language = language


def main() -> None:
    st.set_page_config(
        page_title="CodeLens AI",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
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

        explain_col, improve_col, optimize_col = st.columns(3)
        with explain_col:
            if st.button("Explain", type="primary", use_container_width=True):
                run_analysis("explain", language, code)
        with improve_col:
            if st.button("Improve", use_container_width=True):
                run_analysis("improve", language, code)
        with optimize_col:
            if st.button("Optimize", use_container_width=True):
                run_analysis("optimize", language, code)

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

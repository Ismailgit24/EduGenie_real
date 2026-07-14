"""
app.py — EduGenie AI
A simple, clean, PDF-first AI Education Assistant built with
Streamlit + Gemini (google-genai).

Flow:
1. Upload a PDF (or DOCX/TXT/image) on the "Study Material" page.
2. EduGenie reads it and can summarize, explain, make notes, quiz you,
   and generate homework — all grounded in that document.
3. The Homework page can both GIVE homework (from the material) and
   CHECK homework (your answers to it, or a separate uploaded file).
4. The Dashboard tracks your scores and recent activity.
"""

from datetime import datetime

import pandas as pd
import streamlit as st

import utils

# -----------------------------------------------------------------
# Page config
# -----------------------------------------------------------------
st.set_page_config(
    page_title="EduGenie AI",
    page_icon="🧞",
    layout="wide",
)

# -----------------------------------------------------------------
# Dark, minimalist theme (custom CSS)
# -----------------------------------------------------------------
st.markdown(
    """
    <style>
    :root{
        --bg:#0d0f13;
        --bg-card:#161920;
        --border:#242833;
        --text:#e8e9ec;
        --text-dim:#9298a5;
        --accent:#5b8cff;
        --accent-soft:rgba(91,140,255,0.12);
    }

    html, body, .stApp { background-color: var(--bg); }
    h1, h2, h3, h4 { color: var(--text); font-weight:600; letter-spacing:-0.01em; }
    p, span, label, li { color: var(--text-dim); }
    .stCaption, small { color: var(--text-dim) !important; }

    /* Sidebar */
    section[data-testid="stSidebar"]{
        background-color:#0a0b0e;
        border-right:1px solid var(--border);
    }
    section[data-testid="stSidebar"] * { color: var(--text) !important; }

    /* Buttons */
    .stButton > button{
        background-color: var(--accent);
        color:#0a0b0e;
        border:none;
        border-radius:10px;
        padding:0.5em 1.3em;
        font-weight:600;
        transition:0.15s ease;
    }
    .stButton > button:hover{ background-color:#7ba3ff; color:#0a0b0e; }

    /* Text inputs / text areas */
    .stTextInput input, .stTextArea textarea{
        background-color: var(--bg-card) !important;
        color: var(--text) !important;
        border:1px solid var(--border) !important;
        border-radius:10px !important;
    }

    /* File uploader */
    [data-testid="stFileUploaderDropzone"]{
        background-color: var(--bg-card);
        border:1px dashed var(--border);
        border-radius:12px;
    }
    [data-testid="stFileUploaderDropzone"] * { color: var(--text-dim) !important; }

    /* Cards */
    .edu-card{
        background-color: var(--bg-card);
        border:1px solid var(--border);
        border-radius:14px;
        padding:1.2em 1.4em;
        margin-bottom:1em;
    }
    .edu-card b { color: var(--text); }
    .edu-badge{
        display:inline-block;
        background-color: var(--accent-soft);
        color: var(--accent);
        border-radius:20px;
        padding:0.25em 0.9em;
        font-size:0.8em;
        font-weight:600;
        margin-bottom:0.6em;
    }

    /* Metrics */
    [data-testid="stMetricValue"]{ color: var(--accent); }
    [data-testid="stMetricLabel"]{ color: var(--text-dim); }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"]{ gap:4px; border-bottom:1px solid var(--border); }
    .stTabs [data-baseweb="tab"]{
        background-color: transparent;
        color: var(--text-dim);
        border-radius:8px 8px 0 0;
    }
    .stTabs [aria-selected="true"]{
        color: var(--accent) !important;
        border-bottom:2px solid var(--accent);
    }

    /* Progress bar */
    .stProgress > div > div { background-color: var(--accent) !important; }

    hr { border-color: var(--border); }

    /* Alerts (info/warning/error) keep readable text on dark bg */
    div[data-testid="stAlert"] { border-radius:10px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------
# Session state
# -----------------------------------------------------------------
defaults = {
    "doc_text": "",
    "doc_name": "",
    "chat_history": [],       # list of (question, answer) about the document
    "homework_questions": "",
    "last_score": None,
    "last_quiz": None,
    "activity": [],           # list of {type, title, time, score}
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


def log_activity(activity_type, title, score=None):
    """Add an entry to the recent-activity log used by the Dashboard."""
    st.session_state.activity.insert(0, {
        "type": activity_type,
        "title": title,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "score": score,
    })
    st.session_state.activity = st.session_state.activity[:15]


def card(title, body_markdown):
    """Render content inside a simple rounded 'card' box."""
    st.markdown(f"<div class='edu-card'><b>{title}</b><br><br>{body_markdown}</div>",
                unsafe_allow_html=True)


def load_document(uploaded_file):
    """Extract text from an uploaded file and store it as the active document."""
    with st.spinner("Reading your file..."):
        try:
            text = utils.extract_text_from_file(uploaded_file)
        except ValueError as e:
            st.error(f"⚠️ {e}")
            return
    st.session_state.doc_text = text
    st.session_state.doc_name = uploaded_file.name
    st.session_state.chat_history = []
    st.session_state.homework_questions = ""
    st.success(f"✅ Loaded **{uploaded_file.name}** — ready to study!")


# -----------------------------------------------------------------
# Sidebar navigation
# -----------------------------------------------------------------
st.sidebar.markdown("### 🧞 EduGenie AI")
page = st.sidebar.radio(
    "Navigate",
    ["Home", "Study Material", "Homework", "Dashboard"],
    label_visibility="collapsed",
)
st.sidebar.markdown("---")
if st.session_state.doc_name:
    st.sidebar.caption(f"📄 Active document: **{st.session_state.doc_name}**")
else:
    st.sidebar.caption("No document loaded yet.")

# ===================================================================
# PAGE: HOME
# ===================================================================
if page == "Home":
    st.title("🧞 EduGenie AI")
    st.write("Upload your study material and let AI turn it into summaries, "
             "explanations, quizzes, and homework — with instant checking.")

    col1, col2, col3 = st.columns(3)
    with col1:
        card("📄 Study Material", "Upload a PDF (or DOCX/TXT/image) and get "
             "summaries, simple explanations, notes, and quizzes from it.")
    with col2:
        card("📝 Homework", "Let EduGenie set homework from your material, "
             "then check your answers with a score and feedback.")
    with col3:
        card("📊 Dashboard", "Track your last score, last quiz, and recent "
             "activity — all in one place.")

    st.info("👈 Start by opening **Study Material** in the sidebar.")

# ===================================================================
# PAGE: STUDY MATERIAL
# ===================================================================
elif page == "Study Material":
    st.title("📄 Study Material")
    st.write("Upload your document — EduGenie will read it and help you study.")

    uploaded_file = st.file_uploader(
        "Upload a PDF, DOCX, TXT, PNG, JPG, or JPEG file",
        type=["pdf", "docx", "txt", "png", "jpg", "jpeg"],
    )
    if uploaded_file is not None and uploaded_file.name != st.session_state.doc_name:
        load_document(uploaded_file)

    if not st.session_state.doc_text:
        st.info("Upload a file above to get started.")
    else:
        # Quick NLP snapshot of the document
        stats = utils.get_text_stats(st.session_state.doc_text)
        s1, s2, s3 = st.columns(3)
        s1.metric("Word Count", stats["word_count"])
        s2.metric("Sentences", stats["sentence_count"])
        s3.metric("Avg. Word Length", stats["avg_word_length"])
        if stats["top_keywords"]:
            st.caption("🔑 Top keywords: " + ", ".join(stats["top_keywords"]))

        st.markdown("---")
        focus = st.text_input(
            "🎯 Focus on a specific topic (optional)",
            placeholder="e.g. Chapter 2, Photosynthesis — leave blank to use the whole document",
        )

        tab_summary, tab_explain, tab_notes, tab_quiz, tab_ask = st.tabs(
            ["Summary", "Explain", "Notes", "Quiz", "Ask a Question"]
        )

        with tab_summary:
            if st.button("Generate Summary"):
                with st.spinner("Summarizing..."):
                    try:
                        result = utils.summarize_document(st.session_state.doc_text, focus)
                        card("📄 Summary", result)
                        log_activity("Summary", focus or st.session_state.doc_name)
                    except RuntimeError as e:
                        st.error(str(e))

        with tab_explain:
            if st.button("Explain This"):
                with st.spinner("Explaining..."):
                    try:
                        result = utils.explain_document(st.session_state.doc_text, focus)
                        card("💡 Explanation", result)
                        log_activity("Explanation", focus or st.session_state.doc_name)
                    except RuntimeError as e:
                        st.error(str(e))

        with tab_notes:
            if st.button("Generate Notes"):
                with st.spinner("Writing notes..."):
                    try:
                        result = utils.generate_notes_from_document(st.session_state.doc_text, focus)
                        card("🗒️ Revision Notes", result)
                        log_activity("Notes", focus or st.session_state.doc_name)
                    except RuntimeError as e:
                        st.error(str(e))

        with tab_quiz:
            if st.button("Generate Quiz"):
                with st.spinner("Building your quiz..."):
                    try:
                        result = utils.generate_quiz_from_document(st.session_state.doc_text, focus)
                        card("❓ Quiz", result)
                        st.session_state.last_quiz = focus or st.session_state.doc_name
                        log_activity("Quiz", focus or st.session_state.doc_name)
                    except RuntimeError as e:
                        st.error(str(e))

        with tab_ask:
            for q, a in st.session_state.chat_history:
                st.markdown(f"**You:** {q}")
                st.markdown(f"**EduGenie:** {a}")

            question = st.text_input("Ask something about this document", key="doc_question")
            if st.button("Send", key="send_question"):
                if question.strip():
                    history_text = "\n".join(
                        f"Q: {q}\nA: {a}" for q, a in st.session_state.chat_history
                    )
                    with st.spinner("Thinking..."):
                        try:
                            answer = utils.answer_question_about_document(
                                st.session_state.doc_text, question, history_text
                            )
                            st.session_state.chat_history.append((question, answer))
                            st.rerun()
                        except RuntimeError as e:
                            st.error(str(e))
                else:
                    st.warning("Please type a question first.")

# ===================================================================
# PAGE: HOMEWORK (giver + checker)
# ===================================================================
elif page == "Homework":
    st.title("📝 Homework")

    tab_give, tab_check = st.tabs(["Get Homework", "Check Homework"])

    # ---------------- Get Homework ----------------
    with tab_give:
        if not st.session_state.doc_text:
            st.info("Upload a document on the **Study Material** page first.")
        else:
            st.write(f"Generate homework from **{st.session_state.doc_name}**.")
            focus = st.text_input(
                "🎯 Focus on a specific topic (optional)", key="hw_focus",
                placeholder="e.g. Chapter 2 — leave blank to use the whole document",
            )
            if st.button("Generate Homework"):
                with st.spinner("Preparing your homework..."):
                    try:
                        hw = utils.generate_homework_from_document(
                            st.session_state.doc_text, focus
                        )
                        st.session_state.homework_questions = hw
                        log_activity("Homework Assigned", focus or st.session_state.doc_name)
                    except RuntimeError as e:
                        st.error(str(e))

            if st.session_state.homework_questions:
                card("📚 Your Homework", st.session_state.homework_questions)
                st.caption("➡️ Go to the **Check Homework** tab once you've answered these.")

    # ---------------- Check Homework ----------------
    with tab_check:
        mode = st.radio(
            "How would you like to submit?",
            ["Answer the generated homework", "Upload a completed homework file"],
            horizontal=True,
        )

        if mode == "Answer the generated homework":
            if not st.session_state.homework_questions:
                st.info("Generate homework in the **Get Homework** tab first.")
            else:
                with st.expander("📚 View homework questions", expanded=False):
                    st.write(st.session_state.homework_questions)

                answers = st.text_area(
                    "✍️ Type your answers here (one per question is fine)",
                    height=200,
                    placeholder="1. My answer...\n2. My answer...",
                )
                if st.button("Check My Answers"):
                    if not answers.strip():
                        st.warning("Please type your answers first.")
                    else:
                        with st.spinner("EduGenie is grading your answers..."):
                            try:
                                result = utils.check_homework_answers(
                                    st.session_state.homework_questions,
                                    answers,
                                    st.session_state.doc_text,
                                )
                            except RuntimeError as e:
                                st.error(str(e))
                                result = None

                        if result:
                            score = result.get("score", 0)
                            st.session_state.last_score = score
                            log_activity("Homework Checked", st.session_state.doc_name, score=score)

                            st.markdown(
                                f"<div class='edu-badge'>Score: {score} / 100</div>",
                                unsafe_allow_html=True,
                            )
                            st.progress(min(max(int(score), 0), 100) / 100)

                            card("📄 Summary", result.get("summary", "—"))
                            card("✅ Checked Answers", result.get("checked_answers", "—"))
                            card("❌ Mistakes", result.get("mistakes", "—"))
                            card("🚀 Suggested Improvements", result.get("improvements", "—"))

                            practice_qs = result.get("practice_questions", [])
                            if practice_qs:
                                qs_html = "<br>".join(
                                    f"{i+1}. {q}" for i, q in enumerate(practice_qs)
                                )
                                card("📝 5 Similar Practice Questions", qs_html)

        else:  # Upload a completed homework file
            uploaded_file = st.file_uploader(
                "Upload a PDF, DOCX, TXT, PNG, JPG, or JPEG file",
                type=["pdf", "docx", "txt", "png", "jpg", "jpeg"],
                key="hw_upload",
            )
            if uploaded_file is not None and st.button("🔍 Check My Homework"):
                with st.spinner("Extracting text from your file..."):
                    try:
                        extracted_text = utils.extract_text_from_file(uploaded_file)
                    except ValueError as e:
                        st.error(f"⚠️ {e}")
                        extracted_text = None

                if extracted_text:
                    stats = utils.get_text_stats(extracted_text)
                    s1, s2, s3 = st.columns(3)
                    s1.metric("Word Count", stats["word_count"])
                    s2.metric("Sentences", stats["sentence_count"])
                    s3.metric("Avg. Word Length", stats["avg_word_length"])

                    with st.spinner("EduGenie is checking your homework..."):
                        try:
                            result = utils.check_homework(
                                extracted_text, st.session_state.doc_text
                            )
                        except RuntimeError as e:
                            st.error(str(e))
                            result = None

                    if result:
                        score = result.get("score", 0)
                        st.session_state.last_score = score
                        log_activity("Homework Checked", uploaded_file.name, score=score)

                        st.markdown(
                            f"<div class='edu-badge'>Score: {score} / 100</div>",
                            unsafe_allow_html=True,
                        )
                        st.progress(min(max(int(score), 0), 100) / 100)

                        card("📄 Summary", result.get("summary", "—"))
                        card("✅ Checked Answers", result.get("checked_answers", "—"))
                        card("❌ Mistakes", result.get("mistakes", "—"))
                        card("🚀 Suggested Improvements", result.get("improvements", "—"))

                        practice_qs = result.get("practice_questions", [])
                        if practice_qs:
                            qs_html = "<br>".join(
                                f"{i+1}. {q}" for i, q in enumerate(practice_qs)
                            )
                            card("📝 5 Similar Practice Questions", qs_html)

# ===================================================================
# PAGE: DASHBOARD
# ===================================================================
elif page == "Dashboard":
    st.title("📊 Dashboard")
    st.write("A quick snapshot of your learning activity.")

    d1, d2 = st.columns(2)
    with d1:
        score_display = (
            f"{st.session_state.last_score} / 100"
            if st.session_state.last_score is not None else "No homework checked yet"
        )
        card("🏆 Last Homework Score", score_display)
    with d2:
        quiz_display = st.session_state.last_quiz or "No quiz generated yet"
        card("❓ Last Quiz Topic", quiz_display)

    st.markdown("### 📈 Progress Chart (Homework Scores)")
    score_history = [
        a for a in reversed(st.session_state.activity)
        if a["type"] == "Homework Checked" and a["score"] is not None
    ]
    if score_history:
        df = pd.DataFrame({
            "Attempt": list(range(1, len(score_history) + 1)),
            "Score": [a["score"] for a in score_history],
        }).set_index("Attempt")
        st.line_chart(df)
    else:
        st.info("Check some homework to see your progress chart here.")

    st.markdown("### 🕒 Recent Activity")
    if st.session_state.activity:
        for a in st.session_state.activity:
            score_text = f" — Score: {a['score']}/100" if a["score"] is not None else ""
            card(f"{a['type']}: {a['title']}", f"🕒 {a['time']}{score_text}")
    else:
        st.info("No activity yet. Try Study Material or Homework!")
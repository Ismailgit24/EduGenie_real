"""
utils.py — Helper functions for EduGenie AI

Everything here is "logic", kept separate from the Streamlit UI (app.py):
- Qwen2.5 (via Hugging Face Inference Providers) client setup and calls
- File text extraction (PDF, DOCX, TXT, PNG, JPG, JPEG)
- Document-grounded AI features: summary, explanation, notes, quiz, homework
- Homework checking (both generated-homework answers and uploaded files)
- Simple NLP text statistics (using NLTK)
"""

import os
import re
import json
import base64
from io import BytesIO

import streamlit as st
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

import pdfplumber
import docx2txt
from PIL import Image

import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist

# -----------------------------------------------------------------
# Setup: load API key from .env
# -----------------------------------------------------------------
load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
# Text model — Qwen2.5-7B-Instruct via Hugging Face Inference Providers
MODEL_NAME = os.getenv("QWEN_MODEL", "Qwen/Qwen2.5-7B-Instruct")
# Qwen2.5-7B-Instruct has no vision support, so image OCR uses the VL sibling
VISION_MODEL_NAME = os.getenv("QWEN_VISION_MODEL", "Qwen/Qwen2.5-VL-7B-Instruct")

# Keep prompts from getting too large / expensive for a demo project
MAX_CONTEXT_CHARS = 12000


@st.cache_resource(show_spinner=False)
def get_client():
    """Create (and cache) the Hugging Face Inference client. Returns None if no token is set."""
    if not HF_TOKEN:
        return None
    return InferenceClient(api_key=HF_TOKEN)


@st.cache_resource(show_spinner=False)
def setup_nltk():
    """Download the small NLTK datasets we need, once per app run (quiet mode)."""
    for pkg in ["punkt", "punkt_tab", "stopwords"]:
        try:
            nltk.download(pkg, quiet=True)
        except Exception:
            pass
    return True


def _trim(text):
    """Trim very long documents so prompts stay a reasonable size."""
    text = text or ""
    if len(text) > MAX_CONTEXT_CHARS:
        return text[:MAX_CONTEXT_CHARS] + "\n...[content truncated for length]..."
    return text


# -----------------------------------------------------------------
# Core Qwen call (via Hugging Face Inference Providers)
# -----------------------------------------------------------------
def _image_to_data_url(image):
    """Convert a PIL image to a base64 data URL for multimodal chat messages."""
    buf = BytesIO()
    fmt = (image.format or "PNG").upper()
    if fmt not in ("PNG", "JPEG"):
        fmt = "PNG"
    image.save(buf, format=fmt)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    mime = "image/png" if fmt == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{b64}"


def ask_qwen(prompt, image=None):
    """
    Send a text prompt (and an optional PIL image) to Qwen2.5.
    Text-only prompts use Qwen2.5-7B-Instruct; prompts with an image use the
    Qwen2.5-VL-7B-Instruct vision model instead, since the plain 7B model
    can't read images.
    Returns the response text, or raises a friendly RuntimeError on failure.
    """
    client = get_client()
    if client is None:
        raise RuntimeError(
            "Hugging Face API token not found. Please add HF_TOKEN to your .env file "
            "and restart the app."
        )
    try:
        if image is None:
            messages = [{"role": "user", "content": prompt}]
            model = MODEL_NAME
        else:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": _image_to_data_url(image)}},
                    ],
                }
            ]
            model = VISION_MODEL_NAME

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=2048,
        )
        text = response.choices[0].message.content if response and response.choices else None
        if not text or not text.strip():
            raise RuntimeError("Qwen returned an empty response. Please try again.")
        return text.strip()
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Qwen request failed: {e}")


# Backwards-compatible alias (rest of this module was written against this name)
ask_gemini = ask_qwen


# -----------------------------------------------------------------
# Document-grounded AI Teacher features
# -----------------------------------------------------------------
def summarize_document(text, focus=""):
    focus_line = f" Pay special attention to: {focus}." if focus.strip() else ""
    prompt = (
        "You are a helpful teacher. Summarize the study material below in clear, "
        f"simple language, covering the key points a student must know.{focus_line}\n\n"
        f'Material:\n"""{_trim(text)}"""'
    )
    return ask_gemini(prompt)


def explain_document(text, focus=""):
    focus_topic = focus.strip() or "the main concepts covered in this material"
    prompt = (
        "You are a friendly, patient teacher. Based on the study material below, "
        f"explain '{focus_topic}' in very simple, easy-to-understand language, "
        "and include one short example.\n\n"
        f'Material:\n"""{_trim(text)}"""'
    )
    return ask_gemini(prompt)


def generate_notes_from_document(text, focus=""):
    focus_line = f" Focus on: {focus}." if focus.strip() else ""
    prompt = (
        "Create short, well-organized bullet-point revision notes from the study "
        f"material below, so a student can revise quickly before an exam.{focus_line}\n\n"
        f'Material:\n"""{_trim(text)}"""'
    )
    return ask_gemini(prompt)


def generate_quiz_from_document(text, focus="", num_questions=5):
    focus_line = f" Focus on: {focus}." if focus.strip() else ""
    prompt = (
        f"Create a quiz with {num_questions} multiple-choice questions based only on "
        f"the study material below.{focus_line} For each question give 4 options "
        "(A-D), clearly mark the correct answer, and add a one-line explanation. "
        "Number the questions.\n\n"
        f'Material:\n"""{_trim(text)}"""'
    )
    return ask_gemini(prompt)


def generate_homework_from_document(text, focus="", num_questions=5):
    focus_line = f" Focus on: {focus}." if focus.strip() else ""
    prompt = (
        f"Create a homework assignment with {num_questions} short-answer questions "
        f"based only on the study material below.{focus_line} Mix easy and medium "
        "difficulty questions. Number the questions clearly, one per line.\n\n"
        f'Material:\n"""{_trim(text)}"""'
    )
    return ask_gemini(prompt)


def answer_question_about_document(text, question, history=""):
    prompt = (
        "You are a teacher helping a student understand the study material below.\n\n"
        f'Material:\n"""{_trim(text)}"""\n\n'
        f"Conversation so far:\n{history}\n\n"
        f"Student's question: {question}\n"
        "Answer clearly and simply, using the material as your source of truth."
    )
    return ask_gemini(prompt)


# -----------------------------------------------------------------
# File text extraction
# -----------------------------------------------------------------
def extract_text_from_file(uploaded_file):
    """
    Extract text from an uploaded PDF, DOCX, TXT, PNG, JPG, or JPEG file.
    Images are read using Qwen2.5-VL's vision (OCR-style extraction).
    Returns the extracted text, or raises ValueError with a friendly message.
    """
    name = uploaded_file.name.lower()
    file_bytes = uploaded_file.read()

    try:
        if name.endswith(".pdf"):
            text = ""
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if not text.strip():
                raise ValueError("empty")
            return text.strip()

        elif name.endswith(".docx"):
            text = docx2txt.process(BytesIO(file_bytes))
            if not text or not text.strip():
                raise ValueError("empty")
            return text.strip()

        elif name.endswith(".txt"):
            text = file_bytes.decode("utf-8", errors="ignore")
            if not text.strip():
                raise ValueError("empty")
            return text.strip()

        elif name.endswith((".png", ".jpg", ".jpeg")):
            image = Image.open(BytesIO(file_bytes))
            prompt = (
                "Extract all readable text from this image exactly as written. "
                "Only return the extracted text, nothing else."
            )
            text = ask_gemini(prompt, image=image)
            if not text or not text.strip():
                raise ValueError("empty")
            return text.strip()

        else:
            raise ValueError("unsupported")

    except ValueError as ve:
        if str(ve) == "unsupported":
            raise ValueError(
                "Unsupported file type. Please upload a PDF, DOCX, TXT, PNG, JPG, or JPEG file."
            )
        raise ValueError(
            "Could not extract any readable text from this file (OCR/extraction "
            "returned nothing). Please try a clearer file or a different format."
        )
    except Exception:
        raise ValueError(
            "Something went wrong while reading this file. Please try again with "
            "a different file."
        )


# -----------------------------------------------------------------
# Homework checking (shared JSON grading logic)
# -----------------------------------------------------------------
def _grade_and_parse(prompt):
    """Send a grading prompt to Qwen and parse the JSON result safely."""
    raw = ask_gemini(prompt)
    cleaned = re.sub(r"^```json|^```|```$", "", raw.strip(), flags=re.MULTILINE).strip()

    try:
        data = json.loads(cleaned)
        data.setdefault("summary", "")
        data.setdefault("checked_answers", "")
        data.setdefault("mistakes", "")
        data.setdefault("improvements", "")
        data.setdefault("score", 0)
        data.setdefault("practice_questions", [])
    except Exception:
        data = {
            "summary": raw,
            "checked_answers": "",
            "mistakes": "",
            "improvements": "",
            "score": 0,
            "practice_questions": [],
        }
    return data


_JSON_INSTRUCTIONS = (
    "Respond ONLY with valid JSON (no markdown formatting, no extra text) using "
    "exactly this structure:\n"
    "{\n"
    '  "summary": "short summary of the homework",\n'
    '  "checked_answers": "evaluation of each answer - correct or wrong",\n'
    '  "mistakes": "explanation of the mistakes found",\n'
    '  "improvements": "suggestions to improve",\n'
    '  "score": <integer between 0 and 100>,\n'
    '  "practice_questions": ["question 1", "question 2", "question 3", '
    '"question 4", "question 5"]\n'
    "}"
)


def check_homework(homework_text, context=""):
    """
    Check an uploaded homework file. If `context` (source study material) is
    given, grade the answers against it for accuracy.
    """
    context_block = (
        f'Study material for reference:\n"""{_trim(context)}"""\n\n' if context.strip() else ""
    )
    prompt = (
        "You are a strict but helpful teacher checking a student's homework. "
        f"{context_block}"
        f'Student\'s homework:\n"""{homework_text}"""\n\n'
        f"{_JSON_INSTRUCTIONS}"
    )
    return _grade_and_parse(prompt)


def check_homework_answers(questions, answers, context=""):
    """
    Check a student's typed answers against homework that EduGenie itself
    generated. If `context` (source study material) is given, grade for
    accuracy against it.
    """
    context_block = (
        f'Study material for reference:\n"""{_trim(context)}"""\n\n' if context.strip() else ""
    )
    prompt = (
        "You are a strict but helpful teacher checking a student's homework "
        f"answers.\n\n{context_block}"
        f'Homework questions:\n"""{questions}"""\n\n'
        f'Student\'s answers:\n"""{answers}"""\n\n'
        f"{_JSON_INSTRUCTIONS}"
    )
    return _grade_and_parse(prompt)


# -----------------------------------------------------------------
# Simple NLP text statistics (uses NLTK)
# -----------------------------------------------------------------
def get_text_stats(text):
    """
    Compute simple NLP statistics for a piece of text using NLTK:
    word count, sentence count, average word length, and top keywords.
    """
    setup_nltk()
    try:
        words = word_tokenize(text)
        sentences = sent_tokenize(text)
        words_only = [w.lower() for w in words if w.isalpha()]

        try:
            stop_words = set(stopwords.words("english"))
        except Exception:
            stop_words = set()

        keywords = [w for w in words_only if w not in stop_words]
        freq = FreqDist(keywords)
        top_keywords = [w for w, _ in freq.most_common(8)]

        avg_word_len = (
            round(sum(len(w) for w in words_only) / len(words_only), 2)
            if words_only else 0
        )

        return {
            "word_count": len(words_only),
            "sentence_count": len(sentences),
            "avg_word_length": avg_word_len,
            "top_keywords": top_keywords,
        }
    except Exception:
        # Very safe fallback that never crashes the app
        return {
            "word_count": len(text.split()),
            "sentence_count": max(text.count(".") + text.count("!") + text.count("?"), 1),
            "avg_word_length": 0,
            "top_keywords": [],
        }

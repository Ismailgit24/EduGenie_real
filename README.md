# 🧞 EduGenie AI

A simple, clean, **PDF-first AI Education Assistant** built with **Streamlit**
and **Qwen2.5-7B-Instruct** via the **Hugging Face Inference Providers** API
(`huggingface_hub` SDK).

Upload your study material, and EduGenie reads it and turns it into
summaries, explanations, quizzes, and homework — with instant checking.
Minimalist dark UI.

---

## ✨ Features

### 📄 Study Material (upload once, use everywhere)
- Upload a **PDF** (also supports DOCX, TXT, PNG, JPG, JPEG)
- Text is extracted automatically (images are read using Qwen2.5-VL's vision/OCR)
- Quick NLP snapshot: word count, sentence count, top keywords (via **NLTK**)
- Optional "focus topic" to narrow any feature to one part of the document
- **Summary** — key points in simple language
- **Explain** — a concept from the document explained simply, with an example
- **Notes** — short bullet-point revision notes
- **Quiz** — multiple-choice quiz (with answers) generated from the document
- **Ask a Question** — follow-up Q&A chat grounded in the document

### 📝 Homework — Giver + Checker
- **Get Homework** — EduGenie generates a homework assignment from your document
- **Check Homework** — two ways to submit:
  - Type your answers to the generated homework directly in the app
  - Or upload a separate completed homework file (PDF/DOCX/TXT/image)
- Either way you get: a summary, checked answers, explained mistakes,
  improvement suggestions, a **score out of 100**, and **5 similar practice
  questions**
- Friendly error messages if text extraction/OCR fails

### 📊 Dashboard
- Last homework score
- Last quiz topic
- Recent activity log
- A simple progress chart of homework scores over time

---

## 📁 Project Structure

```
edugenie-ai/
├── app.py             # Streamlit UI (all pages)
├── utils.py           # Gemini calls, file extraction, NLP helpers
├── requirements.txt   # Python dependencies
├── .env.example        # Example environment file
└── README.md
```

---

## ⚙️ Setup Instructions

### 1. Make sure `app.py`, `utils.py`, and `requirements.txt` are in the same folder.

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Add your Hugging Face token
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Then open `.env` and add your real token (get one for free at
[Hugging Face](https://huggingface.co/settings/tokens) — needs "Inference" permission):
```
HF_TOKEN=your_real_token_here
```

### 5. Run the app
```bash
streamlit run app.py
```
The app opens at `http://localhost:8501`.

---

## 🧠 How it works

1. Go to **Study Material** and upload your PDF.
2. Use the tabs (Summary / Explain / Notes / Quiz / Ask a Question) to study it.
3. Go to **Homework → Get Homework** to have EduGenie set questions from
   the document.
4. Answer them in **Homework → Check Homework**, or upload a separate
   homework file — either way, get a score and feedback.
5. Check **Dashboard** to see your progress over time.

---

## 🧩 Notes

- Uses the **`huggingface_hub` SDK** to call models through Hugging Face
  Inference Providers.
- Default text model is `Qwen/Qwen2.5-7B-Instruct` (configurable via
  `QWEN_MODEL` in `.env`).
- Image OCR uses `Qwen/Qwen2.5-VL-7B-Instruct` (configurable via
  `QWEN_VISION_MODEL`), since the plain 7B model has no vision — no extra
  OCR software needs to be installed on your system.
- Dashboard data lives in the Streamlit session and resets if the app is
  restarted (no database, to keep the project simple).
- Very long documents are trimmed before being sent to Gemini to keep
  requests fast and reasonably priced.

---

## 🛠️ Tech Stack

- **Streamlit** – UI (custom dark, minimalist theme)
- **huggingface_hub** – Qwen2.5 (7B-Instruct / VL) via Hugging Face Inference Providers
- **pdfplumber / docx2txt** – text extraction from PDF/DOCX
- **Pillow** – image handling
- **NLTK** – simple NLP text statistics (word/sentence counts, keywords)
- **pandas** – dashboard progress chart data

---

Built for demonstration purposes — simple, readable, and beginner-friendly. 🎓

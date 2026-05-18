#  Python Quiz App — Web Version
**Introduction to Programming 2 — Final Project**  
Astana IT University | Group SE-2531

---

## How to Run Locally

```bash
pip install flask
python app.py
```

Then open your browser: **http://127.0.0.1:5000**

---

## File Structure

```
quiz_web/
├── app.py            ← Flask backend (all Python logic)
├── questions.json    ← Question bank (100 questions)
├── scores.json       ← Saved scores (auto-updated)
├── requirements.txt
└── templates/
    └── index.html    ← Frontend UI
```

---

## Python Concepts Used

| Concept | Where |
|---|---|
| OOP / Classes | `Question`, `Player`, `QuestionBank`, `ScoreBoard` |
| Decorators | `@log_attempt`, `@timer` on answer route |
| Generators | `question_generator()` in QuestionBank |
| Regex | Player name validation, answer checking |
| File I/O | JSON read/write for questions and scores |
| Exception Handling | `ValueError` on invalid player name |

---

## Quiz Modes

- **Random** — 10 random questions  
- **By Category** — Python, ICT, General Knowledge, English, IQ, EQ  
- **By Difficulty** — Easy / Medium / Hard  
- **Full Quiz** — All 100 questions  

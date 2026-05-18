import json
import re
import time
import random
import os
from functools import wraps
from flask import Flask, request, jsonify, render_template, session

app = Flask(__name__)
app.secret_key = "quiz_app_secret_2024"


# ── Decorators ──────────────────────────────────────────────────────────────

def log_attempt(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"[LOG] Starting: {func.__name__} at {time.strftime('%H:%M:%S')}")
        result = func(*args, **kwargs)
        print(f"[LOG] Finished: {func.__name__}")
        return result
    return wrapper


def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"[TIMER] {func.__name__} took {end - start:.2f} seconds")
        return result
    return wrapper


# ── Classes ──────────────────────────────────────────────────────────────────

class Question:
    def __init__(self, data: dict):
        self.id = data["id"]
        self.category = data["category"]
        self.text = data["question"]
        self.options = data["options"]
        self.answer_index = data["answer"]
        self.difficulty = data["difficulty"]

    def correct_answer(self) -> str:
        return self.options[self.answer_index]

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "text": self.text,
            "options": self.options,
            "answer_index": self.answer_index,
            "difficulty": self.difficulty
        }

    def __str__(self):
        return f"[{self.category}] {self.text}"


class Player:
    def __init__(self, name: str):
        self.name = self._validate_name(name)
        self.score = 0
        self.total = 0
        self.history = []

    def _validate_name(self, name: str) -> str:
        if not re.match(r'^[A-Za-z\s]{2,30}$', name):
            raise ValueError("Name must be 2-30 letters only.")
        return name.strip().title()

    def record(self, question_text: str, category: str, correct: bool, time_taken: float):
        self.total += 1
        if correct:
            self.score += 1
        self.history.append({
            "question": question_text,
            "category": category,
            "correct": correct,
            "time_taken": round(time_taken, 2)
        })

    def percentage(self) -> float:
        if self.total == 0:
            return 0.0
        return round((self.score / self.total) * 100, 1)

    def grade(self) -> str:
        p = self.percentage()
        if p >= 90:
            return "A"
        elif p >= 75:
            return "B"
        elif p >= 60:
            return "C"
        elif p >= 50:
            return "D"
        return "F"

    def to_dict(self):
        return {
            "name": self.name,
            "score": self.score,
            "total": self.total,
            "history": self.history
        }

    def __str__(self):
        return f"Player({self.name}, Score: {self.score}/{self.total})"


class QuestionBank:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.questions = self._load()

    def _load(self) -> list:
        with open(self.filepath, "r") as f:
            data = json.load(f)
        return [Question(q) for q in data]

    def by_category(self, category: str) -> list:
        return [q for q in self.questions if q.category.lower() == category.lower()]

    def by_difficulty(self, difficulty: str) -> list:
        return [q for q in self.questions if q.difficulty == difficulty]

    def categories(self) -> list:
        return list(set(q.category for q in self.questions))

    def random_questions(self, count: int) -> list:
        count = min(count, len(self.questions))
        return random.sample(self.questions, count)

    def question_generator(self, questions: list):
        for q in questions:
            yield q


class ScoreBoard:
    FILEPATH = os.path.join(os.path.dirname(__file__), "scores.json")

    def __init__(self):
        self.records = self._load()

    def _load(self) -> list:
        if os.path.exists(self.FILEPATH):
            with open(self.FILEPATH, "r") as f:
                return json.load(f)
        return []

    def save(self, player: Player, mode: str):
        entry = {
            "name": player.name,
            "score": player.score,
            "total": player.total,
            "percentage": player.percentage(),
            "grade": player.grade(),
            "mode": mode,
            "timestamp": time.strftime("%Y-%m-%d %H:%M")
        }
        self.records.append(entry)
        with open(self.FILEPATH, "w") as f:
            json.dump(self.records, f, indent=2)

    def top_scores(self, limit: int = 10) -> list:
        sorted_records = sorted(self.records, key=lambda x: x["percentage"], reverse=True)
        return sorted_records[:limit]


# ── Globals ──────────────────────────────────────────────────────────────────

BANK = QuestionBank(os.path.join(os.path.dirname(__file__), "questions.json"))
SCOREBOARD = ScoreBoard()


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/categories", methods=["GET"])
def get_categories():
    cats = sorted(BANK.categories())
    return jsonify({"categories": cats})


@app.route("/api/start", methods=["POST"])
def start_quiz():
    data = request.json
    name = data.get("name", "").strip()
    mode = data.get("mode", "random")
    category = data.get("category", "")
    difficulty = data.get("difficulty", "easy")

    try:
        player = Player(name)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if mode == "random":
        questions = BANK.random_questions(10)
        label = "Random"
    elif mode == "category":
        questions = BANK.by_category(category)
        label = category
    elif mode == "difficulty":
        questions = BANK.by_difficulty(difficulty)
        label = difficulty.capitalize()
    elif mode == "full":
        questions = BANK.questions
        label = "Full Quiz"
    else:
        questions = BANK.random_questions(10)
        label = "Random"

    if not questions:
        return jsonify({"error": "No questions found for that selection."}), 400

    random.shuffle(questions)

    session["player"] = player.to_dict()
    session["questions"] = [q.to_dict() for q in questions]
    session["current"] = 0
    session["mode"] = label
    session["start_time"] = time.time()

    return jsonify({
        "total": len(questions),
        "player": player.name
    })


@app.route("/api/question", methods=["GET"])
def get_question():
    if "questions" not in session:
        return jsonify({"error": "No active quiz"}), 400

    index = session.get("current", 0)
    questions = session["questions"]

    if index >= len(questions):
        return jsonify({"done": True})

    q = questions[index]
    return jsonify({
        "index": index,
        "total": len(questions),
        "id": q["id"],
        "text": q["text"],
        "category": q["category"],
        "difficulty": q["difficulty"],
        "options": q["options"]
    })


@app.route("/api/answer", methods=["POST"])
@log_attempt
def submit_answer():
    data = request.json
    selected = data.get("selected")
    time_taken = data.get("time_taken", 0)

    if "questions" not in session:
        return jsonify({"error": "No active quiz"}), 400

    index = session.get("current", 0)
    questions = session["questions"]

    if index >= len(questions):
        return jsonify({"done": True})

    q = questions[index]
    correct_index = q["answer_index"]
    is_correct = selected == correct_index

    player_data = session["player"]
    player_data["total"] = player_data.get("total", 0) + 1
    if is_correct:
        player_data["score"] = player_data.get("score", 0) + 1
    if "history" not in player_data:
        player_data["history"] = []
    player_data["history"].append({
        "question": q["text"],
        "category": q["category"],
        "correct": is_correct,
        "time_taken": round(time_taken, 2)
    })

    session["player"] = player_data
    session["current"] = index + 1

    return jsonify({
        "correct": is_correct,
        "correct_index": correct_index,
        "correct_answer": q["options"][correct_index]
    })


@app.route("/api/result", methods=["GET"])
def get_result():
    if "player" not in session:
        return jsonify({"error": "No quiz data"}), 400

    player_data = session["player"]
    score = player_data.get("score", 0)
    total = player_data.get("total", 0)
    history = player_data.get("history", [])

    if total == 0:
        percentage = 0.0
    else:
        percentage = round((score / total) * 100, 1)

    p = percentage
    if p >= 90:
        grade = "A"
    elif p >= 75:
        grade = "B"
    elif p >= 60:
        grade = "C"
    elif p >= 50:
        grade = "D"
    else:
        grade = "F"

    wrong = [h for h in history if not h["correct"]]

    player = Player.__new__(Player)
    player.name = player_data["name"]
    player.score = score
    player.total = total
    player.history = history

    SCOREBOARD.records = ScoreBoard()._load()
    SCOREBOARD.save(player, session.get("mode", "Random"))

    return jsonify({
        "name": player_data["name"],
        "score": score,
        "total": total,
        "percentage": percentage,
        "grade": grade,
        "wrong": wrong
    })


@app.route("/api/leaderboard", methods=["GET"])
def leaderboard():
    sb = ScoreBoard()
    return jsonify({"scores": sb.top_scores(10)})


if __name__ == "__main__":
    app.run(debug=True)

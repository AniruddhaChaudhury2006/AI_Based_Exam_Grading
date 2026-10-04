```markdown
# AI-Powered Autonomous Examination Grading & Diagnostics Pipeline

An intelligent, multi-stage assessment platform that reads handwritten student scripts and question paper blueprints, parses complex sectional constraints, executes lenient fractional grading, and surfaces gamified debugging diagnostics.

## Key Features

- **Twin-Stream Vision Extraction:** Decoupled pipelines for analyzing master rubrics and parsing handwritten student script pages[cite: 1].
- **Dynamic Sectional Rule Engine:** Automatically manages section choices and optimizes scoring pools[cite: 1].
- **Lenient Fractional Grading:** Uses multi-step rubric alignment to award partial credit rather than binary outcomes[cite: 1].
- **Gamified Diagnostics:** Translates score deductions into "Active Quests" and bug descriptions with XP tracking and celebratory level-up triggers[cite: 1, 3].
- **Database Persistence & Human-in-the-Loop (HITL):** Saves assessment data to SQLite via SQLAlchemy with real-time score adjustment endpoints[cite: 3, 4, 6, 7].

---

## Detailed Tech Stack Breakdown

The project relies on a modern, lightweight, and robust technology stack optimized for multimodal AI processing and rapid prototyping:

* **Backend Framework (`FastAPI`):** Powers the asynchronous REST API server, handling multipart form uploads, dependency injection, and automatic OpenAPI documentation generation[cite: 4].
* **Database & ORM (`SQLite` & `SQLAlchemy`):** Provides zero-configuration relational data persistence for saving assessment records, historical performance metrics, and question evaluations[cite: 4, 6, 7].
* **Data Validation & Typing (`Pydantic v2`):** Enforces strict structural boundaries, model validation, and dynamic sectional calculations for all AI-generated assessment payloads[cite: 1].
* **Multimodal AI Engine (`LangChain Google GenAI` / `Gemini 2.5 Flash`):** Serves as the core intelligence engine responsible for visual layout parsing, structured rubric extraction, raw text transcription, and rubric-based grading[cite: 1].
* **Frontend Interface (`HTML5`, `Vanilla JavaScript`, `CSS3`, `Canvas Confetti`):** Implements a clean, single-file dashboard (`index.html`) that handles asynchronous API requests, dynamic state updates, score overrides, and interactive celebration animations[cite: 3].

---

## Project Structure

```text
IEDC_APP/
├── main.py            # FastAPI application server and REST endpoints[cite: 4]
├── engines.py         # Autonomous grading engine & Pydantic normalization schemas[cite: 1]
├── database.py        # SQLAlchemy database session configuration[cite: 6]
├── db_models.py       # ORM models for assessments and question evaluations[cite: 7]
├── index.html         # Frontend dashboard interface[cite: 3]
└── requirements.txt   # Python dependencies

```

---

## Setup & Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt

```

### 2. Configure Environment Variable

Set your Gemini API key in your environment:

```bash
export GEMINI_API_KEY="your-google-gemini-api-key"

```

### 3. Run the Backend Server

```bash
python main.py

```

The server will start locally at `http://127.0.0.1:8000`, and the database (`grading_app.db`) will generate automatically.

### 4. Launch the Dashboard

Open `index.html` directly in your browser or serve it via a local static server to interact with the grading interface.

---

## API Endpoints Reference

| Method | Endpoint | Description |
| --- | --- | --- |
| **POST** | `/api/v1/grade-autonomous` | Upload question papers and answer sheets to run the grading pipeline.

 |
| **GET** | `/api/v1/assessments` | Fetch all historical assessment records.

 |
| **PUT** | `/api/v1/question-evaluation/{eval_id}/override` | Perform manual score overrides with live database synchronization.

 |

```

```

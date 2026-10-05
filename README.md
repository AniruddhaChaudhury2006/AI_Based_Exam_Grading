# AI-Powered Autonomous Examination Grading & Diagnostics Pipeline

Welcome to the AI-Powered Autonomous Examination Grading & Diagnostics Pipeline. This project is an advanced, multi-stage assessment platform designed to eliminate the tedious bottlenecks of manual evaluation. By seamlessly combining multimodal AI vision, structured data parsing, relational persistence, and gamified diagnostics, it reads handwritten student scripts and question paper blueprints, parses complex sectional constraints, executes lenient fractional grading, and transforms score deductions into actionable debugging quests.

# Detailed Code Architecture & Component Explanation

To understand how the codebase works under the hood, let's break down each file, its specific responsibilities, and how they interact to form a unified grading pipeline:

- **`main.py` (FastAPI Application Server & REST Endpoints):** This serves as the entry point for the entire application backend. It initializes the FastAPI instance, configures CORS middleware, and sets up asynchronous REST routes. It exposes the primary upload endpoint (`/api/v1/grade-autonomous`) which accepts multipart form data containing question paper files and handwritten answer sheet scans. When requests come in, it delegates the files to the grading engine, handles database session commits, and exposes retrieval and manual override endpoints.
- **`engines.py` (Autonomous Grading Engine & Pydantic Normalization):** This is the core cognitive engine of the project. It integrates with LangChain and Google's Gemini multimodal models to process visual inputs. It runs a twin-stream vision extraction process that analyzes the master rubric separately from the student's messy handwritten script. Furthermore, it defines strict **Pydantic v2 schemas** that enforce data validation, structure the JSON outputs returned by the LLM, handle dynamic score capping, and execute sectional rule evaluations (such as choosing the best $N$ answers out of a given set).
- **`database.py` (SQLAlchemy Database Session Configuration):** Responsible for managing the persistence layer infrastructure. It initializes the SQLite database engine (`grading_app.db`), creates session local factories, and handles base declarative mapping classes. It ensures thread-safe session management so that API requests can safely read and write evaluation states without blocking or causing race conditions.
- **`db_models.py` (ORM Models for Assessments and Question Evaluations):** Defines the structural database tables using SQLAlchemy ORM. It establishes relational models such as `Assessment` (storing metadata, student IDs, total scores, and timestamps) and `QuestionEvaluation` (storing granular question-by-question breakdowns, earned marks, rubric alignment notes, and override flags). It maps foreign keys to link individual question evaluations directly back to their parent assessment record.
- **`index.html` (Frontend Dashboard Interface):** A fully self-contained single-file frontend dashboard built with HTML5, vanilla JavaScript, and modern CSS/Tailwind-inspired utility classes. It provides an intuitive drag-and-drop file upload interface, renders asynchronous processing states, displays real-time score breakdowns, and incorporates interactive Human-in-the-Loop (HITL) score override controls. It also uses **Canvas Confetti** to trigger celebratory animations whenever perfect scores or level-up milestones are achieved.
- **`requirements.txt` (Python Dependencies):** A clean manifest file specifying exact package versions required to run the project, including `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `langchain-google-genai`, and supporting libraries.

# Key Features
- **Twin-Stream Vision Extraction:** Uses decoupled pipelines to analyze master rubrics and parse handwritten student script pages separately, preventing layout cross-contamination.
- **Dynamic Sectional Rule Engine:** Automatically manages section choices (like attempting any 3 questions from Section B) and optimizes scoring pools based on best-answer rules.
- **Lenient Fractional Grading:** Uses multi-step rubric alignment to award fair partial credit rather than sticking to harsh binary outcomes, deducting incremental points for minor conceptual gaps.
- **Gamified Diagnostics:** Turns score deductions into "Active Quests" and bug descriptions complete with XP tracking, bug classifications, and celebratory level-up triggers.
- **Database Persistence & Human-in-the-Loop (HITL):** Saves assessment data straight to SQLite via SQLAlchemy while letting educators make real-time score adjustments on the fly with live database synchronization.

# Project Structure
IEDC_APP/
├── main.py            # FastAPI application server and REST endpoints
├── engines.py         # Autonomous grading engine & Pydantic normalization schemas
├── database.py        # SQLAlchemy database session configuration
├── db_models.py       # ORM models for assessments and question evaluations
├── index.html         # Frontend dashboard interface
└── requirements.txt   # Python dependencies

# Setup & Installation
1. Install Dependencies:
   pip install -r requirements.txt
2. Configure Environment Variable:
   export GEMINI_API_KEY="your-google-gemini-api-key"
3. Run the Backend Server:
   python main.py
   (The server will spin up locally at http://127.0.0.1:8000, and grading_app.db will generate automatically)
4. Launch the Dashboard:
   Open index.html right in your web browser or serve it via a local static server to start grading.

# API Endpoints Reference
- POST /api/v1/grade-autonomous: Upload your question papers and answer sheets to kick off the grading pipeline.
- GET /api/v1/assessments: Fetch all saved historical assessment records from the database.
- PUT /api/v1/question-evaluation/{eval_id}/override: Perform manual score overrides with live database synchronization.

import os
import traceback
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Import Autonomous Grading Engine and Pydantic Schemas
from engines import AutonomousGradingEngine, FullGamifiedAssessment

# Import Database setup and ORM models from database.py and db_models.py
from database import engine as db_engine, Base, get_db
import db_models

# Automatically create SQL tables on application startup if they don't exist
Base.metadata.create_all(bind=db_engine)

app = FastAPI(title="Written Exam & HITL Autonomous Grading Engine Core")

# Enable Cross-Origin Resource Sharing (CORS) for external frontend dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the Autonomous Grading Engine using environment key or fallback
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "<Your API Key>")
engine = AutonomousGradingEngine(api_key=GEMINI_API_KEY)


@app.post(
    "/api/v1/grade-autonomous", 
    response_model=FullGamifiedAssessment,
    summary="Evaluate purely handwritten exam answer scripts against question paper blueprints with gamification analytics and database persistence."
)
async def grade_autonomous_endpoint(
    question_paper: List[UploadFile] = File(..., description="One or more images containing the master question paper layout and rules."),
    answer_sheet: List[UploadFile] = File(..., description="One or more images containing the student's handwritten answer script pages."),
    db: Session = Depends(get_db)
):
    """
    Asynchronously accepts multipart form image uploads for both the question paper and 
    the student's written response script. Converts them to in-memory byte strings,
    runs them through the multi-stage structural transcription and grading matrix,
    and persists the output into the database.
    """
    all_files = question_paper + answer_sheet
    
    # Safe fallback parsing and defense guardrail for missing or invalid media headers
    for f in all_files:
        content_type = f.content_type or ""
        if not content_type.startswith("image/"):
            raise HTTPException(
                status_code=400, 
                detail="Validation Error: All uploaded documents must be valid images (JPEG, PNG, etc.). PDFs are not supported."
            )
    
    try:
        # Asynchronously stream multi-page assets into binary buffers without locking server RAM
        paper_images_bytes = [await file.read() for file in question_paper]
        sheet_images_bytes = [await file.read() for file in answer_sheet]
        
        # Dispatch to the multi-stage text transcription, sorting, and choice-capping loop
        result = engine.evaluate_with_question_paper(
            paper_images_bytes=paper_images_bytes,
            sheet_images_bytes=sheet_images_bytes
        )
        
        # -----------------------------------------------------------------
        # 1. PERSIST MAIN ASSESSMENT RECORD
        # -----------------------------------------------------------------
        db_assessment = db_models.AssessmentRecord(
            student_id=result.student_id,
            max_paper_marks=result.max_paper_marks,
            total_score=result.total_score,
            total_xp=result.total_xp,
            level_up_unlocked=result.level_up_unlocked
        )
        db.add(db_assessment)
        db.commit()
        db.refresh(db_assessment)

        # -----------------------------------------------------------------
        # 2. PERSIST INDIVIDUAL QUESTION EVALUATIONS
        # -----------------------------------------------------------------
        for eval_item in result.assessments:
            db_eval = db_models.QuestionEvaluationRecord(
                assessment_id=db_assessment.id,
                question_number=eval_item.question_number,
                section_identifier=eval_item.section_identifier,
                question_type=eval_item.question_type,
                grading_scratchpad=eval_item.grading_scratchpad,
                extracted_student_input=eval_item.extracted_student_input,
                master_key_answer=eval_item.master_key_answer,
                marks_awarded=eval_item.marks_awarded,
                max_possible_marks=eval_item.max_possible_marks,
                justification=eval_item.justification,
                is_buggy=eval_item.gamification.is_buggy,
                bug_description=eval_item.gamification.bug_description,
                quest_directive=eval_item.gamification.quest_directive,
                xp_earned=eval_item.gamification.xp_earned
            )
            db.add(db_eval)

        db.commit()

        # Returning the instantiated Pydantic object directly ensures FastAPI triggers 
        # downstream schema serialization and preserves post-model validator calculations.
        return result
        
    except Exception as e:
        db.rollback()  # Rollback pending database transactions on execution failure
        print("\n" + "="*40 + " CRITICAL BACKEND TRACEBACK " + "="*40)
        traceback.print_exc() 
        print("="*108 + "\n")
        raise HTTPException(
            status_code=500, 
            detail=f"Grading Core Framework Error: {str(e)}"
        )


# ---------------------------------------------------------------------
# ADDITIONAL DATABASE CRUD ENDPOINTS
# ---------------------------------------------------------------------

@app.get(
    "/api/v1/assessments",
    summary="Retrieve all historical assessment records saved in the database."
)
def get_all_assessments(db: Session = Depends(get_db)):
    """Fetches all past evaluated assessments ordered by creation timestamp."""
    return db.query(db_models.AssessmentRecord).order_by(
        db_models.AssessmentRecord.created_at.desc()
    ).all()


@app.put(
    "/api/v1/question-evaluation/{eval_id}/override",
    summary="Update a question evaluation score via Human-In-The-Loop manual override."
)
def update_manual_score(eval_id: int, new_score: float, db: Session = Depends(get_db)):
    """Updates a single question evaluation score in the database."""
    eval_record = db.query(db_models.QuestionEvaluationRecord).filter(
        db_models.QuestionEvaluationRecord.id == eval_id
    ).first()
    
    if not eval_record:
        raise HTTPException(status_code=404, detail="Question evaluation record not found")

    eval_record.marks_awarded = new_score
    eval_record.xp_earned = 10.0 if new_score > 0 else 0.0
    
    db.commit()
    return {"status": "success", "updated_id": eval_id, "new_score": new_score}


if __name__ == "__main__":
    import uvicorn
    # Expose socket layers across all localized network cards to allow container orchestration
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
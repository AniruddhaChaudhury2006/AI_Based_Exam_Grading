from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class AssessmentRecord(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, index=True, default="Unknown Student")
    max_paper_marks = Column(Float)
    total_score = Column(Float)
    total_xp = Column(Float)
    level_up_unlocked = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)

    # One-to-Many Relationship with Individual Question Evaluations
    evaluations = relationship("QuestionEvaluationRecord", back_populates="assessment", cascade="all, delete-orphan")


class QuestionEvaluationRecord(Base):
    __tablename__ = "question_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"))
    
    question_number = Column(Integer)
    section_identifier = Column(String)
    question_type = Column(String)
    grading_scratchpad = Column(Text)
    extracted_student_input = Column(Text)
    master_key_answer = Column(Text)
    marks_awarded = Column(Float)
    max_possible_marks = Column(Float)
    justification = Column(Text)

    # Gamification Metrics
    is_buggy = Column(Boolean)
    bug_description = Column(Text)
    quest_directive = Column(Text)
    xp_earned = Column(Float)

    assessment = relationship("AssessmentRecord", back_populates="evaluations")
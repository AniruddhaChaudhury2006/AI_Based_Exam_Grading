import base64
import json
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field, model_validator, field_validator
from typing import List, Optional, Dict, Any

# =====================================================================
# 1. PYDANTIC SCHEMAS FOR DATA NORMALIZATION
# =====================================================================

class QuestMetrics(BaseModel):
    is_buggy: bool = Field(default=False, description="True if the student lost ANY marks on this question.")
    bug_description: Optional[str] = Field(default="", description="Description of the error or knowledge gap if any.")
    quest_directive: str = Field(default="Review this item.", description="Actionable feedback directive.")
    xp_earned: float = Field(default=0.0, description="XP awarded dynamically up to 10.0.")

class GamifiedEvaluation(BaseModel):
    question_number: int = Field(description="The exact question number identifier.")
    section_identifier: str = Field(default="A", description="Section identifier (e.g., 'A', 'B').")
    question_type: str = Field(default="Theory", description="Classification of written answer.")
    grading_scratchpad: str = Field(default="", description="Internal reasoning path analyzing student response.")
    extracted_student_input: str = Field(description="The fully consolidated and stitched student text.")
    master_key_answer: str = Field(description="The ground-truth marking rubric/keys.")
    marks_awarded: float = Field(default=0.0, description="The final evaluated score assigned.")
    max_possible_marks: float = Field(default=1.0, description="Maximum marks achievable.")
    justification: str = Field(default="", description="Granular explanation for the score.")
    gamification: QuestMetrics

    @field_validator('section_identifier', mode='before')
    @classmethod
    def clean_section_id(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip().replace("Section ", "").replace("section ", "").upper()
        return str(v)

class SectionRule(BaseModel):
    section_identifier: str = Field(description="The section code letter (e.g., 'A', 'B').")
    max_questions_to_attempt: int = Field(default=999, description="Limit of choices allowed.")
    max_section_marks: float = Field(default=999.0, description="Maximum total marks allowed for this section.")

class FullGamifiedAssessment(BaseModel):
    student_id: Optional[str] = Field(default="Unknown Student", description="Extracted student name/ID.")
    max_paper_marks: float = Field(default=100.0, description="Total maximum grand marks possible.")
    total_score: float = Field(default=0.0, description="Calculated grand total score.")
    total_xp: float = Field(default=0.0, description="Sum of all game mechanic XP metrics.")
    level_up_unlocked: bool = Field(default=False, description="True if total_xp crosses 75% target milestone.")
    section_rules: List[SectionRule] = Field(default_factory=list, description="Extracted structural rules.")
    assessments: List[GamifiedEvaluation] = Field(default_factory=list, description="List of processed evaluations.")

    @model_validator(mode='after')
    def process_dynamic_sectional_boundaries(self) -> 'FullGamifiedAssessment':
        if not self.assessments:
            return self

        rule_map: Dict[str, SectionRule] = {r.section_identifier.upper(): r for r in self.section_rules}
        grouped_sections: Dict[str, List[GamifiedEvaluation]] = {}

        final_calculated_score = 0.0
        final_calculated_xp = 0.0
        max_possible_test_xp = 0.0

        for q in self.assessments:
            sec_id = q.section_identifier.upper()
            if sec_id not in grouped_sections:
                grouped_sections[sec_id] = []
            
            if q.marks_awarded > q.max_possible_marks:
                q.marks_awarded = q.max_possible_marks
            if q.marks_awarded < 0:
                q.marks_awarded = 0.0
            grouped_sections[sec_id].append(q)

        for sec_id, questions in grouped_sections.items():
            sorted_questions = sorted(questions, key=lambda x: x.marks_awarded, reverse=True)
            rule = rule_map.get(sec_id)
            max_allowed_attempts = rule.max_questions_to_attempt if rule else 999
            max_section_cap = rule.max_section_marks if rule else 999.0

            section_score_pool = 0.0
            
            for idx, q in enumerate(sorted_questions):
                if idx < max_allowed_attempts:
                    section_score_pool += q.marks_awarded
                    if q.max_possible_marks > 0:
                        performance_ratio = q.marks_awarded / q.max_possible_marks
                        q.gamification.xp_earned = round(performance_ratio * 10, 1)
                        q.gamification.is_buggy = q.marks_awarded < q.max_possible_marks
                    else:
                        q.gamification.xp_earned = 0.0
                        
                    final_calculated_xp += q.gamification.xp_earned
                    max_possible_test_xp += 10.0
                else:
                    q.gamification.xp_earned = 0.0
                    q.justification = f"[Optional Choice Exceeded] Omitted via Best-Answer Optimization. {q.justification}"

            if section_score_pool > max_section_cap:
                section_score_pool = max_section_cap
                
            final_calculated_score += section_score_pool

        self.total_score = round(final_calculated_score, 2)
        self.total_xp = round(final_calculated_xp, 1)
        self.level_up_unlocked = self.total_xp >= (max_possible_test_xp * 0.75) if max_possible_test_xp > 0 else False
        return self

# =====================================================================
# 2. DYNAMIC INTERMEDIATE SCHEMAS FOR EXTRACTION
# =====================================================================

class MasterQuestionItem(BaseModel):
    question_number: int = Field(description="The question number.")
    section_identifier: str = Field(description="The section block it belongs to.")
    max_marks: float = Field(description="Max marks assigned to this question.")
    expected_answer_rubric: str = Field(description="Core solution steps, definitions, or evaluation keywords.")

class DynamicMasterKeyMap(BaseModel):
    max_paper_marks: float = Field(default=100.0, description="Grand maximum marks printed on the paper.")
    section_rules: List[SectionRule] = Field(default_factory=list, description="Discovered exam sections and rules.")
    questions: List[MasterQuestionItem] = Field(default_factory=list, description="Complete list of questions and their solutions.")

class RawHandwrittenAnswer(BaseModel):
    sheet_question_label: str = Field(description="The handwritten label written by the student, e.g., 'Q.1', 'Ans 2'.")
    master_question_number: int = Field(description="The deduced corresponding master question number.")
    section_identifier: str = Field(description="The section block letter.")
    transcribed_student_text: str = Field(description="Word-for-word text/equations transcribed from this specific fragment.")

class RawSheetExtraction(BaseModel):
    student_name: str = Field(description="The student's full name/ID from the header.")
    written_assessments: List[RawHandwrittenAnswer] = Field(default_factory=list, description="Sequential extraction of all raw fragments.")

# Schema for the newly introduced text-only evaluation pipeline
class SingleQuestionGradingOutput(BaseModel):
    question_number: int
    grading_scratchpad: str = Field(description="Step-by-step evaluation against the ground-truth rubric.")
    marks_awarded: float = Field(description="Score assigned following the strict lenient fractional mandate.")
    justification: str = Field(description="Clear explanation of the awarded credit and deductions.")
    bug_description: str = Field(description="Description of omissions if marks were lost.")
    quest_directive: str = Field(description="Actionable improvement feedback step.")

class TextGradingBatchOutput(BaseModel):
    evaluations: List[SingleQuestionGradingOutput]

# =====================================================================
# 3. AUTONOMOUS GRADING ENGINE (DECOUPLED DESIGN)
# =====================================================================

class AutonomousGradingEngine:
    def __init__(self, api_key: str):
        self.vision_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0, api_key=api_key)
        self.key_extractor = self.vision_llm.with_structured_output(DynamicMasterKeyMap)
        self.sheet_extractor = self.vision_llm.with_structured_output(RawSheetExtraction)
        self.text_grader = self.vision_llm.with_structured_output(TextGradingBatchOutput)

    def evaluate_with_question_paper(self, paper_images_bytes: List[bytes], sheet_images_bytes: List[bytes]) -> FullGamifiedAssessment:
        
        # -----------------------------------------------------------------
        # STAGE 1: Extract Blueprint & Detailed Rubrics from Question Paper
        # -----------------------------------------------------------------
        key_payload_messages = []
        for p_bytes in paper_images_bytes:
            key_payload_messages.append({
                "type": "image_url", 
                "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(p_bytes).decode('utf-8')}"}
            })
            
        key_prompt = (
            "You are an academic evaluation compiler.\n"
            "Analyze the attached master question paper images and process these tasks with absolute precision:\n"
            "1. Extract 'max_paper_marks' from the instructions at the top.\n"
            "2. Identify all exam sections and create a 'SectionRule' object for each.\n"
            "3. Parse EVERY single question/sub-question. Populate its 'question_number', 'section_identifier', "
            "'max_marks', and write down a comprehensive 'expected_answer_rubric' containing the solution or required concepts."
        )
        key_payload_messages.insert(0, {"type": "text", "text": key_prompt})
        dynamic_master = self.key_extractor.invoke([("user", key_payload_messages)])

        # -----------------------------------------------------------------
        # STAGE 2: Pure Raw Text Transcription (No Grading on Fragments)
        # -----------------------------------------------------------------
        sheet_payload_messages = []
        for s_bytes in sheet_images_bytes:
            sheet_payload_messages.append({
                "type": "image_url", 
                "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(s_bytes).decode('utf-8')}"}
            })

        extraction_prompt = (
            "Analyze this completed student handwritten answer script page-by-page.\n"
            "Perform a PURE, objective transcription of the text and equations written by the student.\n"
            "For each distinct block of writing, capture the student's question label, map it back to the clean sequential "
            "master question number, and transcribe everything exactly as written. DO NOT perform any grading or mark allocation here."
        )
        sheet_payload_messages.insert(0, {"type": "text", "text": extraction_prompt})
        extracted_student_data = self.sheet_extractor.invoke([("user", sheet_payload_messages)])
        
        # -----------------------------------------------------------------
        # STAGE 3: Programmatic Stitching of Fragmented/Non-Linear Inputs
        # -----------------------------------------------------------------
        consolidated_map: Dict[int, Dict[str, Any]] = {}
        rubric_lookup = {q.question_number: q for q in dynamic_master.questions}

        for raw_block in extracted_student_data.written_assessments:
            q_num = raw_block.master_question_number
            if q_num not in consolidated_map:
                master_info = rubric_lookup.get(q_num)
                consolidated_map[q_num] = {
                    "question_number": q_num,
                    "section_identifier": raw_block.section_identifier.upper(),
                    "text_fragments": [raw_block.transcribed_student_text],
                    "master_key": master_info.expected_answer_rubric if master_info else "Rubric not captured.",
                    "max_possible_marks": master_info.max_marks if master_info else 1.0
                }
            else:
                consolidated_map[q_num]["text_fragments"].append(raw_block.transcribed_student_text)

        # -----------------------------------------------------------------
        # STAGE 4: Stitched, Decoupled Text-Only Rubric Evaluation
        # -----------------------------------------------------------------
        # Build a structured, text-only verification prompt containing all fully-formed answers
        grading_payload_data = []
        for q_num, data in consolidated_map.items():
            unified_text = " [CONTINUED ON NEXT PAGE]: ".join(data["text_fragments"])
            grading_payload_data.append({
                "question_number": q_num,
                "section": data["section_identifier"],
                "max_marks": data["max_possible_marks"],
                "master_rubric": data["master_key"],
                "student_answer": unified_text
            })

        grading_prompt = (
            f"You are an expert examiner grading complete, stitched student answers against a Master Rubric.\n"
            f"Review the provided JSON batch of student answers and evaluate them fairly.\n\n"
            f"CRITICAL MANDATE: ENFORCE LENIENT FRACTIONAL SCORING. Do not grade binary (0 or full marks).\n"
            f"- If the student explains the core concept correctly or understands the underlying meaning but misses technical keywords or formatting: Award 40% to 60% of the maximum marks.\n"
            f"- If the answer is incomplete, deduct partial marks incrementally (e.g., -0.5 or -1.0) rather than dumping it to a 0.\n"
            f"- Assign a 0 ONLY if the space is blank, completely incorrect, or completely irrelevant.\n\n"
            f"Input Data for Evaluation:\n{json.dumps(grading_payload_data, indent=2)}"
        )

        graded_batch = self.text_grader.invoke(grading_prompt)
        graded_lookup = {g.question_number: g for g in graded_batch.evaluations}

        # Assemble finalized array back into unified Pydantic schemas
        compiled_evaluations: List[GamifiedEvaluation] = []
        for q_num, data in consolidated_map.items():
            eval_result = graded_lookup.get(q_num)
            unified_input_text = " | CONTINUATION: ".join(data["text_fragments"])
            
            if eval_result:
                marks = eval_result.marks_awarded
                justification = eval_result.justification
                scratchpad = eval_result.grading_scratchpad
                bug_desc = eval_result.bug_description
                directive = eval_result.quest_directive
            else:
                # Fallback safeguard
                marks = 0.0
                justification = "Grading iteration missed."
                scratchpad = ""
                bug_desc = "Missing trace data."
                directive = "Re-evaluate."

            compiled_evaluations.append(
                GamifiedEvaluation(
                    question_number=q_num,
                    section_identifier=data["section_identifier"],
                    question_type="Theory",
                    grading_scratchpad=scratchpad,
                    extracted_student_input=unified_input_text,
                    master_key_answer=data["master_key"],
                    marks_awarded=marks,
                    max_possible_marks=data["max_possible_marks"],
                    justification=justification,
                    gamification=QuestMetrics(
                        is_buggy=(marks < data["max_possible_marks"]),
                        bug_description=bug_desc,
                        quest_directive=directive
                    )
                )
            )

        # -----------------------------------------------------------------
        # STAGE 5: Construct Verified Output Structure (Handles Section Caps)
        # -----------------------------------------------------------------
        return FullGamifiedAssessment(
            student_id=extracted_student_data.student_name,
            max_paper_marks=dynamic_master.max_paper_marks,
            section_rules=dynamic_master.section_rules,
            assessments=compiled_evaluations
        )
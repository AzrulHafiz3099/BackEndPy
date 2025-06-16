# db_question.py

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from database import get_connection

router = APIRouter(prefix="/api_question", tags=["Questions"])

@router.get("/test")
def test_question_route():
    return {"message": "Question router works"}

# Get questions by exam_id
@router.get("/questions")
def get_questions_by_exam(exam_id: str = Query(...)):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                q.Question_ID as question_id,
                q.Exam_ID as exam_id,
                q.Question_Text as question_text,
                q.Total_Marks as total_marks,
                COUNT(s.Scheme_ID) as total_scheme
            FROM question q
            LEFT JOIN scheme s ON q.Question_ID = s.Question_ID
            WHERE q.Exam_ID = %s
            GROUP BY q.Question_ID
        """, (exam_id,))
        questions = cursor.fetchall()
        return {"success": True, "data": questions}
    finally:
        cursor.close()
        conn.close()


# Create question
class QuestionCreate(BaseModel):
    exam_id: str
    question_text: str
    marks: float

@router.post("/add_questions")
def add_question(question: QuestionCreate):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT Question_ID FROM question ORDER BY Question_ID DESC LIMIT 1")
        last = cursor.fetchone()
        next_id = f"Q{(int(last['Question_ID'][1:]) + 1) if last else 1:03d}"

        cursor.execute("""
            INSERT INTO question (Question_ID, Exam_ID, Question_Text, Total_Marks)
            VALUES (%s, %s, %s, %s)
        """, (next_id, question.exam_id, question.question_text, question.marks))

        conn.commit()
        return {"success": True, "message": "Question added", "question_id": next_id}
    finally:
        cursor.close()
        conn.close()

# Update question
class QuestionUpdate(BaseModel):
    question_text: str
    total_marks: float

@router.put("/questions/{question_id}")
def update_question(question_id: str, question: QuestionUpdate):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE question SET Question_Text=%s, Total_Marks=%s WHERE Question_ID=%s",
            (question.question_text, question.total_marks, question_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Question not found")
        return {"success": True, "message": "Question updated"}
    finally:
        cursor.close()
        conn.close()

# Delete question
@router.delete("/questions/{question_id}")
def delete_question(question_id: str):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM question WHERE Question_ID=%s", (question_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Question not found")
        return {"success": True, "message": "Question deleted"}
    finally:
        cursor.close()
        conn.close()

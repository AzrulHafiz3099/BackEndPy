from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from database import get_connection

router = APIRouter(prefix="/api_exam", tags=["Exams"])

@router.get("/test")
def test_exam_route():
    return {"message": "Exam router works"}

@router.get("/exams")
def get_exams_by_class(class_id: str = Query(...)):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                e.Exam_ID as exam_id, 
                e.Class_ID as class_id, 
                e.Exam_Name as name,
                COUNT(q.Question_ID) as question_count
            FROM exam e
            LEFT JOIN question q ON e.Exam_ID = q.Exam_ID
            WHERE e.Class_ID = %s
            GROUP BY e.Exam_ID
        """, (class_id,))
        exams = cursor.fetchall()
        return {"success": True, "data": exams}
    finally:
        cursor.close()
        conn.close()


class ExamCreate(BaseModel):
    class_id: str
    name: str

@router.post("/exams")
def add_exam(exam: ExamCreate):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT Exam_ID FROM exam ORDER BY Exam_ID DESC LIMIT 1")
        last = cursor.fetchone()
        next_id = f"E{(int(last['Exam_ID'][1:]) + 1) if last else 1:03d}"

        cursor.execute("""
            INSERT INTO exam (Exam_ID, Class_ID, Exam_Name)
            VALUES (%s, %s, %s)
        """, (next_id, exam.class_id, exam.name))
        conn.commit()
        return {"success": True, "message": "Exam added", "exam_id": next_id}
    finally:
        cursor.close()
        conn.close()

class ExamUpdate(BaseModel):
    name: str

@router.put("/exams/{exam_id}")
def update_exam(exam_id: str, exam: ExamUpdate):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE exam SET Exam_Name=%s WHERE Exam_ID=%s", (exam.name, exam_id))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Exam not found")
        return {"success": True, "message": "Exam updated"}
    finally:
        cursor.close()
        conn.close()

@router.delete("/exams/{exam_id}")
def delete_exam(exam_id: str):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM exam WHERE Exam_ID=%s", (exam_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Exam not found")
        return {"success": True, "message": "Exam deleted"}
    finally:
        cursor.close()
        conn.close()
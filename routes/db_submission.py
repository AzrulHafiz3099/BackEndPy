# In routes/answer_submission.py (new or existing file)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from database import get_connection

router = APIRouter(prefix="/api_submission", tags=["Answer Submission"])

class Submission(BaseModel):
    student_id: str
    exam_id: str
    uploaded_folder: str

class ResultInput(BaseModel):
    submission_id: str
    score: str
    summary: str

@router.post("/submit")
def insert_submission(data: Submission):
    print(f"Received student_id: {data.student_id}")  # <-- Print the student_id here
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="DB connection failed")
    cursor = conn.cursor(dictionary=True)

    try:
        # Generate next Submission_ID in format SUB001, SUB002, ...
        cursor.execute("SELECT Submission_ID FROM answer_submission ORDER BY Submission_ID DESC LIMIT 1")
        last = cursor.fetchone()

        if last and last['Submission_ID'].startswith("SUB"):
            last_num = int(last['Submission_ID'][3:])
            next_id = f"SUB{last_num + 1:03d}"
        else:
            next_id = "SUB001"

        cursor.execute("""
            INSERT INTO answer_submission (Submission_ID, Student_ID, Exam_ID, Uploaded_Folder, Timestamp)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            next_id,
            data.student_id,
            data.exam_id,
            data.uploaded_folder,
            datetime.now()
        ))
        conn.commit()
        return {"success": True, "message": "Submission inserted", "submission_id": next_id}
    finally:
        cursor.close()
        conn.close()

@router.post("/confirm")
def insert_result(data: ResultInput):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="DB connection failed")
    cursor = conn.cursor(dictionary=True)

    try:
        # Generate next Result_ID: RS001, RS002, ...
        cursor.execute("SELECT Result_ID FROM result ORDER BY Result_ID DESC LIMIT 1")
        last = cursor.fetchone()
        if last and last["Result_ID"].startswith("RS"):
            last_num = int(last["Result_ID"][2:])
            next_id = f"RS{last_num + 1:03d}"
        else:
            next_id = "RS001"

        cursor.execute(
            """
            INSERT INTO result (Result_ID, Submission_ID, Score, Summary)
            VALUES (%s, %s, %s, %s)
            """,
            (next_id, data.submission_id, data.score, data.summary)
        )
        conn.commit()

        return {"success": True, "message": "Result inserted", "result_id": next_id}
    finally:
        cursor.close()
        conn.close()
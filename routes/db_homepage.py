from fastapi import APIRouter, HTTPException, Query
from database import get_connection

router = APIRouter(prefix="/api_homepage", tags=["Homepage"])

@router.get("/summary")
def get_homepage_summary(lecturer_id: str = Query(...)):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch lecturer name
        cursor.execute("SELECT Lecturer_Name FROM lecturer WHERE Lecturer_ID = %s", (lecturer_id,))
        lecturer = cursor.fetchone()
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer not found")

        # Count classes
        cursor.execute("SELECT COUNT(*) AS class_count FROM class WHERE Lecturer_ID = %s", (lecturer_id,))
        class_count = cursor.fetchone()["class_count"]

        # Count students
        cursor.execute("""
            SELECT COUNT(*) AS student_count
            FROM student s
            JOIN class c ON s.Class_ID = c.Class_ID
            WHERE c.Lecturer_ID = %s
        """, (lecturer_id,))
        student_count = cursor.fetchone()["student_count"]

        # Count exams
        cursor.execute("""
            SELECT COUNT(*) AS exam_count
            FROM exam e
            JOIN class c ON e.Class_ID = c.Class_ID
            WHERE c.Lecturer_ID = %s
        """, (lecturer_id,))
        exam_count = cursor.fetchone()["exam_count"]

        # Count results
        cursor.execute("""
            SELECT COUNT(*) AS result_count
            FROM result r
            JOIN answer_submission a ON r.Submission_ID = a.Submission_ID
            JOIN student s ON a.Student_ID = s.Student_ID
            JOIN class c ON s.Class_ID = c.Class_ID
            WHERE c.Lecturer_ID = %s
        """, (lecturer_id,))
        result_count = cursor.fetchone()["result_count"]

        return {
            "success": True,
            "data": {
                "lecturer_name": lecturer["Lecturer_Name"],
                "class_count": class_count,
                "student_count": student_count,
                "exam_count": exam_count,
                "result_count": result_count
            }
        }
    finally:
        cursor.close()
        conn.close()

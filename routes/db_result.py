from fastapi import APIRouter, HTTPException, Query
from database import get_connection

router = APIRouter(prefix="/api_result", tags=["Results"])

@router.get("/by_lecturer")
def get_results_by_lecturer(lecturer_id: str = Query(...)):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                r.Result_ID AS result_id,
                s.Student_ID AS student_id,
                s.Matrix_Number AS student_matrix,
                c.Class_Name AS class_name,
                a.Timestamp AS timestamp,
                r.Score AS score
            FROM result r
            JOIN answer_submission a ON r.Submission_ID = a.Submission_ID
            JOIN student s ON a.Student_ID = s.Student_ID
            JOIN class c ON s.Class_ID = c.Class_ID
            WHERE c.Lecturer_ID = %s
            ORDER BY CAST(SUBSTRING(r.Result_ID, 3) AS UNSIGNED) ASC
        """, (lecturer_id,))
        data = cursor.fetchall()
        return {"success": True, "data": data}
    finally:
        cursor.close()
        conn.close()

@router.get("/by_result")
def get_result_by_result_id(result_id: str = Query(...)):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                s.Matrix_Number AS matrix_number,
                c.Class_Name AS class_name,
                e.Exam_Name AS exam_name,
                s.Phone_Number AS phone_number,
                r.Score AS score,
                r.Summary AS summary,
                a.Timestamp AS timestamp
            FROM result r
            JOIN answer_submission a ON r.Submission_ID = a.Submission_ID
            JOIN student s ON a.Student_ID = s.Student_ID
            JOIN class c ON s.Class_ID = c.Class_ID
            JOIN exam e ON a.Exam_ID = e.Exam_ID
            WHERE r.Result_ID = %s
            LIMIT 1
        """, (result_id,))
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Result not found")
        return {"success": True, "data": result}
    finally:
        cursor.close()
        conn.close()


@router.get("/by_lecturer5")
def get_results_by_lecturer5(lecturer_id: str = Query(...)):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                r.Result_ID AS result_id,
                s.Student_ID AS student_id,
                s.Matrix_Number AS matrix_number,
                c.Class_Name AS class_name,
                a.Timestamp AS timestamp,
                r.Score AS score
            FROM result r
            JOIN answer_submission a ON r.Submission_ID = a.Submission_ID
            JOIN student s ON a.Student_ID = s.Student_ID
            JOIN class c ON s.Class_ID = c.Class_ID
            WHERE c.Lecturer_ID = %s
            ORDER BY a.Timestamp DESC
            LIMIT 5
        """, (lecturer_id,))
        data = cursor.fetchall()
        return {"success": True, "data": data}
    finally:
        cursor.close()
        conn.close()
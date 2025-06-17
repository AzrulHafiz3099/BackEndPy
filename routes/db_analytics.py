from fastapi import APIRouter, HTTPException, Query
from database import get_connection

router = APIRouter(prefix="/api_analytics", tags=["Analytics"])

@router.get("/completion")
def get_completion_stats(class_id: str = Query(...), exam_id: str = Query(...)):
    print(f"Received request with class_id: {class_id}, exam_id: {exam_id}")

    conn = get_connection()
    if not conn:
        print("❌ Database connection failed")
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Total students in class
        cursor.execute("SELECT COUNT(*) AS total FROM student WHERE Class_ID = %s", (class_id,))
        total_result = cursor.fetchone()
        print("🎓 Total students query result:", total_result)
        total_students = total_result['total'] if total_result else 0
        print("✅ Total students:", total_students)

        if total_students == 0:
            result = {
                "success": True,
                "data": {
                    "total_students": 0,
                    "students_completed": 0,
                    "completion_percentage": 0.0
                }
            }
            print("📊 Final result (no students):", result)
            return result

        # Students who submitted answers for the given exam
        cursor.execute("""
            SELECT COUNT(DISTINCT student_id) AS completed 
            FROM answer_submission 
            WHERE Exam_ID = %s AND Student_ID IN (
                SELECT Student_ID FROM student WHERE Class_ID = %s
            )
        """, (exam_id, class_id))
        completed_result = cursor.fetchone()
        print("📥 Completed submissions query result:", completed_result)
        students_completed = completed_result['completed'] if completed_result else 0
        print("✅ Students completed:", students_completed)

        completion_percentage = round(students_completed / total_students, 2)
        print("📈 Completion percentage:", completion_percentage)

        result = {
            "success": True,
            "data": {
                "total_students": total_students,
                "students_completed": students_completed,
                "completion_percentage": completion_percentage
            }
        }
        print("📦 Final response:", result)
        return result

    finally:
        cursor.close()
        conn.close()
        print("🔒 Database connection closed.")

@router.get("/score_distribution")
def get_score_distribution(class_id: str = Query(...), exam_id: str = Query(...)):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    # total marks
    cur.execute("SELECT SUM(Total_Marks) AS total_marks FROM question WHERE Exam_ID=%s", (exam_id,))
    total_marks = cur.fetchone()["total_marks"] or 0
    print(f"[DEBUG] Total Marks: {total_marks}")

    # number of students who took it
    cur.execute("""
        SELECT COUNT(DISTINCT a.Student_ID) AS taken
        FROM answer_submission a
        JOIN student s USING(Student_ID)
        WHERE a.Exam_ID=%s AND s.Class_ID=%s
    """, (exam_id, class_id))
    students_taken = cur.fetchone()["taken"] or 0
    print(f"[DEBUG] Students Taken: {students_taken}")

    # distribution of scores
    cur.execute("""
        SELECT r.Score AS score, COUNT(*) AS count FROM result r
        JOIN answer_submission a USING(Submission_ID)
        JOIN student s USING(Student_ID)
        WHERE a.Exam_ID=%s AND s.Class_ID=%s
        GROUP BY r.Score
        ORDER BY r.Score DESC
    """, (exam_id, class_id))
    dist = cur.fetchall()
    print(f"[DEBUG] Score Distribution: {dist}")

    cur.close()
    conn.close()

    return {
        "success": True,
        "data": {
            "total_marks": total_marks,
            "students_taken": students_taken,
            "distribution": dist
        }
    }

@router.get("/exam_summary")
def get_exam_summary(class_id: str, exam_id: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get class and exam name
        cursor.execute("""
            SELECT c.Class_Name, e.Exam_Name
            FROM class c
            JOIN exam e ON c.Class_ID = e.Class_ID
            WHERE c.Class_ID = %s AND e.Exam_ID = %s
        """, (class_id, exam_id))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Class or Exam not found")

        class_name = row['Class_Name']
        exam_name = row['Exam_Name']

        # Get student scores
        cursor.execute("""
            SELECT s.Matrix_Number, r.Score
            FROM student s
            JOIN answer_submission a ON s.Student_ID = a.Student_ID
            JOIN result r ON a.Submission_ID = r.Submission_ID
            WHERE s.Class_ID = %s AND a.Exam_ID = %s
        """, (class_id, exam_id))
        student_scores = cursor.fetchall()

        return {
            "class_name": class_name,
            "exam_name": exam_name,
            "students": student_scores
        }

    finally:
        cursor.close()
        conn.close()


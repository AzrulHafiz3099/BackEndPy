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

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel
from database import get_connection

router = APIRouter(prefix="/api_student", tags=["Students"])

@router.get("/students")
def get_students_by_class(class_id: str = Query(...)):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT Student_ID as student_id, Matrix_Number as matrix, Phone_Number as phone  
            FROM student WHERE Class_ID = %s
        """, (class_id,))
        students = cursor.fetchall()
        return {"success": True, "data": students}
    finally:
        cursor.close()
        conn.close()

class StudentCreate(BaseModel):
    class_id: str
    matrix: str
    phone: str

@router.post("/students")
def add_student(student: StudentCreate):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor(dictionary=True)
    try:
        # ✅ Check for duplicate matrix number in the same class
        cursor.execute("""
            SELECT Student_ID FROM student 
            WHERE Matrix_Number = %s AND Class_ID = %s
        """, (student.matrix, student.class_id))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Matrix number already exists in this class")

        # ✅ Check for duplicate phone number in the same class
        cursor.execute("""
            SELECT Student_ID FROM student 
            WHERE Phone_Number = %s AND Class_ID = %s
        """, (student.phone, student.class_id))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Phone number already exists in this class")

        # ✅ Generate new student ID
        cursor.execute("SELECT Student_ID FROM student ORDER BY Student_ID DESC LIMIT 1")
        last = cursor.fetchone()
        next_id = f"S{(int(last['Student_ID'][1:]) + 1) if last else 1:03d}"

        # ✅ Insert student with no name
        cursor.execute("""
            INSERT INTO student (Student_ID, Class_ID, Student_Name, Matrix_Number, Phone_Number)
            VALUES (%s, %s, '', %s, %s)
        """, (next_id, student.class_id, student.matrix, student.phone))
        conn.commit()

        return {"success": True, "message": "Student added", "student_id": next_id}
    finally:
        cursor.close()
        conn.close()


class StudentUpdate(BaseModel):
    class_id: str
    matrix: str
    phone: str

@router.put("/students/{student_id}")
def update_student(student_id: str, student: StudentUpdate):
    print("🔵 Received PUT request to /students/{student_id}")
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor()
    try:
        print(f"Updating student {student_id} with: class_id={student.class_id}, matrix={student.matrix}, phone={student.phone}")

        # ✅ Check for duplicate matrix number in the same class (excluding self)
        cursor.execute("""
            SELECT Student_ID FROM student 
            WHERE Matrix_Number = %s AND Class_ID = %s AND Student_ID != %s
        """, (student.matrix, student.class_id, student_id))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Matrix number already exists in this class")

        # ✅ Check for duplicate phone number in the same class (excluding self)
        cursor.execute("""
            SELECT Student_ID FROM student 
            WHERE Phone_Number = %s AND Class_ID = %s AND Student_ID != %s
        """, (student.phone, student.class_id, student_id))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Phone number already exists in this class")

        # ✅ Proceed with the update
        cursor.execute("""
            UPDATE student 
            SET Class_ID=%s, Matrix_Number=%s, Phone_Number=%s
            WHERE Student_ID=%s
        """, (student.class_id, student.matrix, student.phone, student_id))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Student not found")

        return {"success": True, "message": "Student updated"}
    finally:
        cursor.close()
        conn.close()

@router.delete("/students/{student_id}")
def delete_student(student_id: str):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM student WHERE Student_ID=%s", (student_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Student not found")
        return {"success": True, "message": "Student deleted"}
    finally:
        cursor.close()
        conn.close()

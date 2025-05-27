from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel
from database import get_connection

router = APIRouter(
    prefix="/api_class",
    tags=["Classes"]  # optional, useful if you use FastAPI docs UI
)

# fetch class by lecturer id
@router.get("/classes")
def get_classes_by_lecturer(lecturer_id: str = Query(..., max_length=10)):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT Class_ID as class_id, Lecturer_ID as lecturer_id, Class_Name as class_name, 
                   Class_Code as class_code, Session as session, Year as year 
            FROM class WHERE Lecturer_ID = %s
            """,
            (lecturer_id,)
        )
        classes = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"success": True, "data": classes}
    except Exception as e:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


class ClassCreateRequest(BaseModel):
    lecturer_id: str
    class_name: str
    class_code: str
    session: str
    year: str

# add class to lecturer id 

@router.post("/classes")
def add_class(request: ClassCreateRequest):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor(dictionary=True)
    try:
        # Step 1: Get last class_id (e.g. "C001")
        cursor.execute("SELECT Class_ID FROM class ORDER BY Class_ID DESC LIMIT 1")
        last_row = cursor.fetchone()
        
        if last_row and last_row["Class_ID"].startswith("C"):
            last_num = int(last_row["Class_ID"][1:])
            next_num = last_num + 1
        else:
            next_num = 1
        
        new_class_id = f"C{next_num:03d}"

        # Step 2: Insert the new class with generated class_id
        cursor.execute(
            """
            INSERT INTO class (Class_ID, Lecturer_ID, Class_Name, Class_Code, Session, Year)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                new_class_id,
                request.lecturer_id,
                request.class_name,
                request.class_code,
                request.session,
                request.year
            )
        )

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "success": True,
            "message": "Class added successfully",
            "class_id": new_class_id
        }

    except Exception as e:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
    
class ClassUpdateRequest(BaseModel):
    class_name: str
    class_code: str
    session: str
    year: str

@router.put("/classes/{class_id}")
def update_class(class_id: str = Path(..., max_length=10), request: ClassUpdateRequest = None):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE class SET Class_Name = %s, Class_Code = %s, Session = %s, Year = %s
            WHERE Class_ID = %s
            """,
            (
                request.class_name,
                request.class_code,
                request.session,
                request.year,
                class_id,
            )
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Class not found")
        cursor.close()
        conn.close()

        return {"success": True, "message": "Class updated successfully"}

    except Exception as e:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/classes/{class_id}")
def delete_class(class_id: str = Path(..., max_length=10)):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM class WHERE Class_ID = %s",
            (class_id,)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Class not found")
        cursor.close()
        conn.close()

        return {"success": True, "message": "Class deleted successfully"}

    except Exception as e:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
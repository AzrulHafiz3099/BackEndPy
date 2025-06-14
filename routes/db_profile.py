from fastapi import APIRouter, HTTPException, Query
from database import get_connection
from pydantic import BaseModel

router = APIRouter(prefix="/api_profile", tags=["Profiles"])

@router.get("/lecturer_info")
def get_lecturer_info(lecturer_id: str = Query(...)):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT Lecturer_Name AS name, Email AS email, Phone_Number AS phone, Institution_Name AS institution 
            FROM lecturer 
            WHERE Lecturer_ID = %s
        """, (lecturer_id,))
        lecturer = cursor.fetchone()
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer not found")
        return {"success": True, "data": lecturer}
    finally:
        cursor.close()
        conn.close()

class LecturerUpdateRequest(BaseModel):
    name: str
    email: str
    phone: str
    institution: str


@router.put("/update_lecturers/{lecturer_id}")
def update_lecturer_profile(lecturer_id: str, update_data: LecturerUpdateRequest):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor()
    try:
        # Check if lecturer exists
        cursor.execute("SELECT 1 FROM lecturer WHERE Lecturer_ID = %s", (lecturer_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Lecturer not found")

        # Update lecturer info
        cursor.execute("""
            UPDATE lecturer
            SET Lecturer_Name = %s,
                Email = %s,
                Phone_Number = %s,
                Institution_Name = %s
            WHERE Lecturer_ID = %s
        """, (
            update_data.name,
            update_data.email,
            update_data.phone,
            update_data.institution,
            lecturer_id
        ))
        conn.commit()

        return {"success": True, "message": "Lecturer profile updated successfully."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update lecturer profile: {e}")
    finally:
        cursor.close()
        conn.close()
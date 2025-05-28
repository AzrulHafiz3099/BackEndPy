# db_scheme.py

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from database import get_connection

router = APIRouter(prefix="/api_scheme", tags=["Schemes"])

# --- Models ---

class SchemeCreate(BaseModel):
    question_id: str
    scheme_text: str
    marks: int

class SchemeUpdate(BaseModel):
    scheme_text: Optional[str] = None
    marks: Optional[int] = None

# --- Routes ---

# Get all schemes for a specific question
@router.get("/schemes")
def get_schemes_by_question(question_id: str = Query(...)):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                Scheme_ID as scheme_id,
                Question_ID as question_id,
                Scheme_Text as scheme_text,
                Marks as marks
            FROM scheme
            WHERE Question_ID = %s
        """, (question_id,))
        return {"success": True, "data": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()

# Create a new scheme
@router.post("/schemes")
def add_scheme(scheme: SchemeCreate):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT Scheme_ID FROM scheme ORDER BY Scheme_ID DESC LIMIT 1")
        last = cursor.fetchone()

        if last:
            # Remove the two-letter prefix 'SC' from Scheme_ID
            last_num = int(last['Scheme_ID'][2:])
            next_id = f"SC{last_num + 1:03d}"
        else:
            next_id = "SC001"

        cursor.execute("""
            INSERT INTO scheme (Scheme_ID, Question_ID, Scheme_Text, Marks)
            VALUES (%s, %s, %s, %s)
        """, (next_id, scheme.question_id, scheme.scheme_text, scheme.marks))
        conn.commit()
        return {"success": True, "message": "Scheme added", "scheme_id": next_id}
    finally:
        cursor.close()
        conn.close()


# Update a scheme by ID
@router.put("/schemes/{scheme_id}")
def update_scheme(scheme_id: str, scheme: SchemeUpdate):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor()
    try:
        update_fields = []
        values = []

        if scheme.scheme_text is not None:
            update_fields.append("Scheme_Text = %s")
            values.append(scheme.scheme_text)
        if scheme.marks is not None:
            update_fields.append("Marks = %s")
            values.append(scheme.marks)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        values.append(scheme_id)

        cursor.execute(f"""
            UPDATE scheme
            SET {', '.join(update_fields)}
            WHERE Scheme_ID = %s
        """, tuple(values))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Scheme not found")

        return {"success": True, "message": "Scheme updated"}
    finally:
        cursor.close()
        conn.close()

# Delete a scheme by ID
@router.delete("/schemes/{scheme_id}")
def delete_scheme(scheme_id: str):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM scheme WHERE Scheme_ID = %s", (scheme_id,))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Scheme not found")

        return {"success": True, "message": "Scheme deleted"}
    finally:
        cursor.close()
        conn.close()

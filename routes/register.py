from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field
from database import get_connection
from passlib.context import CryptContext

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class RegisterRequest(BaseModel):
    full_name: str = Field(alias="Lecturer_Name")
    email: EmailStr = Field(alias="Email")
    password: str = Field(alias="Password")
    phone: str = Field(alias="Phone_Number")
    institution: str = Field(alias="Institution_Name")

    class Config:
        allow_population_by_field_name = True  # Allow usage of both aliases and field names

@router.post("/register")
def register(data: RegisterRequest):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor(dictionary=True)

    # Check if email exists
    cursor.execute("SELECT * FROM lecturer WHERE email = %s", (data.email,))
    email_exists = cursor.fetchone()

    # Check if phone exists
    cursor.execute("SELECT * FROM lecturer WHERE phone_number = %s", (data.phone,))
    phone_exists = cursor.fetchone()

    cursor.close()
    conn.close()

    # Respond with custom messages if any already exist
    if email_exists and phone_exists:
        raise HTTPException(status_code=409, detail="Email and Phone number already registered")
    elif email_exists:
        raise HTTPException(status_code=409, detail="Email already registered")
    elif phone_exists:
        raise HTTPException(status_code=409, detail="Phone number already registered")

    # Proceed to insert if both are unique (reconnect again)
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Generate new lecturer_id
    cursor.execute("SELECT lecturer_id FROM lecturer ORDER BY lecturer_id DESC LIMIT 1")
    last = cursor.fetchone()
    new_id = f"L{(int(last['lecturer_id'][1:]) + 1) if last else 1:03}"

    hashed_password = pwd_context.hash(data.password)

    try:
        cursor.execute("""
            INSERT INTO lecturer (lecturer_id, lecturer_name, email, password, phone_number, institution_name)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (new_id, data.full_name, data.email, hashed_password, data.phone, data.institution))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Registration failed: {e}")
    finally:
        cursor.close()
        conn.close()

    return {"success": True, "message": "Registration successful", "lecturer_id": new_id}

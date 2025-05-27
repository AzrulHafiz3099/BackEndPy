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
    print("Received data:", data.dict(by_alias=True)) 
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor(dictionary=True)

    # Check if email already exists
    cursor.execute("SELECT * FROM lecturer WHERE email = %s", (data.email,))
    existing_user = cursor.fetchone()
    if existing_user:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=409, detail="Email already registered")

    # Generate next lecturer_id (assuming format L001, L002, etc.)
    cursor.execute("SELECT lecturer_id FROM lecturer ORDER BY lecturer_id DESC LIMIT 1")
    last_lecturer = cursor.fetchone()
    if last_lecturer and 'lecturer_id' in last_lecturer:
        last_id_num = int(last_lecturer['lecturer_id'][1:])  # skip 'L'
        next_id_num = last_id_num + 1
    else:
        next_id_num = 1

    new_lecturer_id = f"L{next_id_num:03d}"

    # Hash the password
    hashed_password = pwd_context.hash(data.password)

    # Insert new user
    sql_insert = """
        INSERT INTO lecturer (lecturer_id, lecturer_name, email, password, phone_number, institution_name)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    try:
        cursor.execute(sql_insert, (
            new_lecturer_id,
            data.full_name,
            data.email,
            hashed_password,
            data.phone,
            data.institution
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        raise HTTPException(status_code=500, detail=f"Failed to register user: {str(e)}")

    cursor.close()
    conn.close()

    return {"success": True, "message": "User registered successfully", "lecturer_id": new_lecturer_id}

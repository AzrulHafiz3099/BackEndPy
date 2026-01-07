# routes/auth.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_connection
import bcrypt

router = APIRouter()

class LoginRequest(BaseModel):
    emailOrId: str
    password: str

@router.post("/login")
def login(login: LoginRequest):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor(dictionary=True)
    sql = """
        SELECT lecturer_id, email, phone_number, password FROM lecturer 
        WHERE email = %s OR phone_number = %s LIMIT 1
    """
    cursor.execute(sql, (login.emailOrId, login.emailOrId))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        return {"success": False, "message": "Invalid email or phone number or password"}

    # Truncate password to 72 bytes and verify with bcrypt
    password_bytes = login.password.encode('utf-8')[:72]
    stored_hash = user["password"].encode('utf-8')
    
    if bcrypt.checkpw(password_bytes, stored_hash):
        return {
            "success": True,
            "message": "Login successful",
            "lecturer_id": user["lecturer_id"]
        }
    else:
        return {"success": False, "message": "Invalid email or phone number or password"}
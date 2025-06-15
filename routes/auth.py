# routes/auth.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_connection
from passlib.context import CryptContext

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

    if pwd_context.verify(login.password, user["password"]):
        return {
            "success": True,
            "message": "Login successful",
            "lecturer_id": user["lecturer_id"]
        }
    else:
        return {"success": False, "message": "Invalid email or phone number or password"}


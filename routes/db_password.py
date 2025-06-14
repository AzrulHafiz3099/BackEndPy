from fastapi import APIRouter, HTTPException
from database import get_connection

router = APIRouter(prefix="/api_password", tags=["Authentication"])

@router.get("/check_user")
def check_user(email: str = None, phone: str = None):
    if not email and not phone:
        raise HTTPException(status_code=400, detail="Email or phone must be provided")

    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor(dictionary=True)
    try:
        if email:
            cursor.execute("SELECT * FROM lecturer WHERE Email = %s", (email,))
        elif phone:
            cursor.execute("SELECT * FROM lecturer WHERE Phone_Number = %s", (phone,))
        
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"success": True}
    finally:
        cursor.close()
        conn.close()

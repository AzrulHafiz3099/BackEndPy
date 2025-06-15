from fastapi import APIRouter, HTTPException
from database import get_connection
import random
import requests
from fastapi import Request
from secretkey import ULTRAMSG_INSTANCE_ID, ULTRAMSG_TOKEN, EMAIL_SENDER, EMAIL_APP_PASSWORD
import time
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from passlib.context import CryptContext
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


router = APIRouter(prefix="/api_password", tags=["Authentication"])

otp_store = {}  # phone -> otp
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=10  # default is 12, lowering to 10 makes it ~2x faster
)

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

@router.post("/send_otp")
def send_otp(request: Request, phone: str):
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")

    otp = str(random.randint(1000, 9999))
    formatted_phone = f"+60{phone.lstrip('0')}"
    message = f"Your Grading Bot verification code is: {otp}"

    # Send OTP to WhatsApp
    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE_ID}/messages/chat"
    payload = {
        "token": ULTRAMSG_TOKEN,
        "to": formatted_phone,
        "body": message,
    }

    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()

        # Store with expiration time (60 seconds)
        otp_store[phone] = {
            "otp": otp,
            "expires_at": time.time() + 60
        }

        return {"success": True}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to send WhatsApp message: {e}")
    
class EmailRequest(BaseModel):
    email: str

@router.post("/send_otp_email")
def send_otp_email(payload: EmailRequest):
    email = payload.email
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    otp = str(random.randint(1000, 9999))
    message = f"Your Grading Bot verification code is: {otp}"

    try:
        # Email setup (same as before)
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = email
        msg['Subject'] = "Your OTP Code"
        msg.attach(MIMEText(message, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()

        otp_store[email] = {
            "otp": otp,
            "expires_at": time.time() + 60
        }

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {e}")


class OTPVerificationRequest(BaseModel):
    phone: str | None = None
    email: str | None = None
    otp: str

@router.post("/verify_otp")
def verify_otp(payload: OTPVerificationRequest):
    key = payload.phone or payload.email
    if not key:
        raise HTTPException(status_code=400, detail="Phone or email required")

    otp_entry = otp_store.get(key)
    if not otp_entry:
        raise HTTPException(status_code=404, detail="OTP not found")

    if time.time() > otp_entry["expires_at"]:
        del otp_store[key]
        raise HTTPException(status_code=410, detail="OTP expired")

    if otp_entry["otp"] != payload.otp:
        raise HTTPException(status_code=401, detail="Invalid OTP")

    del otp_store[key]
    return {"success": True, "message": "OTP verified"}


class ResetPasswordRequest(BaseModel):
    phone: str | None = None
    email: str | None = None
    new_password: str = Field(..., min_length=8)

@router.post("/reset_password")
def reset_password(data: ResetPasswordRequest):
    print("🔐 Reset request for:", data.phone or data.email)
    if not data.phone and not data.email:
        raise HTTPException(status_code=400, detail="Phone or email is required")

    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor()
    try:
        # Determine lookup field
        if data.phone:
            cursor.execute("SELECT * FROM lecturer WHERE phone_number = %s", (data.phone,))
        else:
            cursor.execute("SELECT * FROM lecturer WHERE email = %s", (data.email,))
        
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Lecturer not found")

        # Hash password
        hashed_password = pwd_context.hash(data.new_password)

        # Update password
        if data.phone:
            cursor.execute("UPDATE lecturer SET password = %s WHERE phone_number = %s", (hashed_password, data.phone))
        else:
            cursor.execute("UPDATE lecturer SET password = %s WHERE email = %s", (hashed_password, data.email))

        conn.commit()
        return {"success": True, "message": "Password updated successfully"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reset password: {e}")
    finally:
        cursor.close()
        conn.close()

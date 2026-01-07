from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from database import get_connection
from typing import List, Dict
from google.cloud import vision
import io
import os
from fuzzywuzzy import fuzz
import json
import re
from pdf2image import convert_from_bytes

router = APIRouter(prefix="/api_exam", tags=["Exams"])

@router.get("/test")
def test_exam_route():
    return {"message": "Exam router works"}

@router.get("/exams")
def get_exams_by_class(class_id: str = Query(...)):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                e.Exam_ID as exam_id, 
                e.Class_ID as class_id, 
                e.Exam_Name as name,
                COUNT(q.Question_ID) as question_count
            FROM exam e
            LEFT JOIN question q ON e.Exam_ID = q.Exam_ID
            WHERE e.Class_ID = %s
            GROUP BY e.Exam_ID
        """, (class_id,))
        exams = cursor.fetchall()
        return {"success": True, "data": exams}
    finally:
        cursor.close()
        conn.close()


class ExamCreate(BaseModel):
    class_id: str
    name: str

@router.post("/exams")
def add_exam(exam: ExamCreate):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT Exam_ID FROM exam ORDER BY Exam_ID DESC LIMIT 1")
        last = cursor.fetchone()
        next_id = f"E{(int(last['Exam_ID'][1:]) + 1) if last else 1:03d}"

        cursor.execute("""
            INSERT INTO exam (Exam_ID, Class_ID, Exam_Name)
            VALUES (%s, %s, %s)
        """, (next_id, exam.class_id, exam.name))
        conn.commit()
        return {"success": True, "message": "Exam added", "exam_id": next_id}
    finally:
        cursor.close()
        conn.close()

class ExamUpdate(BaseModel):
    name: str

@router.put("/exams/{exam_id}")
def update_exam(exam_id: str, exam: ExamUpdate):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE exam SET Exam_Name=%s WHERE Exam_ID=%s", (exam.name, exam_id))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Exam not found")
        return {"success": True, "message": "Exam updated"}
    finally:
        cursor.close()
        conn.close()

@router.delete("/exams/{exam_id}")
def delete_exam(exam_id: str):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM exam WHERE Exam_ID=%s", (exam_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Exam not found")
        return {"success": True, "message": "Exam deleted"}
    finally:
        cursor.close()
        conn.close()

@router.post("/exams_file_preview")
async def preview_exam_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        print(f"Received file: {file.filename}, size={len(content)} bytes")

        client = vision.ImageAnnotatorClient()
        extracted_text = ""

        # ---------- OCR ----------
        if file.filename.lower().endswith(".pdf"):
            print("PDF detected, converting to images...")
            images = convert_from_bytes(content)
            for i, img in enumerate(images, start=1):
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                image = vision.Image(content=img_byte_arr.getvalue())
                response = client.document_text_detection(image=image)
                page_text = response.full_text_annotation.text if response.full_text_annotation else ""
                print(f"Page {i} OCR text length: {len(page_text)}")
                extracted_text += page_text + "\n"
        else:
            print("Image detected, sending directly to Vision API...")
            image = vision.Image(content=content)
            response = client.document_text_detection(image=image)
            extracted_text = response.full_text_annotation.text if response.full_text_annotation else ""

        # ---------- Cleanup ----------
        lines = [l.strip() for l in extracted_text.split("\n") if l.strip()]
        cleaned_text = "\n".join(lines)
        print("----- Cleaned OCR Text -----")
        print(cleaned_text)
        print("----------------------------")

        # ---------- Regex to parse questions & schemes ----------
        question_pattern = re.compile(
            r'<Question\s*(\d+)\s*marks\s*=\s*"?(.*?)"?>(.*?)</Question\s*\1>',
            re.DOTALL | re.IGNORECASE
        )
        scheme_pattern = re.compile(
            r'<Scheme\s*(\d+)\s*marks\s*=\s*"?(.*?)"?>(.*?)</Scheme\s*\1>',
            re.DOTALL | re.IGNORECASE
        )

        questions_matches = question_pattern.findall(cleaned_text)
        print(f"Found {len(questions_matches)} question(s)")

        parsed = []
        for idx, (q_no, q_marks, q_text) in enumerate(questions_matches, start=1):
            q_text_clean = q_text.strip()
            print(f"\nQuestion {q_no}: {q_text_clean[:50]}... Marks: {q_marks}")

            # Get question block
            q_start_regex = re.compile(
                rf'<Question\s*{q_no}\s*marks\s*=\s*"?{q_marks}"?>',
                re.IGNORECASE
            )
            q_start_match = q_start_regex.search(cleaned_text)
            q_start = q_start_match.start() if q_start_match else 0

            if idx < len(questions_matches):
                next_q_no, next_q_marks, _ = questions_matches[idx]
                q_end_regex = re.compile(
                    rf'<Question\s*{next_q_no}\s*marks\s*=\s*"?{next_q_marks}"?>',
                    re.IGNORECASE
                )
                q_end_match = q_end_regex.search(cleaned_text)
                q_end = q_end_match.start() if q_end_match else len(cleaned_text)
            else:
                q_end = len(cleaned_text)

            q_block = cleaned_text[q_start:q_end]

            # Extract schemes
            schemes_for_q = []
            for s_no, s_marks, s_text in scheme_pattern.findall(q_block):
                scheme_text_clean = s_text.strip()
                print(f"  Found scheme {s_no}: {scheme_text_clean[:50]}... Marks: {s_marks}")
                schemes_for_q.append({
                    "scheme_no": int(s_no),
                    "scheme_text": scheme_text_clean,
                    "marks": int(s_marks)
                })

            parsed.append({
                "question_no": int(q_no),
                "question_text": q_text_clean,
                "marks": int(q_marks),
                "schemes": schemes_for_q
            })

        print("\n----- Parsed Structure -----")
        print(parsed)
        print("-----------------------------")

        return {"success": True, "raw_text": cleaned_text, "parsed": parsed}

    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ---------------- Create Exam with Parsed File ----------------
@router.post("/exams_with_file")
async def create_exam_with_file(
    class_id: str = Form(...),
    name: str = Form(...),
    parsed_data: str = Form(...)
):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        parsed = json.loads(parsed_data)  # parsed_data from preview

        # ---------- 1. Create Exam ----------
        cursor.execute("SELECT Exam_ID FROM exam ORDER BY Exam_ID DESC LIMIT 1")
        last = cursor.fetchone()
        next_exam_id = f"E{(int(last['Exam_ID'][1:]) + 1) if last else 1:03d}"

        cursor.execute(
            "INSERT INTO exam (Exam_ID, Class_ID, Exam_Name) VALUES (%s, %s, %s)",
            (next_exam_id, class_id, name)
        )

        # ---------- 2. Insert Questions & Schemes ----------
        for q in parsed:
            # Generate new Question_ID
            cursor.execute("SELECT Question_ID FROM question ORDER BY Question_ID DESC LIMIT 1")
            last_q = cursor.fetchone()
            next_q_id = f"Q{(int(last_q['Question_ID'][1:]) + 1) if last_q else 1:03d}"

            # Insert question with correct Total_Marks
            cursor.execute(
                "INSERT INTO question (Question_ID, Exam_ID, Question_Text, Total_Marks) VALUES (%s, %s, %s, %s)",
                (next_q_id, next_exam_id, q["question_text"], q.get("marks", 0))
            )

            # Insert each scheme with correct marks
            for scheme in q.get("schemes", []):
                cursor.execute("SELECT Scheme_ID FROM scheme ORDER BY Scheme_ID DESC LIMIT 1")
                last_s = cursor.fetchone()
                next_s_id = f"SC{(int(last_s['Scheme_ID'][2:]) + 1) if last_s else 1:03d}"

                cursor.execute(
                    "INSERT INTO scheme (Scheme_ID, Question_ID, Scheme_Text, Marks) VALUES (%s, %s, %s, %s)",
                    (next_s_id, next_q_id, scheme["scheme_text"], scheme.get("marks", 0))
                )

        conn.commit()
        return {"success": True, "exam_id": next_exam_id}

    except Exception as e:
        conn.rollback()
        print(f"ERROR inserting exam: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

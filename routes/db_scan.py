from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from typing import List, Dict
from database import get_connection
from google.cloud import vision
import io
import os
from fuzzywuzzy import fuzz
import json

router = APIRouter(prefix="/api_scan", tags=["Scan"])

@router.get("/questions_schemes")
def get_questions_and_schemes(exam_id: str = Query(...)):
    """
    Returns all questions and schemes for a given exam_id.
    Format:
    [
        {
            "question_id": str,
            "question_text": str,
            "total_marks": double,
            "schemes": [
                {
                    "scheme_id": str,
                    "scheme_text": str,
                    "marks": double
                },
                ...
            ]
        },
        ...
    ]
    """
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="DB connection failed")
    cursor = conn.cursor(dictionary=True)
    try:
        # Get all questions for the exam
        cursor.execute("""
            SELECT Question_ID, Question_Text, Total_Marks
            FROM question
            WHERE Exam_ID = %s
            ORDER BY Question_ID ASC
        """, (exam_id,))
        questions = cursor.fetchall()
        
        if not questions:
            return {"success": True, "data": []}

        # For each question, get its schemes
        result = []
        for q in questions:
            cursor.execute("""
                SELECT Scheme_ID, Scheme_Text, Marks
                FROM scheme
                WHERE Question_ID = %s
                ORDER BY Scheme_ID ASC
            """, (q['Question_ID'],))
            schemes = cursor.fetchall()
            result.append({
                "question_id": q['Question_ID'],
                "question_text": q['Question_Text'],
                "total_marks": q['Total_Marks'],
                "schemes": schemes
            })

        return {"success": True, "data": result}
    finally:
        cursor.close()
        conn.close()

# Dynamically resolve the absolute path to gradingbot_service.json
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVICE_KEY_PATH = os.path.join(BASE_DIR, "gradingbot_service.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = SERVICE_KEY_PATH

@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    schemes_json: str = Form(...)
):
    """
    Receives an image and selected schemes (JSON). 
    Extracts text, matches using fuzzy, and returns scoring results.
    """
    try:
        # Step 1: Extract text from image
        contents = await file.read()
        print(f"[DEBUG] Received file size: {len(contents)} bytes")

        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=contents)
        response = client.document_text_detection(image=image)

        extracted_text = response.full_text_annotation.text.lower().strip()
        print("----- Extracted Text -----")
        print(extracted_text)
        print("--------------------------")

        # Step 2: Parse schemes JSON string into Python list
        print(f"[DEBUG] Raw schemes_json string: {schemes_json}")
        selected_schemes = json.loads(schemes_json)
        print(f"[DEBUG] Parsed selected schemes (count={len(selected_schemes)}):")
        for idx, scheme in enumerate(selected_schemes, 1):
            print(f"  Scheme #{idx}: {scheme}")

        results = []
        total_marks = 0
        total_possible_marks = sum(scheme.get("marks", 0) for scheme in selected_schemes)

        # Step 3: Fuzzy match and assign marks
        lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]

        for scheme in selected_schemes:
            scheme_id = scheme.get("scheme_id")
            scheme_text = scheme.get("scheme_text", "").lower().strip()
            scheme_marks = scheme.get("marks", 0)

            matched = False
            highest_similarity = 0

            for line in lines:
                sim = fuzz.token_set_ratio(scheme_text, line)
                if sim > highest_similarity:
                    highest_similarity = sim
                if sim >= 80:  # Threshold can be adjusted
                    matched = True
                    break

            mark_awarded = scheme_marks if matched else 0
            total_marks += mark_awarded

            print(f"[DEBUG] Scheme ID: {scheme_id}")
            print(f"        Scheme Text: {scheme_text}")
            print(f"        Expected Marks: {scheme_marks}")
            print(f"        Highest Similarity: {highest_similarity}")
            print(f"        Matched: {matched}")
            print(f"        Marks Awarded: {mark_awarded}")
            print("----------------------------")

            results.append({
                "scheme_id": scheme_id,
                "scheme_text": scheme_text,
                "expected_marks": scheme_marks,
                "awarded_marks": mark_awarded,
                "similarity": highest_similarity
            })

        print(f"[DEBUG] Total Marks Awarded: {total_marks}")

        return {
            "success": True,
            "results": results,
            "total_awarded_marks": total_marks,
            "total_possible_marks": total_possible_marks
        }

    except Exception as e:
        print("OCR error:", str(e))
        raise HTTPException(status_code=500, detail="OCR processing failed")

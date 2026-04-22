import os
import json
import google.generativeai as genai
from pdf2image import convert_from_bytes
from PIL import Image
from io import BytesIO
from app.models.schemas import StatementSchema

# Setup Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Use flash for speed, multi-modal support, and JSON structure
MODEL_NAME = "gemini-1.5-flash"

EXTRACTION_PROMPT = """
You are a highly capable financial data extraction assistant.
Your task is to extract information from the provided bank statement image(s) and return it EXACTLY in the requested JSON structure.

Analyze the layout, tables, and text to accurately extract the following fields. Do not invent data; if a field is missing, leave it as an empty string (or 0 for numbers).

Ensure the output is a raw JSON object matching this schema:
{
  "bank_name": "string",
  "account_number": "string",
  "account_holder": "string",
  "statement_period": "string",
  "opening_balance": float (0 if missing),
  "closing_balance": float (0 if missing),
  "transactions": [
    {
      "date": "string (e.g., YYYY-MM-DD or as written)",
      "description": "string",
      "debit": float (0 if none),
      "credit": float (0 if none),
      "balance": float (0 if missing)
    }
  ]
}

IMPORTANT: Return ONLY the JSON object. Do not include markdown formatting like ```json or any other text.
"""

def process_document(file_bytes: bytes, filename: str) -> StatementSchema:
    """Processes a PDF or Image, calls Gemini, and returns structured data."""
    images = []

    # Handle PDF to Image conversion
    if filename.lower().endswith('.pdf'):
        # Convert PDF bytes to a list of PIL Images
        pdf_images = convert_from_bytes(file_bytes)
        images.extend(pdf_images)
    else:
        # Handle regular images (png, jpg)
        img = Image.open(BytesIO(file_bytes))
        images.append(img)

    if not images:
        raise ValueError("Could not process the document into images.")

    return call_gemini_extraction(images)


def call_gemini_extraction(images: list) -> StatementSchema:
    """Calls Gemini API with images and parses the JSON response."""

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set.")

    model = genai.GenerativeModel(MODEL_NAME)

    # Prepare the prompt payload (prompt + all images)
    prompt_parts = [EXTRACTION_PROMPT] + images

    response = model.generate_content(prompt_parts)

    try:
        # Clean the response in case it has markdown
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        parsed_data = json.loads(text)
        # Validate against schema
        return StatementSchema(**parsed_data)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON from Gemini response: {response.text}")
        raise ValueError("Gemini did not return valid JSON.") from e
    except Exception as e:
        print(f"Validation or extraction error: {str(e)}")
        raise e

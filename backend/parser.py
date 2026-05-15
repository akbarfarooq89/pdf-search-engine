import os
import sys
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

# Allow processing of very large images (high-res brochures)
Image.MAX_IMAGE_PIXELS = None

# Add the current directory to sys.path to allow imports when deployed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure Tesseract path for Windows (default installation path)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def categorize_document(rel_path, title):
    parts = rel_path.split('/')
    if len(parts) > 1:
        university = parts[0]
    else:
        university = "Uncategorized"
        
    text_to_check = f"{rel_path} {title}".lower()
    doc_type = "Other"
    
    if "fact sheet" in text_to_check:
        doc_type = "Fact Sheet"
    elif "fee" in text_to_check or "tuition" in text_to_check:
        doc_type = "Fee Structure"
    elif "application" in text_to_check or "form" in text_to_check:
        doc_type = "Application Form"
    elif "program" in text_to_check or "guide" in text_to_check or "course" in text_to_check:
        doc_type = "Program Guide"
    elif "brochure" in text_to_check:
        doc_type = "Brochure"
        
    return university, doc_type

def extract_text_from_file(filepath):
    text = ""
    try:
        if filepath.lower().endswith(('.png', '.jpg', '.jpeg')):
            print("  -> Image file detected, running direct OCR...")
            img = Image.open(filepath)
            text = pytesseract.image_to_string(img)
            return text
            
        doc = fitz.open(filepath)
        for page in doc:
            try:
                page_text = page.get_text()
                
                # If the page has almost no text, it might be a scanned image flyer
                if len(page_text.strip()) < 50:
                    print(f"  -> Page {page.number} has little text, running OCR...")
                    pix = page.get_pixmap(dpi=200, alpha=False) 
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    
                    ocr_text = pytesseract.image_to_string(img)
                    page_text += "\n" + ocr_text
                    
                text += page_text + "\n"
            except Exception as page_err:
                print(f"  [WARNING] Skipping page {page.number} due to error: {page_err}")
                continue
        return text
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return ""

if __name__ == "__main__":
    print("This file is now a utility library for text extraction.")

import os
import sys

# Add the current directory to sys.path to allow imports when deployed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from database import supabase, init_db

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Allow Iframes (Important for WordPress embedding)
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "ALLOWALL"
    response.headers["Content-Security-Policy"] = "frame-ancestors *"
    return response

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Ensure DB is initialized (Compatibility)
init_db()

@app.get("/api/search")
def search_documents(q: str = "", university: str = "", doc_type: str = ""):
    query = supabase.table("documents").select("id, filename, title, university, doc_type, content, gdrive_link")
    
    if university:
        query = query.eq("university", university)
    if doc_type:
        query = query.eq("doc_type", doc_type)
    
    # Simple search in content/title/university
    if q:
        search_term = f"%{q}%"
        query = query.or_(f"content.ilike.{search_term},title.ilike.{search_term},university.ilike.{search_term}")

    res = query.limit(50).execute()
    
    # Process snippets manually (Supabase doesn't have substr in simple client)
    results = []
    for row in res.data:
        snippet = row.get("content", "")[:300] + "..."
        results.append({
            "id": row["id"],
            "filename": row["filename"],
            "title": row["title"],
            "university": row["university"],
            "doc_type": row["doc_type"],
            "gdrive_link": row["gdrive_link"],
            "snippet": snippet
        })
        
    return results

@app.get("/api/metadata")
def get_metadata():
    # Get universities and doc types from Supabase
    univ_res = supabase.table("documents").select("university").execute()
    universities = sorted(list(set(row["university"] for row in univ_res.data if row["university"])))
    
    type_res = supabase.table("documents").select("doc_type").execute()
    doc_types = sorted(list(set(row["doc_type"] for row in type_res.data if row["doc_type"])))
    
    return {"universities": universities, "doc_types": doc_types}

@app.get("/api/courses/{university}")
def get_courses(university: str):
    res = supabase.table("documents").select("id, filename, title, content, gdrive_link")\
        .eq("university", university)\
        .or_("doc_type.eq.Brochure,doc_type.eq.Program Guide")\
        .order("title").execute()
        
    courses = []
    for row in res.data:
        courses.append({
            "id": row["id"],
            "filename": row["filename"],
            "title": row["title"],
            "gdrive_link": row["gdrive_link"],
            "snippet": row.get("content", "")[:300] + "..."
        })
    return courses

@app.get("/api/fees/{university}")
def get_fees(university: str):
    res = supabase.table("documents").select("id, filename, title, gdrive_link")\
        .eq("university", university)\
        .eq("doc_type", "Fee Structure")\
        .order("title").execute()
    return res.data

@app.get("/pdfs/{filename:path}")
def serve_pdf(filename: str):
    # In the cloud version, we redirect to Google Drive
    res = supabase.table("documents").select("gdrive_link").eq("filename", filename).execute()
    if res.data and res.data[0]["gdrive_link"]:
        return RedirectResponse(res.data[0]["gdrive_link"])
    
    raise HTTPException(status_code=404, detail="PDF not found in cloud storage")

@app.post("/api/parse")
def parse_documents():
    return {"success": True, "message": "In the cloud version, please run 'cloud_sync.py' on your computer to sync new PDFs."}

@app.get("/{filename}")
def serve_static(filename: str):
    file_path = os.path.join(FRONTEND_DIR, filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)

@app.get("/")
def serve_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend not found"}

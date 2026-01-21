from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import time

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=10000)
    region: Optional[str] = None

import os
import glob
from rag_service import rag_service

class FieldNoteRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=10000)

# In-memory store for notes (for demo purposes)
# In production, this should be a DB.
notes_db = {} 

import json

@app.on_event("startup")
async def startup_event():
    # Index seed data if collection is empty or we force it 
    # note: count() check might need reset if we want to ensure fresh data for this new schema. 
    # Because we are changing the schema (adding metadata), it's best to clear it if it exists or just add to it.
    # For this "shippable v1", assuming a fresh or compatible db is fine, or user can clear `chroma_db` folder.
    if rag_service.count() == 0:
        print("Indexing seed data...")
        seed_files = glob.glob("seed_data/*.json")
        for file_path in seed_files:
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    
                documents = data.get("documents", [])
                for doc in documents:
                    doc_id = doc.get("id")
                    text = doc.get("text")
                    title = doc.get("title")
                    
                    if doc_id and text:
                        # Construct metadata
                        metadata = {
                            "title": title,
                            "region": doc.get("region", "All"), # Default to All if missing
                            "domain": doc.get("domain", ""),
                            "category": doc.get("category", ""),
                            "source_file": os.path.basename(file_path)
                        }
                        rag_service.index_text(text, doc_id=doc_id, metadata=metadata)
            except Exception as e:
                print(f"Error processing seed file {file_path}: {e}")
                        
        print(f"Indexed seed documents from {len(seed_files)} files.")

@app.post("/field-note")
async def create_field_note(note: FieldNoteRequest):
    # Store note for later retrieval
    note_id = str(len(notes_db) + 1)
    notes_db[note_id] = note.text
    return {"note_id": note_id}

@app.get("/matches")
async def get_matches(note_id: str, region: Optional[str] = None):
    if note_id not in notes_db:
        return {"error": "Note not found"}
    
    note_text = notes_db[note_id]
    filters = {"region": region} if region and region != "All" else None
    matches = rag_service.search(note_text, filters=filters)
    return matches

@app.get("/recommendation")
async def get_recommendation(note_id: str, doc_id: str):
    if note_id not in notes_db:
        return {"error": "Note not found"}
    
    note_text = notes_db[note_id]
    recommendation = rag_service.generate_recommendation(note_text, doc_id)
    return recommendation

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    user_message = request.message
    region = request.region
    
    # Construct filters
    filters = None
    if region and region != "All":
        filters = {"region": region}

    # 1. Search for relevant documents
    matches = rag_service.search(user_message, n_results=3, filters=filters)
    
    if not matches:
        return {
            "role": "assistant",
            "content": f"I couldn't find any relevant agricultural information in my database for region '{region or 'Any'}' to answer that."
        }
    
    # 2. Use the top match to generate a recommendation
    # In a full system, might synthesize across multiple, but here we pick the best one.
    best_doc = matches[0]
    doc_id = best_doc['doc_id']
    
    result = rag_service.generate_recommendation(user_message, doc_id)
    
    # 3. Format the response
    # The frontend expects a simple string or struct.
    # Let's combine bullets and citations into a nice message.
    
    response_text = ""
    
    if result.get("bullets"):
        response_text += "Here are some recommendations based on our knowledge base:\n\n"
        for bullet in result["bullets"]:
            response_text += f"- {bullet}\n"
    
    if result.get("citations"):
        response_text += "\n**Evidence:**\n"
        for cite in result["citations"]:
             response_text += f"> {cite}\n"
             
    if result.get("fallback_used"):
        response_text += "\n*(Note: This response generated using fallback logic)*"

    return {
        "role": "assistant",
        "content": response_text
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
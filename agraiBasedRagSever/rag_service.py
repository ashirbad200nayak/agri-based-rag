import os
import numpy as np
import openai
from dotenv import load_dotenv

load_dotenv()

# Check for OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
AZURE_LLM_DEPLOYMENT = os.getenv("AZURE_LLM_DEPLOYMENT", "gpt-4o")

openai_client = None

if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT:
    print("Configuring for Azure OpenAI...")
    try:
        from openai import AzureOpenAI
        openai_client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version="2024-02-15-preview",
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            timeout=60.0
        )
    except Exception as e:
        print(f"Error initializing Azure OpenAI client: {e}")
elif OPENAI_API_KEY:
    print("Configuring for Standard OpenAI...")
    openai.api_key = OPENAI_API_KEY
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
else:
    print("WARNING: No OpenAI API keys found. RAG functionality will use fallbacks.")

class RagService:
    def __init__(self):
        # In-memory storage: list of dictionaries
        # Each item: { "id": str, "text": str, "metadata": dict, "vector": np.array }
        self.documents = []
        
    def count(self):
        """Returns the number of documents in the store."""
        return len(self.documents)

    def _get_embedding(self, text):
        if not openai_client:
            return np.zeros(1536) # Dummy vector if no API key
            
        try:
            # Helper to get embedding
            # Note: For Azure or Standard, client usage is similar.
            response = openai_client.embeddings.create(
                input=text,
                model=AZURE_EMBEDDING_DEPLOYMENT if AZURE_OPENAI_API_KEY else "text-embedding-ada-002" 
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return np.zeros(1536)

    def index_text(self, text: str, doc_id: str, metadata: dict) -> str:
        """
        Indexes a piece of text into the in-memory store.
        """
        vector = self._get_embedding(text)
        self.documents.append({
            "id": doc_id,
            "text": text,
            "metadata": metadata,
            "vector": vector
        })
        return doc_id

    def search(self, query_text: str, n_results: int = 5, filters: dict = None):
        """
        Searches for the most relevant documents using cosine similarity.
        """
        if not self.documents:
            return []

        query_vector = self._get_embedding(query_text)
        
        # Simple brute-force cosine similarity
        results = []
        for doc in self.documents:
            # Check filters
            if filters:
                match = True
                for k, v in filters.items():
                    if doc["metadata"].get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            # Cosine similarity: (A . B) / (||A|| * ||B||)
            # OpenAI embeddings are usually normalized, so just dot product is enough.
            # But let's be safe.
            doc_vector = doc["vector"]
            score = np.dot(query_vector, doc_vector) / (np.linalg.norm(query_vector) * np.linalg.norm(doc_vector) + 1e-9)
            
            # Use same score 0-100 scale as previous impl
            display_score = max(0, score * 100) 
            
            results.append({
                "doc_id": doc["id"],
                "text": doc["text"],
                "metadata": doc["metadata"],
                "score_0_100": round(display_score, 0),
                "raw_score": score
            })

        # Sort by score descending
        results.sort(key=lambda x: x["raw_score"], reverse=True)
        top_results = results[:n_results]

        matches = []
        for res in top_results:
            text = res["text"]
            evidence_snippet = text[:300] + "..." if len(text) > 300 else text
            
            matches.append({
                "doc_id": res["doc_id"],
                "title": res["metadata"].get("title", "Unknown Title"),
                "score_0_100": res["score_0_100"],
                "evidence_snippet": evidence_snippet
            })
            
        return matches

    def generate_recommendation(self, note_text: str, doc_id: str):
        """
        Generates a recommendation based on the note and a specific document.
        """
        # Find doc in memory
        doc_text = None
        for doc in self.documents:
            if doc["id"] == doc_id:
                doc_text = doc["text"]
                break
                
        if not doc_text:
            return {
                "bullets": ["Error: Document not found."],
                "citations": [],
                "fallback_used": True
            }
        
        if not openai_client:
             return {
                "bullets": ["Fallback: OpenAI API Key missing. Reference document manually."],
                "citations": ["Citation not available without LLM."],
                "fallback_used": True
            }       

        try:
            prompt = f"""
            You are an expert Field Ops Advisor for forestry and agriculture.
            Your task is to provide a grounded recommendation based on a specific Standard Operating Procedure (SOP).
            
            INPUTS:
            1. Field Note (User Observation): "{note_text}"
            2. Matched SOP (Reference Document): "{doc_text}"

            INSTRUCTIONS:
            - Provide 3-5 actionable bullet points telling the user what to do next based on the SOP.
            - EXTRACT EXACT TEXT SPANS from the SOP that support your advice. These must be verbatim quotes.
            - Output specific JSON format.

            OUTPUT FORMAT (JSON ONLY):
            {{
                "bullets": ["action 1", "action 2", ...],
                "citations": ["exact quote from text 1", "exact quote from text 2", ...]
            }}
            """
            
            completion = openai_client.chat.completions.create(
                model=AZURE_LLM_DEPLOYMENT if AZURE_OPENAI_API_KEY else "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3, # Lower temperature for better grounding
                response_format={ "type": "json_object" } # valid for newer models, safer parsing
            )
            
            content = completion.choices[0].message.content
            
            import json
            try:
                data = json.loads(content)
                return {
                    "bullets": data.get("bullets", []),
                    "citations": data.get("citations", []),
                    "fallback_used": False
                }
            except json.JSONDecodeError:
                # Fallback if json parsing fails but text is there
                return {
                    "bullets": ["Error parsing AI response.", content],
                    "citations": [],
                    "fallback_used": True
                }

        except Exception as e:
            print(f"LLM Error: {e}")
            return {
                "bullets": ["Error generating recommendation due to LLM failure."],
                "citations": [],
                "fallback_used": True
            }

# Singleton instance for easy import
rag_service = RagService()

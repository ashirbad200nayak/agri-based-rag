import os
import uuid
import chromadb
from chromadb.utils import embedding_functions
import openai
from dotenv import load_dotenv
import sys

# Patch sqlite3 for Vercel/Linux environments where system sqlite3 is too old
if os.environ.get("VERCEL"):
    try:
        __import__('pysqlite3')
        sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
    except ImportError:
        pass

load_dotenv()

# Check for OpenAI API key
# Check for OpenAI API key (Standard or Azure)
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

class CustomAzureEmbeddingFunction:
    def __init__(self, client, model_name):
        self.client = client
        self.model_name = model_name

    def _generate_embeddings(self, input):
        # Ensure input is a list
        if isinstance(input, str):
            input = [input]
        
        # Call the embedding API
        response = self.client.embeddings.create(
            input=input,
            model=self.model_name
        )
        
        # Extract embeddings
        return [data.embedding for data in response.data]

    def __call__(self, input):
        return self._generate_embeddings(input)

    def embed_documents(self, input):
        return self._generate_embeddings(input)

    def embed_query(self, input):
        return self._generate_embeddings(input)

    def name(self):
        return "custom_azure_embedding_function"

class RagService:
    def __init__(self, persistence_path="./chroma_db"):
        # On Vercel, we must use /tmp for any write operations
        if os.environ.get("VERCEL"):
            persistence_path = "/tmp/chroma_db"
            
        self.client = chromadb.PersistentClient(path=persistence_path)
        
        # Configure Embeddings
        if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT and openai_client:
            self.embedding_fn = CustomAzureEmbeddingFunction(
                client=openai_client,
                model_name=AZURE_EMBEDDING_DEPLOYMENT
            )
        elif OPENAI_API_KEY:
            self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_key=OPENAI_API_KEY,
                model_name="text-embedding-ada-002"
            )
        else:
            # Fallback to default equivalent (DefaultEmbeddingFunction uses ONNX MiniLM)
            self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()

        self.collection = self.client.get_or_create_collection(
            name="agri_knowledge_base",
            embedding_function=self.embedding_fn
        )

    def index_text(self, text: str, doc_id: str, metadata: dict) -> str:
        """
        Indexes a piece of text into the vector DB with metadata.
        """
        self.collection.add(
            documents=[text],
            metadatas=[metadata],
            ids=[doc_id]
        )
        return doc_id

    def search(self, query_text: str, n_results: int = 5, filters: dict = None):
        """
        Searches for the most relevant documents.
        Returns detailed matches including evidence snippets.
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=filters if filters else None
        )
        
        matches = []
        if results['ids']:
            ids = results['ids'][0]
            docs = results['documents'][0]
            metadatas = results['metadatas'][0]
            distances = results['distances'][0] if results['distances'] else [0]*len(ids)

            for i in range(len(ids)):
                # Score conversion (approximate for cosine distance)
                # Chroma cosine distance is typically 0 to 2.
                # Just using a simple mapping: 1 - distance (clamped to 0) * 100 
                # This is just for UI display not scientific precision here.
                score = max(0, 100 - (distances[i] * 100))
                
                # Evidence snippet: simple prefix or use text
                # Ideally, we would find the exact matching span, but for v1 we take the first 300 chars.
                evidence_snippet = docs[i][:300] + "..." if len(docs[i]) > 300 else docs[i]

                matches.append({
                    "doc_id": ids[i],
                    "title": metadatas[i].get("title", "Unknown Title"),
                    "score_0_100": round(score, 0),
                    "evidence_snippet": evidence_snippet
                })
        
        return matches

    def generate_recommendation(self, note_text: str, doc_id: str):
        """
        Generates a recommendation based on the note and a specific document.
        """
        # Fetch the doc content
        result = self.collection.get(ids=[doc_id])
        if not result['documents']:
            return {
                "bullets": ["Error: Document not found."],
                "citations": [],
                "fallback_used": True
            }
        
        doc_text = result['documents'][0]
        
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

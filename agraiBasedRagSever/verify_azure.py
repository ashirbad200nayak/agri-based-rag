
import os
from rag_service import rag_service, AZURE_OPENAI_API_KEY, OPENAI_API_KEY, openai_client

def verify_azure_config():
    print("--- Verifying Azure OpenAI Configuration ---")
    
    if AZURE_OPENAI_API_KEY:
        print(f"✅ AZURE_OPENAI_API_KEY found: {AZURE_OPENAI_API_KEY[:5]}...")
        print(f"✅ AZURE_OPENAI_ENDPOINT: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
        print(f"✅ AZURE_EMBEDDING_DEPLOYMENT: {os.getenv('AZURE_EMBEDDING_DEPLOYMENT', 'text-embedding-3-large')}")
        print(f"✅ AZURE_LLM_DEPLOYMENT: {os.getenv('AZURE_LLM_DEPLOYMENT', 'gpt-5')}")
        
        # Verify Client
        if openai_client:
             print("✅ OpenAI/Azure Client initialized successfully.")
        else:
             print("❌ OpenAI/Azure Client FAILED to initialize.")

        # Verify Embedding Function
        try:
            # Check internal attributes of embedding_fn if possible, or just run a test
            # Chroma 0.4.x stores config inside embedding_fn object usually
            print("Running test embedding...")
            test_doc = "This is a test document."
            # We can't easily call embedding_fn directly without inspecting chroma internals or just using the rag_service to index something.
            # Let's try to search using the service which triggers embedding.
            rag_service.search("test query", n_results=1)
            print("✅ Embedding and Search triggered successfully (no errors thrown).")
        except Exception as e:
            print(f"❌ Error during embedding/search test: {e}")

    else:
        print("ℹ️ AZURE_OPENAI_API_KEY not found. Checking for standard OpenAI...")
        if OPENAI_API_KEY:
            print(f"✅ OPENAI_API_KEY found: {OPENAI_API_KEY[:5]}...")
        else:
            print("❌ No API keys found.")

if __name__ == "__main__":
    verify_azure_config()

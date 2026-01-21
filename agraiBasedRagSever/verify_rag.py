import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def test_rag_flow():
    print("Testing RAG Flow...")
    
    # 1. Create Field Note
    print("\n1. submitting field note...")
    note_text = "I have a lot of aphids on my beans. What should I do?"
    response = requests.post(f"{BASE_URL}/field-note", json={"text": note_text})
    if response.status_code != 200:
        print(f"FAILED to submit note: {response.text}")
        sys.exit(1)
    
    data = response.json()
    note_id = data.get("note_id")
    print(f"Success! Note ID: {note_id}")
    
    # 2. Get Matches
    print(f"\n2. Getting matches for note {note_id}...")
    response = requests.get(f"{BASE_URL}/matches", params={"note_id": note_id})
    if response.status_code != 200:
        print(f"FAILED to get matches: {response.text}")
        sys.exit(1)
        
    matches = response.json()
    if not matches:
        print("WARNING: No matches found. Seed data might not be indexed or relevance is low.")
    else:
        print(f"Found {len(matches)} matches.")
        print(f"Top match: {matches[0]['title']} (Score: {matches[0]['score_0_100']})")
        
    # 3. Get Recommendation
    if matches:
        doc_id = matches[0]['doc_id']
        print(f"\n3. Getting recommendation using doc {doc_id}...")
        response = requests.get(f"{BASE_URL}/recommendation", params={"note_id": note_id, "doc_id": doc_id})
        
        if response.status_code != 200:
             print(f"FAILED to get recommendation: {response.text}")
        else:
            rec = response.json()
            print("Recommendation received:")
            print("\nBullets:")
            for b in rec.get("bullets", []):
                print(f"- {b}")
            print("\nFallback used:", rec.get("fallback_used"))
    
    print("\nVerification Complete.")

if __name__ == "__main__":
    # Wait a bit for server to be ready if called immediately after startup
    try:
        test_rag_flow()
    except requests.exceptions.ConnectionError:
        print("Could not connect to server. Is it running?")

# Agri-Based RAG Application

A full-stack RAG (Retrieval Augmented Generation) application for agricultural advice, featuring a React frontend and a FastAPI backend with ChromaDB.

## Features
- **Region Filter**: Filter knowledge base results by region (e.g., India, South America).
- **RAG Architecture**: Uses ChromaDB for vector storage and OpenAI/Azure OpenAI for generation.
- **Chat Interface**: Interactive chat UI built with React.
- **Seed Data**: Synthetic agricultural SOPs included for demonstration.

## Setup

### Prerequisites
- Node.js & npm
- Python 3.9+
- OpenAI API Key (Standard or Azure)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd agri-based-rag
   ```

2. **Frontend Setup**
   ```bash
   cd agribasedRag
   npm install
   ```

3. **Backend Setup**
   ```bash
   cd agraiBasedRagSever
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Environment Variables**
   Create a `.env` file in `agraiBasedRagSever/` based on `.env.example`:
   ```
   OPENAI_API_KEY=your_key_here
   # OR for Azure
   AZURE_OPENAI_API_KEY=...
   AZURE_OPENAI_ENDPOINT=...
   ```

## Running Locally

1. **Start Backend**
   ```bash
   cd agraiBasedRagSever
   python -m uvicorn app:app --port 8000 --reload
   ```

2. **Start Frontend**
   ```bash
   cd agribasedRag
   npm run dev
   ```

3. **Access App**: Open [http://localhost:5173](http://localhost:5173)

## Deployment (Vercel)

This project is configured for Vercel.

1. Install Vercel CLI: `npm i -g vercel`
2. Run `vercel` in the root directory.
3. Add your environment variables in the Vercel dashboard.

> **Note**: ChromaDB on Vercel uses ephemeral storage (`/tmp`), so the database resets on every cold start. This is strictly for demonstration.

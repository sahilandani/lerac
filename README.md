# Local RAG Application for SMEs

A Python-based Retrieval-Augmented Generation (RAG) application that runs 100% locally, designed for Small and Medium Enterprises (SMEs).

## Features

- **Ingestion**: Convert PDFs, Excel files, emails, and images to Markdown using LiteParse or fallbacks.
- **Storage**: Store document chunks in ChromaDB with metadata (source_name, upload_date, chunk_id).
- **Retrieval**: Query for top 5 most relevant chunks.
- **Reasoning**: Use Ollama with conflict-resolution prompt prioritizing newer dates; fallback to similarity-based answer if Ollama unavailable.
- **UI**: Streamlit interface with file uploader, chat, and support ticket generation.
- **Conflict Detection**: Explicit pre-LLM detection of contradictions.
- **Semantic Chunking**: Paragraph-based splitting for prose; row-level for tables.
- **Validation**: `validate_retrieval.py` for testing with dummy data.
- **CRM Mock**: UI form simulation for ticket submission.

## Prerequisites

- Python 3.8+
- Ollama installed and running locally (with Llama 3.2 or GLM4 model)
- For image OCR: Pillow and pytesseract (optional)

## Installation

1. Clone or download the project.
2. Create virtual environment: `python -m venv .venv`
3. Activate: `.venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`

## Usage

1. Start Ollama server: `ollama serve`
2. Pull a model: `ollama pull llama3.2` (or glm4)
3. Run the app: `streamlit run app.py`
4. Upload files, ask questions, generate tickets.

## Testing

- Use `test_sample.py` for isolated testing: `streamlit run test_sample.py`
- Supports PDFs, Excel, emails, images.

## Files

- `app.py`: Main Streamlit app
- `ingestion.py`: File parsing logic
- `storage.py`: ChromaDB setup and chunking
- `retrieval.py`: Query function
- `reasoning.py`: Ollama integration with conflict detection
- `test_sample.py`: Test interface
- `start.bat` / `stop.bat`: Batch scripts for starting/stopping

## Troubleshooting

- If LiteParse fails, it falls back to PyPDF2 for PDFs.
- Ensure Ollama is running for reasoning.
- ChromaDB data is in `./chroma_db`.
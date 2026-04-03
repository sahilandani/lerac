import streamlit as st
import os
from datetime import datetime
from ingestion import ingest_file
from storage import get_chroma_client, store_document, chunk_text

st.title("Sample Test Window for Parsing and Storage")

uploaded_file = st.file_uploader("Upload a sample file (PDF, Excel, email/text, or images)", type=['pdf', 'xlsx', 'xls', 'eml', 'txt', 'png', 'jpg', 'jpeg', 'bmp', 'gif', 'tiff'])

if uploaded_file:
    # Save file temporarily
    file_path = f"./temp_sample_{uploaded_file.name}"
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Check extension
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in ['.pdf', '.xlsx', '.xls', '.eml', '.txt']:
        st.error("Unsupported file type. Please upload PDF, Excel (.xlsx/.xls), or email/text (.eml/.txt) files.")
    else:
        try:
            # Ingest
            markdown = ingest_file(file_path)
            
            st.subheader("Parsed Markdown")
            st.code(markdown, language="markdown")
            
            # Simulate storage
            client = get_chroma_client()
            source_name = uploaded_file.name
            upload_date = datetime.now()
            store_document(client, source_name, markdown, upload_date)
            
            # Show chunks
            chunks = chunk_text(markdown)
            st.subheader("Generated Chunks")
            for i, chunk in enumerate(chunks):
                st.write(f"**Chunk {i+1}:** {chunk[:200]}...")
            
            st.success("Sample stored in ChromaDB!")
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
        finally:
            # Clean up
            if os.path.exists(file_path):
                os.remove(file_path)
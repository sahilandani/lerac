#!/usr/bin/env python3
"""
Validation script for RAG retrieval.
Ingests dummy data and runs test queries to validate retrieval and reasoning.
"""

import os
import tempfile
from datetime import datetime
from ingestion import ingest_file
from storage import get_chroma_client, store_document
from retrieval import retrieve_relevant_chunks
from reasoning import resolve_conflicts_and_reason

def create_dummy_files():
    """Create dummy files for testing."""
    files = []
    
    # Dummy PDF text (simulate)
    pdf_content = """
# Dummy PDF

This is a policy document.

Refund policy: Refunds are allowed within 30 days.

Updated: No refunds after 30 days.
"""
    pdf_path = tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False)
    pdf_path.write(pdf_content)
    pdf_path.close()
    files.append(('dummy_policy.pdf', pdf_path.name))
    
    # Dummy Excel (simulate CSV for simplicity)
    excel_content = "Product,Price,Stock\nApple,1.00,100\nBanana,0.50,200\n"
    excel_path = tempfile.NamedTemporaryFile(mode='w', suffix='.xlsx', delete=False)
    excel_path.write(excel_content)
    excel_path.close()
    files.append(('dummy_inventory.xlsx', excel_path.name))
    
    # Dummy email
    email_content = """
From: boss@company.com
Subject: Policy Update

Body: The refund policy has changed. No refunds allowed.
"""
    email_path = tempfile.NamedTemporaryFile(mode='w', suffix='.eml', delete=False)
    email_path.write(email_content)
    email_path.close()
    files.append(('dummy_email.eml', email_path.name))
    
    return files

def validate():
    """Run validation tests."""
    print("Creating dummy files...")
    files = create_dummy_files()
    
    client = get_chroma_client()
    
    print("Ingesting and storing...")
    for name, path in files:
        try:
            content = ingest_file(path)
            store_document(client, name, content, datetime.now())
            print(f"Stored: {name}")
        except Exception as e:
            print(f"Error with {name}: {e}")
        finally:
            os.unlink(path)
    
    print("\nRunning test queries...")
    test_queries = [
        "What is the refund policy?",
        "How much does an apple cost?",
        "What did the email say about refunds?"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        chunks = retrieve_relevant_chunks(query, n_results=3)
        if chunks:
            print(f"Retrieved {len(chunks)} chunks:")
            for chunk in chunks:
                print(f"  - {chunk['source_name']}: {chunk['content'][:100]}...")
            
            try:
                answer = resolve_conflicts_and_reason(chunks, query)
                print(f"Answer: {answer[:200]}...")
            except Exception as e:
                print(f"Reasoning failed: {e}")
        else:
            print("No chunks retrieved.")
    
    print("\nValidation complete.")

if __name__ == "__main__":
    validate()
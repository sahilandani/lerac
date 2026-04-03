import streamlit as st
import os
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from ingestion import ingest_file, infer_source_type, extract_dates_from_text
from storage import get_chroma_client, store_document
from retrieval import retrieve_relevant_chunks, retrieve_all_chunks
from reasoning import resolve_conflicts_and_reason, classify_intent, find_supporting_snippets


# -------------------------------
# File processing
# -------------------------------
def process_upload_file(client, uploaded_file):
    file_path = f"./temp_{uploaded_file.name}"
    try:
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        markdown = ingest_file(file_path)
        source_type = infer_source_type(file_path)

        file_date = None
        if isinstance(markdown, str):
            file_date = extract_dates_from_text(markdown)
        elif isinstance(markdown, dict) and 'file_date' in markdown:
            file_date = markdown['file_date']

        source_name = uploaded_file.name
        upload_date = datetime.now()

        store_document(
            client,
            source_name,
            markdown,
            upload_date,
            source_type=source_type,
            file_date=file_date
        )

        return (source_name, True, f"{source_name} ingested")

    except Exception as e:
        return (uploaded_file.name, False, str(e))

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# -------------------------------
# UI
# -------------------------------
st.title("Local RAG Application for SMEs")

st.markdown(
    "Drag and drop files or upload manually.\n\n"
    "Supports PDFs, Excel, email/text files, and images."
)

uploaded_files = st.file_uploader(
    "Upload files",
    accept_multiple_files=True,
    type=['pdf', 'xlsx', 'xls', 'eml', 'txt', 'png', 'jpg', 'jpeg']
)


# -------------------------------
# Clear database
# -------------------------------
if st.button("Clear stored data"):
    client = get_chroma_client()
    collection = client.get_collection(name='documents')

    try:
        current = collection.get(include=['metadatas'])
        metadatas = current.get('metadatas', [])

        all_ids = [
            m.get('chunk_id')
            for m in metadatas
            if isinstance(m, dict) and 'chunk_id' in m
        ]

        if all_ids:
            collection.delete(ids=all_ids)
        else:
            st.info("No documents to delete.")

    except Exception as e:
        st.error(f"Failed to clear stored data: {e}")

    else:
        st.success("All stored data cleared.")


# -------------------------------
# File ingestion
# -------------------------------
if uploaded_files:
    client = get_chroma_client()

    st.info("Processing files in background...")

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(process_upload_file, client, f): f
            for f in uploaded_files
        }

        for future in as_completed(futures):
            uploaded_file = futures[future]

            try:
                source_name, ok, msg = future.result()

                if ok:
                    st.success(f"{source_name} uploaded successfully!")
                else:
                    st.error(f"{source_name} failed: {msg}")

            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {e}")


# -------------------------------
# Chat system
# -------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

show_reasoning = st.checkbox("Show reasoning details", value=False)


# -------------------------------
# Chat input
# -------------------------------
if prompt := st.chat_input("Ask a question"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        ql = prompt.lower().strip()

        # Guard against vague queries
        if len(ql) < 40 and any(w in ql for w in [
            'tell me about', 'overview', 'explain', 'what is'
        ]):
            st.warning("Please ask a more specific question.")
            answer = "Query too broad. Please specify details."

        else:
            intent = classify_intent(prompt)

            source_filter = None
            if intent == 'Pricing':
                source_filter = ['policy', 'table']
            elif intent == 'Policy':
                source_filter = ['policy']
            elif intent == 'Communication':
                source_filter = ['email']

            chunks = retrieve_relevant_chunks(
                prompt,
                source_types=source_filter
            )

            if not chunks:
                chunks = retrieve_relevant_chunks(prompt, n_results=10)

            if chunks:
                st.info(
                    "Sources: " +
                    ", ".join([c['source_name'] for c in chunks])
                )

                answer = resolve_conflicts_and_reason(chunks, prompt)

            else:
                answer = "No relevant data found."

        if not show_reasoning and 'CRITIC VERDICT' in answer:
            answer = answer.split('CRITIC VERDICT:')[0].strip()

    except Exception as e:
        answer = f"Error: {str(e)}"

    st.session_state.messages.append({"role": "assistant", "content": answer})

    with st.chat_message("assistant"):
        st.markdown(answer)


# -------------------------------
# Support ticket generator
# -------------------------------
if st.button("Generate Support Ticket"):
    if st.session_state.messages:

        last_query = next(
            (m["content"] for m in reversed(st.session_state.messages)
             if m["role"] == "user"),
            ""
        )

        last_answer = next(
            (m["content"] for m in reversed(st.session_state.messages)
             if m["role"] == "assistant"),
            ""
        )

        sources = retrieve_relevant_chunks(last_query)

        ticket = {
            "ticket": {
                "query": last_query,
                "answer": last_answer,
                "sources": [
                    {
                        "source_name": s["source_name"],
                        "upload_date": str(s["upload_date"]),
                        "content": s["content"]
                    }
                    for s in sources
                ]
            }
        }

        with open("support_ticket_log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(ticket) + "\n")

        st.success("Support ticket saved!")

        st.download_button(
            "Download Ticket",
            json.dumps(ticket, indent=4),
            "ticket.json",
            "application/json"
        )

    else:
        st.error("No chat history found.")
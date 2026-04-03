import chromadb
from chromadb.config import Settings
import hashlib
from datetime import datetime

def get_chroma_client():
    """Initialize ChromaDB client."""
    return chromadb.PersistentClient(path="./chroma_db")

def semantic_chunk_text(text, chunk_size=500):
    """Semantic chunking: split by paragraphs, then by size."""
    # Split by double newlines (paragraphs)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def chunk_text(text, chunk_size=500):
    """Fallback to simple chunking if needed."""
    return semantic_chunk_text(text, chunk_size)

def normalize_date(datestr):
    """Ensure upload date is a datetime object."""
    if isinstance(datestr, datetime):
        return datestr
    if isinstance(datestr, str):
        try:
            return datetime.fromisoformat(datestr)
        except Exception:
            try:
                return datetime.fromisoformat(datestr.split(' ')[0])
            except Exception:
                return datetime.now()
    return datetime.now()


def _normalize_meta_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool, list)):
        return value
    if value is None:
        return None
    return str(value)


def store_document(client, source_name, markdown_content, upload_date, source_type='unknown', file_date=None):
    """Store chunks in ChromaDB with enhanced metadata and hierarchical table structure."""
    collection = client.get_or_create_collection(name="documents")
    upload_date = normalize_date(upload_date)

    chunks = []
    if isinstance(markdown_content, dict) and markdown_content.get('type') == 'table':
        # Parent row representing table context
        parent_chunk = {
            'content': f"TABLE {source_name} HEADERS: {', '.join(markdown_content.get('headers', []))}",
            'meta': {
                'is_parent': True,
                'source_type': source_type,
                'file_date': file_date.isoformat() if isinstance(file_date, datetime) else str(file_date) if file_date else ''
            }
        }
        chunks.append(parent_chunk)

        for row in markdown_content['rows']:
            row_text = ' | '.join([f"{k}: {v}" for k, v in row['values'].items()])
            chunks.append({
                'content': f"Row {row['row_index']}: {row_text}",
                'meta': {
                    'is_parent': False,
                    'parent_source': source_name,
                    'source_type': source_type,
                    'file_date': file_date.isoformat() if isinstance(file_date, datetime) else str(file_date) if file_date else ''
                }
            })
    elif isinstance(markdown_content, list):
        for item in markdown_content:
            chunks.append({'content': item, 'meta': {'source_type': source_type, 'file_date': file_date or ''}})
    else:
        for c in chunk_text(markdown_content):
            chunks.append({'content': c, 'meta': {'source_type': source_type, 'file_date': file_date or ''}})

    ids = []
    metadatas = []
    documents = []

    for i, chunk in enumerate(chunks):
        text = chunk['content']
        meta = chunk['meta']
        chunk_id = f"{source_name}_{i}_{hashlib.md5(text.encode()).hexdigest()[:8]}"
        ids.append(chunk_id)
        merged_meta = {
            "source_name": source_name,
            "upload_date": _normalize_meta_value(upload_date.isoformat()),
            "chunk_id": chunk_id,
            "chunk_index": _normalize_meta_value(str(i)),
            "source_type": _normalize_meta_value(source_type),
            "is_parent": _normalize_meta_value(meta.get('is_parent', False)),
            "parent_source": _normalize_meta_value(meta.get('parent_source', '')),
            "file_date": _normalize_meta_value(meta.get('file_date', ''))
        }
        metadatas.append(merged_meta)
        documents.append(text)

    collection.add(ids=ids, documents=documents, metadatas=metadatas)

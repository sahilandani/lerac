import chromadb
from datetime import datetime
import math
import re


def get_chroma_client():
    """Initialize ChromaDB client."""
    return chromadb.PersistentClient(path="./chroma_db")


def _normalize_date_value(date_str):
    if not date_str:
        return None
    if isinstance(date_str, datetime):
        return date_str
    if isinstance(date_str, str):
        try:
            return datetime.fromisoformat(date_str)
        except Exception:
            try:
                return datetime.strptime(date_str, '%m/%d/%Y')
            except Exception:
                try:
                    return datetime.strptime(date_str, '%d.%m.%Y')
                except Exception:
                    return None
    return None


def _recency_boost(file_date, reference_date=None):
    """Give newer documents higher score by recency factor."""
    dt = _normalize_date_value(file_date)
    if not dt:
        return 1.0
    if reference_date is None:
        reference_date = datetime.now()
    days_delta = (reference_date - dt).days
    return 1.0 + min(1.0, max(0.0, (365 - days_delta) / 365))


def retrieve_all_chunks():
    """Retrieve all stored chunks from ChromaDB."""
    client = get_chroma_client()
    collection = client.get_collection(name="documents")
    results = collection.get(include=['documents', 'metadatas'])
    chunks = []
    for doc, metadata in zip(results['documents'], results['metadatas']):
        chunks.append({
            "content": doc,
            "source_name": metadata.get("source_name"),
            "upload_date": metadata.get("upload_date"),
            "source_type": metadata.get("source_type"),
            "file_date": metadata.get("file_date"),
            "chunk_id": metadata.get("chunk_id"),
            "chunk_index": metadata.get("chunk_index")
        })
    return chunks


def _bm25_score(query, text):
    query_tokens = [t for t in re.findall(r"\w+", query.lower()) if t]
    doc_tokens = [t for t in re.findall(r"\w+", text.lower()) if t]
    if not query_tokens or not doc_tokens:
        return 0.0
    doc_len = len(doc_tokens)
    term_freq = {}
    for tok in doc_tokens:
        term_freq[tok] = term_freq.get(tok, 0) + 1

    # simple BM25 approximate weights
    k1 = 1.2
    b = 0.75
    avgdl = doc_len
    score = 0.0
    for token in set(query_tokens):
        if token in term_freq:
            raw = term_freq[token]
            score += ((raw * (k1 + 1)) / (raw + k1 * (1 - b + b * doc_len / (avgdl or 1))))
    return score


def keyword_search(query, n_results=5, source_types=None, date_after=None, date_before=None):
    """Fallback keyword-based retrieval for exact product code / phrase matches."""
    all_chunks = retrieve_all_chunks()
    filtered = []

    for c in all_chunks:
        if source_types and c.get('source_type') not in source_types:
            continue
        if date_after:
            fd = _normalize_date_value(c.get('file_date'))
            if not fd or fd < date_after:
                continue
        if date_before:
            fd = _normalize_date_value(c.get('file_date'))
            if not fd or fd > date_before:
                continue
        filtered.append(c)

    scored = []
    query_lower = query.lower()
    for c in filtered:
        content = c.get('content', '')
        score = _bm25_score(query_lower, content)
        if query_lower in content.lower():
            score += 3.0
        # Exact token match as strong clue (Widget A etc.)
        for term in re.findall(r"\w+", query_lower):
            if term and term in content.lower():
                score += 0.1
        if score > 0:
            scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:n_results]]


def retrieve_relevant_chunks(query, n_results=5, source_types=None, date_after=None, date_before=None):
    """Query ChromaDB for top n relevant chunks with hybrid semantic+keyword scoring and time weighting."""
    client = get_chroma_client()
    collection = client.get_collection(name="documents")

    where = {}
    if source_types:
        where['source_type'] = {'$in': source_types}

    if date_after or date_before:
        where['file_date'] = {}
        if date_after:
            where['file_date']['$gt'] = date_after.isoformat() if isinstance(date_after, datetime) else str(date_after)
        if date_before:
            where['file_date']['$lt'] = date_before.isoformat() if isinstance(date_before, datetime) else str(date_before)

    try:
        results = collection.query(query_texts=[query], n_results=n_results, where=where if where else None, include=['distances'])
    except Exception:
        results = collection.query(query_texts=[query], n_results=n_results, where=where if where else None)

    semantic_chunks = []
    distances = []
    if results is not None:
        distances = results.get('distances', [])
        if distances and isinstance(distances, list):
            distances = distances[0] if len(distances) > 0 and distances[0] is not None else []

    doc_list = []
    meta_list = []
    if results is not None:
        raw_docs = results.get('documents')
        raw_metas = results.get('metadatas')
        if isinstance(raw_docs, list) and len(raw_docs) > 0 and raw_docs[0] is not None:
            doc_list = raw_docs[0]
        elif isinstance(raw_docs, list):
            doc_list = raw_docs
        if isinstance(raw_metas, list) and len(raw_metas) > 0 and raw_metas[0] is not None:
            meta_list = raw_metas[0]
        elif isinstance(raw_metas, list):
            meta_list = raw_metas

    for idx, (doc, metadata) in enumerate(zip(doc_list, meta_list)):
        if doc is None or metadata is None:
            continue
        dist = distances[idx] if idx < len(distances) else None
        sem_score = 1.0 / (1.0 + (dist if dist is not None else 1.0))
        recency = _recency_boost(metadata.get('file_date'))
        semantic_chunks.append((sem_score * recency, {
            "content": doc,
            "source_name": metadata.get("source_name"),
            "upload_date": metadata.get("upload_date"),
            "source_type": metadata.get("source_type"),
            "file_date": metadata.get("file_date"),
            "chunk_id": metadata.get("chunk_id"),
            "chunk_index": metadata.get("chunk_index"),
            "score": sem_score,
            "recency": recency
        }))

    keyword_chunks = []
    # Run keyword search for terms that often need exact matching (product ids, refund policy, dates etc.)
    if any(k in query.lower() for k in ['widget', 'product', 'sku', 'code', 'refund', 'return', 'cancellation', 'policy', 'price', 'pricing', '30 days', 'window']):
        keyword_chunks = [(c, _bm25_score(query, c['content'])) for c in keyword_search(query, n_results=n_results*2, source_types=source_types, date_after=date_after, date_before=date_before)]

    combined = {}

    for score, chunk in semantic_chunks:
        cid = chunk['chunk_id']
        combined[cid] = chunk
        combined[cid]['combined_score'] = max(combined[cid].get('combined_score', 0), score)

    for chunk, kscore in keyword_chunks:
        cid = chunk.get('chunk_id')
        recency = _recency_boost(chunk.get('file_date'))
        combined_score = (kscore + 0.1) * recency
        if cid in combined:
            combined[cid]['combined_score'] = max(combined[cid]['combined_score'], combined_score)
        else:
            chunk['combined_score'] = combined_score
            combined[cid] = chunk

    ranked = sorted(combined.values(), key=lambda c: c.get('combined_score', 0), reverse=True)

    # If no semantic-boosted hits, fallback to keyword and/or raw matching
    if not ranked:
        if keyword_chunks:
            ranked = [c for c, _ in sorted(keyword_chunks, key=lambda x: x[1], reverse=True)]
        else:
            # fallback to pure text contains
            all_chunks = retrieve_all_chunks()
            query_lower = query.lower()
            contains_hits = [c for c in all_chunks if query_lower in (c.get('content', '').lower())]
            ranked = contains_hits

    return ranked[:n_results]

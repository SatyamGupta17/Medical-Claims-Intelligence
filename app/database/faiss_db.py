import numpy as np
try:
    import faiss
except Exception:
    faiss = None

# Simple in-memory FAISS adapter
_index = None
_dim = 384
_documents = []  # list of chunks
_metadata = []


def create_collection(dim: int = 384):
    global _index, _dim, _documents, _metadata
    _dim = dim
    _documents = []
    _metadata = []
    if faiss is None:
        _index = None
        return
    # IndexFlatL2 does not require training
    _index = faiss.IndexFlatL2(_dim)


def store_vectors(chunks, embeddings, filename):
    """Add chunks and embeddings to FAISS index and metadata store."""
    global _index, _documents, _metadata
    if faiss is None:
        return
    if _index is None:
        create_collection()

    # Ensure embeddings is a 2D numpy array float32
    embs = np.array([e.tolist() if hasattr(e, "tolist") else e for e in embeddings], dtype="float32")
    if embs.ndim == 1:
        embs = np.expand_dims(embs, 0)

    _index.add(embs)
    # store chunks and metadata
    for c in chunks:
        _documents.append(c)
        _metadata.append({"file": filename, "chunk": c})


def search_vectors(query_embedding, limit: int = 5):
    """Search FAISS index and return list of dicts with payload."""
    global _index, _documents, _metadata
    if faiss is None or _index is None or len(_documents) == 0:
        return []

    qe = query_embedding.tolist() if hasattr(query_embedding, "tolist") else list(query_embedding)
    xq = np.array([qe], dtype="float32")
    D, I = _index.search(xq, limit)
    results = []
    for dist, idx in zip(D[0], I[0]):
        if idx < 0 or idx >= len(_documents):
            continue
        md = _metadata[idx]
        results.append({"id": idx, "payload": md, "distance": float(dist)})
    return results

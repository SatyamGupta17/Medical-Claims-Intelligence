import chromadb

client = chromadb.Client()
collection = client.create_collection(name="documents")
def store_embeddings(chunks,embeddings,filename):
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        metadata = {
            "file": filename,
            "chunk_id": i
        }
        collection.add(
            documents=[chunk],
            embeddings=[emb.tolist()],
            metadatas=[metadata],
            ids=[f"{filename}_{i}"]
        )


# Search similar chunks
def search(query_embedding, top_k=5):
    results = collection.query(
        query_embeddings=[
            query_embedding.tolist()
        ],
        n_results=top_k
    )
    return results

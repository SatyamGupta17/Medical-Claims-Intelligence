import chromadb

# Create Chroma client
client = chromadb.Client()

# Create collection
collection = client.create_collection(
    name="documents"
)


# Store embeddings with metadata
def store_embeddings(
    chunks,
    embeddings,
    filename
):

    for i, (chunk, emb) in enumerate(
        zip(chunks, embeddings)
    ):

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

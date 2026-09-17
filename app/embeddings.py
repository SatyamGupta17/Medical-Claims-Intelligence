# # embeddings/embedder.py

# from openai import AzureOpenAI
# from app.config import OPENAI_ENDPOINT, OPENAI_KEY

# client = AzureOpenAI(
#     api_key=OPENAI_KEY,
#     azure_endpoint=OPENAI_ENDPOINT,
#     api_version="2024-02-01"
# )

# def generate_embedding(text):

#     response = client.embeddings.create(
#         model="text-embedding-3-large",
#         input=text
#     )

#     return response.data[0].embedding

from sentence_transformers import (
    SentenceTransformer
)

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

def create_embedding(text):

    embedding = model.encode(text)

    return embedding
# # chunking/chunker.py

# from langchain.text_splitter import RecursiveCharacterTextSplitter

# def create_chunks(text):

#     splitter = RecursiveCharacterTextSplitter(
#         chunk_size=1000,
#         chunk_overlap=200
#     )

#     chunks = splitter.split_text(text)

#     return chunks
 
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter
)

def chunk_text(text):

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = splitter.split_text(text)

    return chunks

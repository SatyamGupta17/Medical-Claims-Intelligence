# app/config.py

from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")

SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")

DOC_ENDPOINT = os.getenv("DOC_INTELLIGENCE_ENDPOINT")
DOC_KEY = os.getenv("DOC_INTELLIGENCE_KEY")
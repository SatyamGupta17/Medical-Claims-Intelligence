from groq import Groq
import os
from pathlib import Path
from dotenv import load_dotenv

# Explicitly load .env from project root 
env_path = Path(__file__).resolve().parent.parent / ".env" 
load_dotenv(dotenv_path=env_path)  
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

def ask_llm(context, question):

    prompt = f"""
    You are an intelligent document assistant. 
    Answer the user's question ONLY using the provided context.
    You may: 
        - summarize information 
        - combine related details 
        - infer the main topic from the context 
        
        Do NOT invent facts outside the context. 
        If the answer cannot be determined from the context, 
        say: "Information not found in document."

    Context:
    {context}

    Question:
    {question}
    """

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content
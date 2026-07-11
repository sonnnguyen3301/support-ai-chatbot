import os
from dotenv import load_dotenv
from openai import OpenAI

# 1. Initialize and load API Key from .env file
load_dotenv()
client = OpenAI()

# Directory containing Markdown articles from Part 1
MARKDOWN_DIR = "markdown_docs"

def main():
    if not os.path.exists(MARKDOWN_DIR):
        print(f"Error: Directory '{MARKDOWN_DIR}' not found. Please run the Part 1 scraper first.")
        return

    file_paths = [
        os.path.join(MARKDOWN_DIR, f) 
        for f in os.listdir(MARKDOWN_DIR) if f.endswith('.md')
    ]
    
    if not file_paths:
        print(f"Directory '{MARKDOWN_DIR}' is empty. No files to upload.")
        return

    print(f"Found {len(file_paths)} Markdown files. Initializing OpenAI Vector Store...")

    vector_store = client.vector_stores.create(
        name="OptiSigns Knowledge Base"
    )
    print(f"-> Successfully created Vector Store. (ID: {vector_store.id})")

    file_streams = [open(path, "rb") for path in file_paths]
    
    print("Uploading files to OpenAI and polling for embedding completion...")
    file_batch = client.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store.id,
        files=file_streams
    )

    for stream in file_streams:
        stream.close()

    print(f"-> Upload status: {file_batch.status}")
    print(f"-> File counts result: {file_batch.file_counts}")

    print("\nConfiguring AI Assistant (OptiBot)...")
    
    system_instructions = (
        "You are OptiBot, the customer-support bot for OptiSigns.com.\n"
        "• Tone: helpful, factual, concise.\n"
        "• Only answer using the uploaded docs.\n"
        "• Max 5 bullet points; else link to the doc.\n"
        "• Cite up to 3 \"Article URL:\" lines per reply."
    )

    assistant = client.beta.assistants.create(
        name="OptiBot Assistant",
        instructions=system_instructions,
        model="gpt-4o", 
        tools=[{"type": "file_search"}], 
        tool_resources={
            "file_search": {
                "vector_store_ids": [vector_store.id] 
            }
        }
    )

    print("-" * 50)
    print("PART 2 COMPLETED SUCCESSFULLY!")
    print(f"Assistant ID   : {assistant.id}")
    print(f"Vector Store ID: {vector_store.id}")
    print("-> You can now go to the OpenAI Platform for the Sanity Check.")
    print("-" * 50)

if __name__ == "__main__":
    main()
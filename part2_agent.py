import os
import glob
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables from the .env file
load_dotenv()

def main():
    # Initialize the Gemini client (automatically picks up GEMINI_API_KEY from environment)
    client = genai.Client()
    
    markdown_folder = "markdown_docs"
    search_pattern = os.path.join(markdown_folder, "*.md")
    md_files = glob.glob(search_pattern)
    
    if not md_files:
        print(f"No markdown files found in '{markdown_folder}'. Please run Part 1 scraper first.")
        return

    print(f"Found {len(md_files)} files to upload to Gemini File API...")
    uploaded_files = []

    # 1. Upload files to Gemini File API to be used as context grounding
    for file_path in md_files:
        print(f"Uploading {os.path.basename(file_path)}...")
        try:
            # Upload file using the official File API
            uploaded_file = client.files.upload(file=file_path)
            uploaded_files.append(uploaded_file)
        except Exception as e:
            print(f"Failed to upload {file_path}: {e}")

    print(f"Successfully uploaded {len(uploaded_files)} documents to Gemini File API.")

    # 2. Define the system instructions for OptiBot
    system_instruction = (
        "You are OptiBot, an expert AI Assistant specialized in OptiSigns digital signage software. "
        "Your task is to provide accurate, helpful, and professional support to users using the provided context documents. "
        "Always rely on the attached documents to answer questions. If the answer cannot be found in the context, "
        "politely inform the user that you don't have that information and offer to escalate to human support."
    )

    # 3. Initialize a chat session using the core conversational model
    print("Initializing OptiBot chat session...")
    
    chat = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.3,  # Low temperature for factual, grounded responses
        )
    )

    # 4. Interactive Chat Loop
    print("\nOptiBot is ready! Type 'exit' to quit.")
    print("-" * 50)
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            break
            
        if not user_input.strip():
            continue
            
        try:
            # Pass both the uploaded context files and the current user input text
            # inside the message parameter for active grounding
            payload = uploaded_files + [user_input]
            
            response = chat.send_message(message=payload)
            print(f"\nOptiBot: {response.text}\n")
            print("-" * 50)
        except Exception as e:
            print(f"Error generating response: {e}")

if __name__ == "__main__":
    main()
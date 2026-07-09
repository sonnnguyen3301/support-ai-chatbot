import os
import re
import io
import time
from datetime import datetime
import requests
from markdownify import markdownify as md
from openai import OpenAI
from dotenv import load_dotenv

# Load variables from .env file (primarily for local execution)
load_dotenv()

# Configuration and Constants
ZENDESK_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json?per_page=100"
VECTOR_STORE_NAME = "OptiSigns-Knowledge-Base"
ASSISTANT_NAME = "OptiBot"
SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply."""

def fetch_zendesk_articles():
    """Fetches up to 100 help articles directly from the Zendesk Help Center API."""
    print("Fetching articles from Zendesk API...")
    try:
        response = requests.get(ZENDESK_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
        articles = data.get("articles", [])
        # Filter out empty or draft articles
        valid_articles = [a for a in articles if a.get("body")]
        print(f" -> Found {len(valid_articles)} valid articles.")
        return valid_articles
    except Exception as e:
        print(f"Error fetching data from Zendesk: {e}")
        return []

def convert_html_to_markdown(html_body, article_url="#"):
    """Converts raw HTML text into clean Markdown and appends the source URL citation."""
    if not html_body:
        return ""
    # Convert HTML elements to standard Markdown structural elements
    markdown = md(html_body, heading_style="ATX", strip=["script", "style"])
    # Append the Article URL citation strictly matching OptiBot's prompt instructions
    markdown += f"\n\n---\nArticle URL: {article_url}\n"
    return markdown

def get_or_create_resources(client):
    """
    Ensures an OpenAI Vector Store and Assistant exist.
    Reuses existing assets if they match the assigned names to prevent resource leakage.
    """
    vector_store_id = None
    assistant_id = None

    # 1. Resolve Vector Store
    try:
        stores = client.beta.vector_stores.list(limit=50)
        for vs in stores.data:
            if vs.name == VECTOR_STORE_NAME:
                vector_store_id = vs.id
                break
    except Exception:
        pass

    if not vector_store_id:
        print("Creating a new OpenAI Vector Store...")
        vs = client.beta.vector_stores.create(name=VECTOR_STORE_NAME)
        vector_store_id = vs.id
    else:
        print(f"Using existing OpenAI Vector Store (ID: {vector_store_id})")

    # 2. Resolve Assistant
    try:
        assistants = client.beta.assistants.list(limit=50)
        for ast in assistants.data:
            if ast.name == ASSISTANT_NAME:
                assistant_id = ast.id
                break
    except Exception:
        pass

    if not assistant_id:
        print(f"Creating a new OpenAI Assistant ({ASSISTANT_NAME})...")
        assistant = client.beta.assistants.create(
            name=ASSISTANT_NAME,
            instructions=SYSTEM_PROMPT,
            model="gpt-4o-mini",
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}}
        )
        assistant_id = assistant.id
    else:
        print(f"Using existing OpenAI Assistant (ID: {assistant_id})")
        # Ensure tool resources remain attached correctly
        client.beta.assistants.update(
            assistant_id=assistant_id,
            tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}}
        )

    return vector_store_id, assistant_id

def upload_and_attach_to_vector_store(client, vector_store_id, filename, content):
    """Uploads data bytes in-memory to OpenAI storage and mounts it to the Vector Store."""
    try:
        # Create an in-memory file stream to avoid write operations onto volatile container layers
        file_io = io.BytesIO(content.encode("utf-8"))
        file_io.name = filename
        
        # Upload file directly to OpenAI
        openai_file = client.files.create(file=file_io, purpose="assistants")
        
        # Attach the uploaded file to the specific Vector Store
        client.beta.vector_stores.files.create(vector_store_id=vector_store_id, file_id=openai_file.id)
        return openai_file.id
    except Exception as e:
        print(f" -> Error uploading/attaching file {filename}: {e}")
        return None

def sync_articles_to_openai(client, vector_store_id, zendesk_articles):
    """
    Computes a remote Delta sync matrix comparing real-time Zendesk articles with 
    active OpenAI Vector store files. Identifies and executes ADDED, UPDATED, and SKIPPED states.
    """
    print("Fetching existing files from OpenAI Vector Store to compute Delta...")
    
    # Structure: { "article_id": {"file_id": "...", "filename": "..."} }
    openai_files = {}
    try:
        vs_files = client.beta.vector_stores.files.list(vector_store_id=vector_store_id, limit=100)
        for vs_file in vs_files.data:
            file_detail = client.files.retrieve(vs_file.id)
            fname = file_detail.filename
            
            # Extract target article ID from filenames formatted as "ID-v-TIMESTAMP-..."
            match = re.match(r"^(\d+)-v-", fname)
            if match:
                art_id = match.group(1)
                openai_files[art_id] = {
                    "file_id": vs_file.id,
                    "filename": fname
                }
    except Exception as e:
        print(f"Warning: Could not fetch remote vector store inventory ({e}). Forcing full sync.")

    added_count = 0
    updated_count = 0
    skipped_count = 0

    print("Analyzing articles for Delta Updates...")
    
    for article in zendesk_articles:
        art_id = str(article['id'])
        html_body = article.get('body', '')
        html_url = article.get('html_url', 'https://support.optisigns.com')
        
        # Parse Zendesk ISO string into a deterministic Unix epoch timestamp for integrity hashing
        updated_str = article.get('updated_at', '0')
        try:
            clean_time_str = updated_str.replace('Z', '+00:00')
            dt = datetime.fromisoformat(clean_time_str)
            timestamp = int(dt.timestamp())
        except Exception:
            timestamp = 0

        # Construct clean normalized slug layout
        slug = article['title'].lower().replace(" ", "-")
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        
        # Pattern matching naming convention: {ID}-v-{TIMESTAMP}-{SLUG}.md
        new_filename = f"{art_id}-v-{timestamp}-{slug}.md"
        markdown_content = convert_html_to_markdown(html_body, html_url)

        # Delta Logic Evaluation Pipeline
        if art_id in openai_files:
            existing_file_info = openai_files[art_id]
            existing_filename = existing_file_info["filename"]
            existing_file_id = existing_file_info["file_id"]
            
            # Check if timestamps embedded inside names match up exactly
            if f"-v-{timestamp}-" in existing_filename:
                print(f"[SKIPPED] Article ID: {art_id} has no updates.")
                skipped_count += 1
            else:
                # Trigger UPDATED pipeline: Delete ancient asset metadata, load delta replacement
                print(f"[UPDATED] Article ID: {art_id} content change detected. Upgrading cloud file assets...")
                try:
                    # Dissociate from Vector Store index
                    client.beta.vector_stores.files.delete(vector_store_id=vector_store_id, file_id=existing_file_id)
                    # Erase from base organization storage tier
                    client.files.delete(file_id=existing_file_id)
                except Exception as ex:
                    print(f" -> Note: Asset garbage collection statement returned warning: {ex}")
                
                file_id = upload_and_attach_to_vector_store(client, vector_store_id, new_filename, markdown_content)
                if file_id:
                    print(f" -> Successfully updated & re-embedded. (New File ID: {file_id})")
                    updated_count += 1
        else:
            # Trigger ADDED pipeline
            print(f"[ADDED] Processing Article ID: {art_id} -> {new_filename}")
            file_id = upload_and_attach_to_vector_store(client, vector_store_id, new_filename, markdown_content)
            if file_id:
                print(f" -> Successfully uploaded & embedded. (File ID: {file_id})")
                added_count += 1

    # Print out transaction report logs parsed cleanly by reviewer monitoring engines
    print("\n" + "-" * 40)
    print("CRON JOB EXECUTION SUMMARY:")
    print(f"Added   : {added_count}")
    print(f"Updated : {updated_count}")
    print(f"Skipped : {skipped_count}")
    print("-" * 40)

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("CRITICAL ERROR: Environment variable 'OPENAI_API_KEY' is missing.")
        exit(1)

    # Initialize the core client configuration
    client = OpenAI(api_key=api_key)

    # Resolve platform components
    vector_store_id, _ = get_or_create_resources(client)

    # Pipeline sequence trigger
    zendesk_articles = fetch_zendesk_articles()
    
    if not zendesk_articles:
        print("No articles to process. Pipeline transaction halted.")
        return

    sync_articles_to_openai(client, vector_store_id, zendesk_articles)
    print("Process finished successfully. Exiting code 0.")

if __name__ == "__main__":
    main()
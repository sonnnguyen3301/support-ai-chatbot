import os
import json
import glob
import requests
from markdownify import markdownify
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Global Configurations
API_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json?per_page=40"
OUTPUT_DIR = "markdown_docs"
STATE_FILE = "sync_state.json"

load_dotenv()

def load_sync_state():
    """
    Load the tracking state from the local JSON file.
    """
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not read state file, initializing fresh state. Error: {e}")
    return {}

def save_sync_state(state):
    """
    Persist the tracking state back to the local JSON file.
    """
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving state file: {e}")

def main():
    # 1. Initialize Gemini Client
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        return

    client = genai.Client()

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 2. Load current sync state
    sync_state = load_sync_state()
    new_sync_state = {}

    # 3. Fetch data from Zendesk API
    print(f"Fetching documentation articles from: {API_URL}")
    try:
        response = requests.get(API_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
        articles = data.get("articles", [])
    except Exception as e:
        print(f"Failed to fetch articles from Zendesk: {e}")
        return

    # Counter metrics required by the test criteria
    added_count = 0
    updated_count = 0
    skipped_count = 0

    delta_files_to_upload = []

    # 4. Process Delta Detection
    for article in articles:
        article_id = str(article.get("id"))
        api_updated_at = article.get("updated_at")
        html_url = article.get("html_url", "")
        html_body = article.get("body")

        if not html_body:
            continue

        # Generate slug name for referencing the document file
        slug = html_url.split("/")[-1] if html_url else article_id
        file_path = os.path.join(OUTPUT_DIR, f"{slug}.md")

        # Check if article is New, Updated, or Unchanged
        if article_id not in sync_state:
            status = "ADDED"
            added_count += 1
        elif sync_state[article_id] != api_updated_at:
            status = "UPDATED"
            updated_count += 1
        else:
            status = "SKIPPED"
            skipped_count += 1

        # Keep tracking the current state irrespective of changes
        new_sync_state[article_id] = api_updated_at

        if status in ["ADDED", "UPDATED"]:
            print(f"[{status}] Processing article ID: {article_id} -> {slug}.md")
            # Convert HTML raw layout to optimized Markdown structure
            md_content = markdownify(html_body, heading_style="ATX")
            
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(md_content)
                delta_files_to_upload.append(file_path)
            except IOError as e:
                print(f"Failed to write file {file_path}: {e}")

    # Save the updated sync state locally
    save_sync_state(new_sync_state)

    # 5. Programmatic API upload of the delta documents to Gemini File API
    if delta_files_to_upload:
        print(f"\nFound {len(delta_files_to_upload)} changes. Syncing delta with Gemini File API...")
        for file_path in delta_files_to_upload:
            print(f"Uploading delta file: {os.path.basename(file_path)}")
            try:
                # API upload behavior strictly executed as requested
                uploaded_file= client.files.upload(file=file_path,config={'mime_type': 'text/markdown'})

                print(f" -> Successfully uploaded! (ID: {uploaded_file.name})")
            except Exception as e:
                print(f"Failed uploading {file_path} to Gemini API: {e}")
    else:
        print("\nNo new or updated data discovered during this execution sync cycle.")

    # 6. Structured completion output logs required by the job specification
    print("-" * 40)
    print("CRON JOB EXECUTION SUMMARY:")
    print(f"Added   : {added_count}")
    print(f"Updated : {updated_count}")
    print(f"Skipped : {skipped_count}")
    print("-" * 40)
    print("Process finished successfully. Exiting code 0.")

if __name__ == "__main__":
    main()
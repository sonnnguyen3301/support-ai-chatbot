import os
import json
import requests
from markdownify import markdownify
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables (for local run). Docker will pass this via -e flag.
load_dotenv()

# Global Configurations
API_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json?per_page=40"
OUTPUT_DIR = "markdown_docs"
STATE_FILE = "sync_state.json"
VECTOR_STORE_NAME = "OptiSigns Knowledge Base"
ASSISTANT_NAME = "OptiBot Assistant"

# Initialize OpenAI client
client = OpenAI()

def load_state():
    """Read the local sync state file to track update history."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"vector_store_id": None, "assistant_id": None, "articles": {}}

def save_state(state):
    """Persist the tracking state back to the local file."""
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

def setup_openai_infrastructure(state):
    """Setup or retrieve Vector Store and Assistant on OpenAI."""
    # 1. Manage Vector Store
    if not state.get("vector_store_id"):
        print("Creating a new OpenAI Vector Store...")
        vs = client.beta.vector_stores.create(name=VECTOR_STORE_NAME)
        state["vector_store_id"] = vs.id
        save_state(state)
    
    vector_store_id = state["vector_store_id"]

    # 2. Manage Assistant
    if not state.get("assistant_id"):
        print("Creating a new OpenAI Assistant (OptiBot)...")
        system_instructions = (
            "You are OptiBot, the customer-support bot for OptiSigns.com.\n"
            "• Tone: helpful, factual, concise.\n"
            "• Only answer using the uploaded docs.\n"
            "• Max 5 bullet points; else link to the doc.\n"
            "• Cite up to 3 \"Article URL:\" lines per reply."
        )
        
        assistant = client.beta.assistants.create(
            name=ASSISTANT_NAME,
            instructions=system_instructions,
            model="gpt-4o-mini", 
            tools=[{"type": "file_search"}],
            tool_resources={
                "file_search": {
                    "vector_store_ids": [vector_store_id]
                }
            }
        )
        state["assistant_id"] = assistant.id
        save_state(state)

    return state["vector_store_id"]

def fetch_zendesk_articles():
    """Fetch articles from Zendesk API."""
    print(f"Fetching articles from Zendesk API...")
    try:
        response = requests.get(API_URL, timeout=15)
        response.raise_for_status()
        return response.json().get('articles', [])
    except Exception as e:
        print(f"Error fetching data from Zendesk: {e}")
        return []

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 1. Setup Environment and Load State
    state = load_state()
    vector_store_id = setup_openai_infrastructure(state)
    
    # 2. Fetch latest data
    articles = fetch_zendesk_articles()
    if not articles:
        print("No articles found to process. Exiting.")
        return

    # Counter metrics required by the test criteria
    added_count = 0
    updated_count = 0
    skipped_count = 0

    print("Analyzing articles for Delta Updates...")
    for article in articles:
        article_id = str(article.get('id'))
        api_updated_at = article.get('updated_at')
        html_url = article.get('html_url', '')
        html_body = article.get('body')

        if not html_body:
            continue

        slug = html_url.split('/')[-1] if html_url else article_id
        file_path = os.path.join(OUTPUT_DIR, f"{slug}.md")

        # Delta Detection Logic: Check if New or Updated
        is_new = article_id not in state["articles"]
        is_updated = not is_new and state["articles"][article_id]["updated_at"] < api_updated_at

        if is_new or is_updated:
            status_label = "ADDED" if is_new else "UPDATED"
            print(f"[{status_label}] Processing Article ID: {article_id} -> {slug}.md")

            # Remove old file version from OpenAI to prevent data duplication
            if is_updated:
                old_file_id = state["articles"][article_id].get("file_id")
                if old_file_id:
                    try:
                        print(f" -> Removing old file version ({old_file_id}) from OpenAI...")
                        client.files.delete(old_file_id)
                    except Exception as e:
                        print(f" -> Warning: Could not delete old file from OpenAI: {e}")
                updated_count += 1
            else:
                added_count += 1

            # 1. Convert HTML to clean Markdown
            md_content = markdownify(html_body, heading_style="ATX")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(md_content)

            # 2. Upload new file to OpenAI via API
            try:
                with open(file_path, "rb") as f_stream:
                    openai_file = client.files.create(file=f_stream, purpose="assistants")
                
                # 3. Attach file to the Vector Store
                client.beta.vector_stores.files.create(
                    vector_store_id=vector_store_id, 
                    file_id=openai_file.id
                )
                print(f" -> Successfully uploaded & embedded. (File ID: {openai_file.id})")

                # 4. Update local state
                state["articles"][article_id] = {
                    "updated_at": api_updated_at,
                    "file_id": openai_file.id
                }
                save_state(state)

            except Exception as e:
                print(f" -> Error syncing file to OpenAI: {e}")
        else:
            skipped_count += 1

    # Execution Summary Output
    print("-" * 40)
    print("CRON JOB EXECUTION SUMMARY:")
    print(f"Added   : {added_count}")
    print(f"Updated : {updated_count}")
    print(f"Skipped : {skipped_count}")
    print("-" * 40)
    print("Process finished successfully. Exiting code 0.")

if __name__ == "__main__":
    main()
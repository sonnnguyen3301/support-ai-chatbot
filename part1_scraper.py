import os
import requests
from markdownify import markdownify

# Global constants
API_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json?per_page=40"
OUTPUT_DIR = "markdown_docs"

def fetch_articles(url):
    """
    Fetch the list of articles from the Zendesk API.
    """
    print(f"Calling API: {url}...")
    try:
        response = requests.get(url, timeout=10)
        # Raise an HTTPError if the HTTP request returned an unsuccessful status code
        response.raise_for_status()
        
        data = response.json()
        articles = data.get('articles', [])
        print(f"Found {len(articles)} articles.")
        return articles
        
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to API: {e}")
        return []

def process_and_save_article(article):
    """
    Extract article data, convert HTML body to Markdown, and save to a file.
    """
    article_id = article.get('id')
    html_url = article.get('html_url', '')
    html_body = article.get('body')
    
    # Skip processing if the article has no content
    if not html_body:
        print(f"Skipping article ID {article_id} because it has an empty body.")
        return False

    # 1. Extract Slug from URL. If URL is missing, fall back to ID as filename.
    # Example: ".../articles/123-abc" -> slug = "123-abc"
    if html_url:
        slug = html_url.split('/')[-1]
    else:
        slug = str(article_id)

    # 2. Convert HTML content to standard Markdown
    # Use heading_style="ATX" to convert H1, H2 tags into clean #, ## Markdown style
    md_content = markdownify(html_body, heading_style="ATX")

    # 3. Save the Markdown content to a file
    file_path = os.path.join(OUTPUT_DIR, f"{slug}.md")
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(md_content)
        return True
    except IOError as e:
        print(f"Error saving file {file_path}: {e}")
        return False

def main():
    """
    Main execution flow for the scraping and conversion process.
    """
    # Create the output directory if it does not exist
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created directory: {OUTPUT_DIR}/")

    # Fetch articles from the API
    articles = fetch_articles(API_URL)
    
    if not articles:
        print("No articles to process. Exiting program.")
        return

    # Process each article and keep track of successful exports
    success_count = 0
    for article in articles:
        is_saved = process_and_save_article(article)
        if is_saved:
            success_count += 1

    print("-" * 30)
    print(f"COMPLETE: Successfully saved {success_count}/{len(articles)} Markdown files into '{OUTPUT_DIR}/'.")

if __name__ == "__main__":
    main()
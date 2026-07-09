# KB Sync Pipeline & AI Assistant

An automated ETL pipeline that scrapes support articles, converts them to Markdown, executes incremental delta updates, and programmatically populates an OpenAI Vector Store for a production RAG Assistant.

---

## 🛠️ System Overview & Architecture

- **Stage 1 (Scrape):** Pulls raw JSON data directly via Zendesk Help Center API to bypass navigation elements and ads. Normalizes HTML content into semantic, ATX-style Markdown using `markdownify`.
- **Stage 2 (Delta Engine):** Tracks modification timestamps against a local state object (`sync_state.json`). Automatically classifies updates into `ADDED`, `UPDATED`, or `SKIPPED`. Stale data versions on OpenAI are programmatically deleted prior to replacing them with new delta files to ensure no duplication.
- **Stage 3 (Chunking & Embedding):** Utilizes OpenAI's native Vector Store API via the File Batches endpoints. Text parsing, layout splitting, and markdown structural boundaries are managed under-the-hood natively by OpenAI, ensuring zero chunking drift.

---

## 💻 Local Execution (Docker)

The application is fully dockerized, executes as a single transaction job, and gracefully exits with status `0`.

### Prerequisites
Ensure your local environment includes a configured `.env` file mapping:
```text
OPENAI_API_KEY=your_secret_api_key_here

#Execution Commands

## Build the production container image
docker build -t support-ai-sync .

## Run the sync operation sequentially 
docker run --rm -e OPENAI_API_KEY="sk-proj-..." support-ai-sync


## ☁️ Production Deployment & Monitoring

- **Deployment Platform:** Deployed as an automated daily serverless **Cron Job** on Render using the compiled Dockerfile.
- **Schedule Execution:** Configured to trigger once per day.
- **Production Execution Run Logs:** [Dán link trang dashboard/logs Render của bạn vào đây]
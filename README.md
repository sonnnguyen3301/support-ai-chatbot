# KB Sync Pipeline & AI Assistant

An automated ETL pipeline that scrapes support articles, converts them to Markdown, executes incremental delta updates, and programmatically populates an OpenAI Vector Store for a production RAG Assistant.

---

## 🛠️ System Overview & Architecture

- **Stage 1 (Scrape):** Pulls raw JSON data directly via Zendesk Help Center API to bypass navigation elements and ads. Normalizes HTML content into semantic, ATX-style Markdown using `markdownify`.
- **Stage 2 (Delta Engine):** Tracks modification timestamps directly against the remote OpenAI Vector Store file database using embedded filename tags. Automatically classifies updates into `ADDED`, `UPDATED`, or `SKIPPED`. Stale data versions on OpenAI are programmatically deleted prior to replacing them with new delta files to ensure zero asset duplication.
- **Stage 3 (Chunking & Embedding):** Utilizes OpenAI's native Vector Store API via the File Batches endpoints. Text parsing, layout splitting, and markdown structural boundaries are managed under-the-hood natively by OpenAI, ensuring zero chunking drift.
- **Stage 4 (Automated Cloud Logging):** Captures runtime logs in-memory using an interception layer. Upon cloud execution termination, the buffer is base64-encoded and committed directly via the GitHub Contents API to the repository's `logs/` directory as public artifacts (automatically bypassed during basic local runs).

---

## 💻 Local Execution (Docker)

The application is fully dockerized, executes as a single transaction job, and gracefully exits with status `0`.

### Prerequisites
Create a `.env` file in your root directory based on the provided `.env.example`. For local evaluation, only the OpenAI key is strictly required:
```text
API_KEY=your_secret_api_key_here

#Execution Commands

## Build the production container image
docker build -t support-ai-sync .

## Run the sync operation sequentially using only the required OpenAI API Key
docker run --rm -e API_KEY="sk-proj-..." support-ai-sync

#☁️ Production Deployment & Monitoring
Deployment Platform: Deployed as an automated serverless Cron Job on Railway using the compiled production Dockerfile.

Schedule Execution: Configured to trigger daily at 01:00 UTC (08:00 AM ICT / Vietnam Time) (0 1 * * *).

Production Execution Run Logs: To guarantee long-term data persistence across serverless cloud boundaries, every automated pipeline execution generates a unique timestamped run trace artifact. You can inspect the historical live cloud execution logs directly within the repository: https://github.com/sonnnguyen3301/support-ai-chatbot/tree/main/logs

#🔄 Delta Sync & Chunking Strategy
Instead of relying on volatile local file storage (sync_state.json) which is wiped out across stateless serverless cloud container lifecycles, this pipeline implements a robust Remote State Validation Strategy:

- Remote Inventory Scanning: Every boot sequence fetches the active file inventory directly from the OpenAI Vector Store API.

- Deterministic Metadata Hashing: Document naming conventions are strict and deterministic: {Zendesk_Article_ID}-v-{Unix_Updated_Timestamp}-{Slug}.md.

- Delta Matrix Computation:
   - ADDED: If the Article ID does not exist in the remote OpenAI store, it is treated as a new document and injected into the pipeline.
   - UPDATED: If the Article ID exists but the embedded Unix_Updated_Timestamp differs from the fresh Zendesk payload, the stale cloud file is cleanly purged via API and replaced with the updated content.
   - SKIPPED: If both the ID and timestamp match identically, the document is safely bypassed within milliseconds, saving API costs and network overhead.
This architectural choice guarantees 100% stateless compliance, data persistence, and sub-second delta evaluations on production cloud networks.
# Support Knowledge Automation Pipeline

This project is an automated data-sync system designed to maintain an AI-powered Support Assistant (**OptiBot**). It fetches customer support documentation via Zendesk APIs, normalizes rich HTML text into semantic Markdown, and programmatically updates an OpenAI Vector Store.

---

## 📋 Features

- **Delta Scraping Engine:** Detects updates via Zendesk timestamps to ensure only modified articles are re-uploaded.
- **Stateful Remote Logging:** Execution logs are dynamically intercepted and pushed to the repository via GitHub API.
- **Automated AI Assistant Provisioning:** Configures OpenAI Assistants (GPT-4o) and connects File Search resources programmatically.

---

## 🛠️ Chunking Strategy

To maintain semantic data structures, we feed the raw converted Markdown files directly into OpenAI's **File Search tool**:

- **Chunk Size:** OpenAI handles splitting at 800 tokens per chunk.
- **Context Preservation:** Markdown headers (`#`, `##`, `###`) are intentionally preserved during the scraping phase, allowing the vector embedding model to easily detect logical boundaries and contextual relationships.

---

## 🚀 Local Installation & Setup

### 1. Prerequisites

Ensure you have Python 3.11+ installed.

### 2. Install Dependencies

```
pip install -r requirements.txt
```

### 3. Environment Setup

Create a .env file in the root directory based on your .env-example:

```
API_KEY=sk-proj-your-openai-api-key
```

Optional for logs saving:
GITHUB_TOKEN=your-github-personal-access-token
GITHUB_REPO=username/your-cryptic-repo-name

### 4. Execute Pipeline

```
python main.py
```

# 🐳 Docker Containerization

To package and run the engine locally inside an isolated runtime environment:

# 1. Build the image

```
docker build -t optisigns-sync-job .
```

# 2. Run the container once (it will execute main.py and exit 0)

```
docker run -e API_KEY="sk-proj-your-openai-api-key" optisigns-sync-job
```

## ☁️ Cloud Deployment (Railway)

This sync job is successfully containerized and deployed on **Railway** as a Daily Cron Job.

- **Schedule:** Runs automatically once per day (`0 1 * * *`).
- **Mechanism:** Railway builds the application via the provided `Dockerfile` and injects `API_KEY` and GitHub credentials via platform environment variables.
- **Logs:** Runtime artifacts are securely pushed back to the `logs/` directory of this repository via the GitHub REST API.

## 📊 Artifacts & Daily Logs

The cron job automatically commits its execution summary directly to this repository.

- **View Job Logs (Artifacts):** [Click here to view the /logs directory](https://github.com/sonnnguyen3301/support-ai-chatbot/tree/main/logs)

_(Each file contains the exact Delta Sync counts: Added, Updated, and Skipped)._

## 📸 Proof of Execution

### 1. Cloud Cron Job (Railway)

![Deployment Status Dashboard](static\Deploy_build.png)

![Execution Logs](static\Deploy_logs.png)

### 2. Assistant Sanity Check

![Assistant Sanity Check](static\How_do_i_add_a_youtube_video.png)

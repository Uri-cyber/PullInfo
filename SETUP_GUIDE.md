# Content Monitor - Complete Setup Guide

This guide will walk you through setting up the Content Monitor system from scratch.

## Step 1: Prerequisites

Before you begin, ensure you have:

- Python 3.10 or higher installed
- pip package manager
- Git (for cloning the repository)
- Text editor or IDE
- Anthropic Claude API key (sign up at https://console.anthropic.com)
- Make.com account (optional, for workflow automation)

## Step 2: Installation

### 2.1 Clone or Download the Repository

```bash
git clone https://github.com/Uri-cyber/PullInfo.git
cd PullInfo
```

### 2.2 Create Virtual Environment

**On Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 2.3 Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 3: API Keys Setup

### 3.1 Get Anthropic Claude API Key

1. Go to https://console.anthropic.com
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (starts with `sk-ant-...`)

### 3.2 Get Make.com API Key (Optional)

1. Log in to Make.com
2. Go to Profile → API
3. Generate API token
4. Copy the token

### 3.3 Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your favorite editor
nano .env  # or vim, code, etc.
```

Add your keys:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
MAKE_API_KEY=your-make-api-key-here
LOG_LEVEL=INFO
```

## Step 4: Configure Sources

### 4.1 Edit Sources Configuration

```bash
nano config/sources.json
```

Example RSS source:
```json
{
  "sources": [
    {
      "source_id": "hacker_news",
      "type": "rss",
      "url": "https://news.ycombinator.com/rss",
      "check_interval": 3600,
      "enabled": true,
      "priority": "medium",
      "description": "Hacker News RSS feed"
    }
  ]
}
```

### 4.2 Configure Claude Settings

```bash
nano config/claude.json
```

Adjust cost limits and prompt templates as needed.

### 4.3 Configure Make.com (Optional)

If using Make.com integration:

```bash
nano config/makecom.json
```

Add your webhook URLs from Make.com scenarios.

## Step 5: Initial Validation

### 5.1 Validate Configuration

```bash
python main.py config
```

This will check:
- Environment variables are set
- API keys are valid
- Configuration files are correct
- All dependencies are installed

### 5.2 Test a Source

```bash
python main.py test --source hacker_news
```

This will:
- Extract content from the source
- Show sample output
- Verify the extractor works

## Step 6: First Run

### 6.1 Manual Test Run

```bash
python main.py run
```

This performs a complete cycle:
1. Extracts from all enabled sources
2. Generates summaries
3. Sends to Make.com (if configured)
4. Shows statistics

### 6.2 Review Results

Check the logs:
```bash
cat logs/content_monitor.log
```

Check the database:
```bash
python main.py report --days 1
```

## Step 7: Scheduling (Optional)

### 7.1 Run with Built-in Scheduler

```bash
python main.py schedule
```

This will:
- Monitor sources at configured intervals
- Run daily/weekly tasks
- Continue until you press Ctrl+C

### 7.2 Use System Scheduler (Production)

**On Linux (cron):**
```bash
# Edit crontab
crontab -e

# Add line to run every hour
0 * * * * cd /path/to/PullInfo && /path/to/venv/bin/python main.py run >> logs/cron.log 2>&1
```

**On Windows (Task Scheduler):**
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., hourly)
4. Set action: Start a program
5. Program: `C:\path\to\venv\Scripts\python.exe`
6. Arguments: `main.py run`
7. Start in: `C:\path\to\PullInfo`

## Step 8: Make.com Integration Setup

### 8.1 Create Scenario in Make.com

1. Log in to Make.com
2. Create new scenario
3. Add "Webhooks" → "Custom webhook" as first module
4. Copy the webhook URL
5. Add other modules (e.g., send to Slack, save to Google Sheets)
6. Save and activate scenario

### 8.2 Add Webhook to Configuration

Edit `config/makecom.json`:
```json
{
  "scenarios": [
    {
      "scenario_id": "my-scenario-1",
      "name": "Content to Slack",
      "webhook_url": "https://hook.us1.make.com/your-webhook-url",
      "enabled": true,
      "content_types": ["rss", "web"]
    }
  ]
}
```

### 8.3 Test Integration

```bash
python main.py run
```

Check Make.com scenario execution history.

## Step 9: Monitoring and Maintenance

### 9.1 Daily Monitoring

Check costs:
```bash
python main.py costs --days 1
```

View activity:
```bash
python main.py report --days 1
```

### 9.2 Weekly Maintenance

Review logs:
```bash
ls -lh logs/
```

Clean up old cache (automatically done by scheduler):
```bash
# Manual cleanup if needed
python -c "from src.database import DatabaseManager; db = DatabaseManager(); db.cleanup_old_cache(30)"
```

### 9.3 Monthly Review

Analyze costs:
```bash
python main.py costs --days 30
```

Review and adjust:
- Source check intervals
- Summary styles
- Cost limits

## Step 10: Troubleshooting

### Common Issues

**Issue: "Module not found"**
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

**Issue: High costs**
```bash
# Check usage
python main.py costs --days 7

# Adjust settings in config/claude.json:
# - Reduce max_tokens
# - Lower daily_limit_usd
# - Use "quick_summary" style
```

**Issue: No content extracted**
```bash
# Test source individually
python main.py test --source your_source_id

# Check source is enabled in config/sources.json
# Verify URL is accessible
```

**Issue: Database errors**
```bash
# Reset database (WARNING: deletes all cached data)
rm cache/content_monitor.db
python main.py config  # Reinitializes database
```

### Getting Help

1. Check logs: `logs/content_monitor.log` and `logs/errors.log`
2. Run config validation: `python main.py config`
3. Test individual components: `python main.py test --source <id>`
4. Check GitHub issues: https://github.com/Uri-cyber/PullInfo/issues

## Advanced Configuration

### Custom Extractors

To add support for new content sources:

1. Create new file: `src/extractors/custom_extractor.py`
2. Inherit from `BaseExtractor`
3. Implement required methods
4. Add to `src/extractors/__init__.py`
5. Use in `config/sources.json` with type: "custom"

### Custom Summary Styles

Add to `config/claude.json`:
```json
{
  "prompt_templates": {
    "executive_summary": {
      "system": "You are an executive assistant.",
      "user": "Create an executive summary:\n\n{content}",
      "max_tokens": 300
    }
  }
}
```

Use with:
```bash
python main.py summarize --url https://example.com --style executive_summary
```

### Gmail Integration

1. Go to Google Cloud Console
2. Enable Gmail API
3. Create OAuth 2.0 credentials
4. Download credentials.json
5. Save to `config/gmail_credentials.json`
6. Set in .env: `GMAIL_CREDENTIALS_PATH=./config/gmail_credentials.json`
7. Enable email sources in `config/sources.json`

## Production Deployment

### Using systemd (Linux)

1. Create service file:
```bash
sudo nano /etc/systemd/system/content-monitor.service
```

2. Add:
```ini
[Unit]
Description=Content Monitor Service
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/PullInfo
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python main.py schedule
Restart=always

[Install]
WantedBy=multi-user.target
```

3. Enable and start:
```bash
sudo systemctl enable content-monitor
sudo systemctl start content-monitor
sudo systemctl status content-monitor
```

### Using Docker (Optional)

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py", "schedule"]
```

Build and run:
```bash
docker build -t content-monitor .
docker run -d --name content-monitor -v $(pwd)/config:/app/config content-monitor
```

## Success Checklist

- [ ] Python 3.10+ installed
- [ ] Dependencies installed
- [ ] API keys configured
- [ ] Sources configured
- [ ] Configuration validated
- [ ] Test run completed
- [ ] Logs reviewed
- [ ] Scheduling set up (optional)
- [ ] Make.com integrated (optional)
- [ ] Monitoring in place

## Next Steps

1. Add more content sources to `config/sources.json`
2. Customize summary styles in `config/claude.json`
3. Create Make.com scenarios for automation
4. Set up monitoring dashboards
5. Configure alerts for high costs or errors

---

**Need help?** Open an issue on GitHub or consult the main README.md

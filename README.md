# Content Monitor - Automated Content Monitoring & Summarization Bot

A comprehensive Python-based system that automatically monitors multiple content sources (RSS feeds, emails, web pages), generates AI-powered summaries using Claude API, and integrates with Make.com workflows for automation.

## Features

- **Multi-Source Content Extraction**
  - RSS/Atom feed monitoring
  - Gmail integration (optional)
  - Web page scraping
  - Customizable check intervals per source

- **AI-Powered Summarization**
  - Claude Sonnet 4 integration
  - Multiple summary styles (quick, detailed, key points, bilingual)
  - Token and cost tracking
  - Automatic caching to avoid duplicate processing

- **Make.com Integration**
  - Webhook-based workflow automation
  - Batch processing support
  - Configurable scenarios per content type
  - Data transformation for Make.com format

- **Content Processing**
  - HTML cleaning and text normalization
  - Language detection (English, Hebrew, mixed)
  - Keyword extraction
  - Priority assignment
  - Reading time estimation

- **Scheduling & Automation**
  - Flexible scheduling per source
  - Daily/weekly automated tasks
  - Priority-based processing
  - Background execution

- **Monitoring & Logging**
  - Comprehensive activity logging
  - Cost tracking and alerts
  - Performance metrics
  - SQLite-based caching and history

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager
- API keys: Anthropic Claude API, Make.com (optional)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/Uri-cyber/PullInfo.git
cd PullInfo
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

5. Configure sources:
```bash
# Edit config/sources.json to add your content sources
# Edit config/claude.json for Claude API settings
# Edit config/makecom.json for Make.com integration
```

## Configuration

### Environment Variables (.env)

```bash
# Required
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional
MAKE_API_KEY=your_make_api_key_here
GMAIL_CREDENTIALS_PATH=./config/gmail_credentials.json
LOG_LEVEL=INFO
```

### Sources Configuration (config/sources.json)

Define your content sources:

```json
{
  "sources": [
    {
      "source_id": "tech_rss",
      "type": "rss",
      "url": "https://example.com/feed.xml",
      "check_interval": 3600,
      "enabled": true,
      "priority": "high"
    }
  ]
}
```

### Claude Configuration (config/claude.json)

Configure AI summarization:

```json
{
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 4096,
  "temperature": 0.7,
  "cost_limits": {
    "daily_limit_usd": 5.0,
    "monthly_limit_usd": 100.0
  }
}
```

## Usage

### Basic Commands

**Run full monitoring cycle:**
```bash
python main.py run
```

**Test a specific source:**
```bash
python main.py test --source tech_rss
```

**Generate activity report:**
```bash
python main.py report --days 7
```

**Show cost analysis:**
```bash
python main.py costs --days 30
```

**Summarize a URL manually:**
```bash
python main.py summarize --url https://example.com/article --style detailed_analysis
```

**Validate configuration:**
```bash
python main.py config
```

**Run with scheduler:**
```bash
python main.py schedule
```

### Command Details

#### `run`
Executes a complete monitoring cycle:
1. Extracts content from all enabled sources
2. Cleans and classifies content
3. Generates AI summaries
4. Sends to Make.com webhooks
5. Logs all activity and costs

#### `test --source=SOURCE_ID`
Tests a specific source extractor:
- Validates source configuration
- Performs dry-run extraction
- Shows sample output
- Optional: generates test summary

#### `report --days=N`
Generates activity report:
- Content processed count
- Summaries generated
- Total costs
- API usage statistics
- Error rates

#### `costs --days=N`
Detailed cost analysis:
- Current session costs
- Historical costs
- Daily/monthly limits
- Remaining budget
- Cost projections

#### `summarize --url=URL [--style=STYLE]`
Manual URL summarization:
- Extracts content from URL
- Generates immediate summary
- Shows token usage and cost
- No caching (one-time use)

#### `config`
Validates all configurations:
- Checks environment variables
- Validates API keys
- Tests Make.com connectivity
- Verifies source configurations

## Architecture

### Project Structure

```
PullInfo/
├── config/                 # Configuration files
│   ├── sources.json       # Content sources
│   ├── claude.json        # Claude API settings
│   └── makecom.json       # Make.com integration
├── src/                   # Source code
│   ├── extractors/        # Content extractors
│   │   ├── base_extractor.py
│   │   ├── rss_extractor.py
│   │   ├── web_extractor.py
│   │   └── email_extractor.py
│   ├── processors/        # Content processors
│   │   ├── content_cleaner.py
│   │   ├── content_classifier.py
│   │   └── batch_manager.py
│   ├── makecom/          # Make.com integration
│   │   ├── make_client.py
│   │   ├── webhook_handler.py
│   │   └── data_transformer.py
│   ├── claude_client.py  # Claude API client
│   ├── database.py       # SQLite database
│   ├── scheduler.py      # Task scheduling
│   └── logger.py         # Logging utilities
├── tests/                # Test files
├── logs/                 # Log files
├── cache/                # SQLite database
├── main.py               # CLI entry point
└── requirements.txt      # Dependencies
```

### Data Flow

1. **Extraction**: Sources → Extractors → Raw Content
2. **Processing**: Raw Content → Cleaner → Classifier → Structured Content
3. **Summarization**: Structured Content → Claude API → Summaries
4. **Integration**: Summaries → Data Transformer → Make.com Webhooks
5. **Storage**: All steps → SQLite Database → Logs

## Summary Styles

### Quick Summary (100 words)
Concise overview focusing on key points. Ideal for daily digests.

### Detailed Analysis (500 words)
Comprehensive analysis with themes, implications, and insights.

### Key Points
Bullet-point list of actionable items and important facts.

### Bilingual
Summaries in both Hebrew and English. Perfect for mixed-language content.

## Make.com Integration

### Setup

1. Create scenarios in Make.com
2. Get webhook URLs from each scenario
3. Add to `config/makecom.json`
4. Configure content type routing

### Data Format

Content sent to Make.com includes:
- Name (title)
- Description (body excerpt)
- URL
- Date
- Summary (if generated)
- Keywords
- Metadata

## Cost Management

### Automatic Tracking
- Real-time token counting
- Per-request cost calculation
- Daily/monthly limits
- Alert thresholds (80% by default)

### Cost Controls
- Automatic stop at limit
- Cost estimation before processing
- Historical cost analysis
- Budget projections

### Pricing (Approximate)
- Claude Sonnet 4: $3 per million input tokens, $15 per million output tokens
- Average summary: ~500 input tokens + ~200 output tokens = ~$0.005 per summary

## Scheduling

### Automatic Scheduling
Sources are automatically scheduled based on `check_interval` in configuration.

### Custom Schedules
```python
scheduler.add_daily_task("daily_report", report_function, "08:00")
scheduler.add_weekly_task("cleanup", cleanup_function, "sunday", "00:00")
scheduler.add_interval_task("quick_check", check_function, 30)  # Every 30 min
```

### Priority Processing
High-priority sources are processed first in each cycle.

## Caching

### Automatic Caching
- Content hash-based deduplication
- Prevents reprocessing same content
- Configurable TTL (Time To Live)
- Automatic cleanup of old cache

### Database Storage
- Content cache: Original content and metadata
- Summaries: Generated summaries with costs
- API logs: All API calls and responses
- Processing queue: Failed items for retry

## Troubleshooting

### Common Issues

**"ANTHROPIC_API_KEY not found"**
- Ensure `.env` file exists in project root
- Verify API key is set: `ANTHROPIC_API_KEY=sk-...`

**"Source not found"**
- Check `source_id` matches configuration
- Verify `config/sources.json` is valid JSON

**"Gmail credentials not found"**
- Gmail integration is optional
- Set `GMAIL_CREDENTIALS_PATH` or disable email sources

**High costs**
- Reduce `check_interval` for sources
- Use "quick_summary" style instead of "detailed_analysis"
- Adjust `daily_limit_usd` in `config/claude.json`

### Logging

Logs are stored in `logs/` directory:
- `content_monitor.log`: All activity
- `errors.log`: Errors only

Set log level in `.env`:
```bash
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Development

### Running Tests
```bash
pytest tests/ -v
```

### Code Style
```bash
black src/ main.py
flake8 src/ main.py
```

### Adding New Extractors

1. Create new file in `src/extractors/`
2. Inherit from `BaseExtractor`
3. Implement `fetch_content()` and `parse_content()`
4. Add to `src/extractors/__init__.py`

### Adding New Summary Styles

Edit `config/claude.json` and add to `prompt_templates`:

```json
{
  "custom_style": {
    "system": "Your system prompt",
    "user": "Your user prompt with {content} placeholder",
    "max_tokens": 1000
  }
}
```

## Security

- **API Keys**: Never commit `.env` file or credentials
- **Data Privacy**: Enable `ANONYMIZE_DATA=true` for sensitive content
- **Content Logging**: Disable with `ENABLE_CONTENT_LOGGING=false`
- **Rate Limiting**: Automatic rate limit handling
- **HTTPS**: All external communications use HTTPS

## Performance

### Optimization Tips
- Adjust `max_concurrent` in `config/sources.json`
- Use batch processing for multiple items
- Enable caching to avoid duplicate work
- Schedule during off-peak hours
- Use appropriate summary styles for use case

### Benchmarks (Typical)
- RSS extraction: ~2-5 seconds per feed
- Web scraping: ~3-8 seconds per page
- Summary generation: ~2-5 seconds per item
- Make.com webhook: ~1-2 seconds per item

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/Uri-cyber/PullInfo/issues
- Documentation: See docs/ folder
- Email: [Your contact email]

## Changelog

### Version 1.0.0 (2025-01-XX)
- Initial release
- Multi-source content extraction
- Claude API integration
- Make.com workflow automation
- Comprehensive monitoring and logging
- Flexible scheduling system

## Acknowledgments

- Anthropic for Claude API
- Make.com for workflow automation
- Open source community for excellent libraries

---

**Built with ❤️ for automated content monitoring**

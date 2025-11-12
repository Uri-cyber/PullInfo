# Known Issues and Workarounds

## Installation Issues

### feedparser Installation Error

**Issue**: When installing dependencies, you may encounter an error installing `feedparser` due to its dependency `sgmllib3k`:

```
ERROR: Failed building wheel for sgmllib3k
AttributeError: install_layout. Did you mean: 'install_platlib'?
```

**Cause**: This is a compatibility issue with `sgmllib3k` and newer versions of setuptools.

**Impact**: RSS feed extraction will not work, but all other features (Web extraction, Email extraction, Claude summarization, Make.com integration) will function normally.

**Workarounds**:

**Option 1: Skip feedparser (Recommended for quick start)**
- The system is designed to work without feedparser
- RSS extraction will be disabled with a warning message
- All other extractors (Web, Email) will work fine
- Simply skip installing feedparser and proceed

**Option 2: Install feedparser with workaround**
```bash
# Try installing with --no-cache-dir
pip install --no-cache-dir feedparser

# Or downgrade setuptools temporarily
pip install setuptools==67.8.0
pip install feedparser
pip install --upgrade setuptools
```

**Option 3: Use alternative RSS parsing**
- You can use the Web extractor for RSS feeds by treating them as regular web pages
- Many RSS feeds are also available as HTML pages

**Option 4: Docker installation**
- Use Docker to avoid environment issues
- The Dockerfile (if created) will handle dependencies correctly

## Runtime Issues

### Claude API "Invalid API Key"

**Issue**: Configuration validation passes but actual API calls fail with authentication errors.

**Cause**: Test validation doesn't make actual API calls.

**Solution**:
- Verify your API key is correct in `.env`
- Test with: `python main.py summarize --url https://example.com`
- Check your Anthropic account has sufficient credits

### Make.com Webhook Timeouts

**Issue**: Webhooks to Make.com time out or return errors.

**Cause**: Make.com scenario might be inactive or webhook URL is incorrect.

**Solution**:
- Verify scenario is active in Make.com
- Check webhook URL is correct in `config/makecom.json`
- Test webhook manually using curl:
  ```bash
  curl -X POST https://your-webhook-url \
    -H "Content-Type: application/json" \
    -d '{"test": "data"}'
  ```

### Gmail Integration Fails

**Issue**: Email extractor returns no results or authentication errors.

**Cause**: Gmail credentials not configured or OAuth flow not completed.

**Solution**:
- Gmail integration is optional - disable if not needed
- To enable:
  1. Set up Google Cloud project
  2. Enable Gmail API
  3. Download OAuth credentials
  4. Place in `config/gmail_credentials.json`
  5. Run once to complete OAuth flow

### Database Lock Errors

**Issue**: `database is locked` error when running scheduler.

**Cause**: Multiple processes trying to access SQLite database.

**Solution**:
- SQLite is single-writer
- Don't run multiple instances simultaneously
- For production, consider PostgreSQL (requires code modification)

### High Memory Usage

**Issue**: Process uses excessive memory with large batches.

**Cause**: Processing too many items at once.

**Solution**:
- Reduce `max_tokens` in BatchManager (currently 150,000)
- Process fewer sources simultaneously
- Adjust `max_concurrent` in `config/sources.json`

## Feature Limitations

### Language Detection Limitations

**Issue**: Language detection may be inaccurate for short texts or technical content.

**Cause**: Simple character-based detection.

**Workaround**:
- Manually specify language in source configuration (future feature)
- Use bilingual summary style for mixed content

### Cost Tracking Not Persistent

**Issue**: Cost tracking resets when application restarts.

**Cause**: Costs are tracked in-memory only.

**Solution**:
- Check database stats for historical costs: `python main.py report --days 30`
- API logs table contains all costs in database

### No Automatic Retry Queue

**Issue**: Failed items are not automatically retried.

**Current Behavior**: Errors are logged but items are skipped.

**Workaround**:
- Check logs for failed items
- Manually reprocess with `python main.py test --source <id>`
- Future update will add automatic retry queue

## Performance Issues

### Slow RSS Feed Parsing (when feedparser works)

**Issue**: Large RSS feeds take long to parse.

**Solution**:
- Feeds are cached - duplicates won't be reprocessed
- Increase `check_interval` for large feeds
- Consider fetching only recent items (requires custom filtering)

### Claude API Rate Limits

**Issue**: "Rate limit exceeded" errors from Claude API.

**Cause**: Too many requests in short time.

**Solution**:
- Anthropic Sonnet 4 has high rate limits
- If hit, wait 1 minute and retry
- Reduce number of sources or increase intervals
- System includes automatic retry with exponential backoff

## Configuration Issues

### Invalid JSON in Config Files

**Issue**: `JSONDecodeError` when loading configurations.

**Cause**: Syntax error in JSON file.

**Solution**:
- Validate JSON: `python -m json.tool config/sources.json`
- Check for trailing commas (not allowed in JSON)
- Ensure proper quote usage (double quotes only)

### Environment Variables Not Loaded

**Issue**: "API key not found" despite setting in `.env`.

**Cause**: `.env` file not in correct location or not loaded.

**Solution**:
- Ensure `.env` is in project root (same directory as `main.py`)
- Check file permissions (should be readable)
- Verify no typos in variable names
- Use absolute path if running from different directory

## Getting Help

If you encounter an issue not listed here:

1. **Check Logs**: `cat logs/content_monitor.log` and `logs/errors.log`
2. **Run Validation**: `python main.py config`
3. **Test Components**: Use `test` command to isolate issues
4. **Check GitHub Issues**: https://github.com/Uri-cyber/PullInfo/issues
5. **Enable Debug Logging**: Set `LOG_LEVEL=DEBUG` in `.env`

## Contributing Fixes

If you fix an issue, please:
1. Update this document
2. Add tests for the fix
3. Submit a pull request with clear description

## System Requirements

**Verified Working**:
- Python 3.10, 3.11
- Linux (Ubuntu 20.04+, Debian 11+)
- macOS 12+
- Windows 10+ (WSL recommended)

**Known Not Working**:
- Python 3.8 or earlier (uses newer type hints)
- Windows without WSL (path issues)

## Security Considerations

**API Keys**: Never commit `.env` or configuration files containing keys

**Rate Limiting**: System respects rate limits but doesn't enforce them proactively

**Content Logging**: Disable content logging for sensitive data:
```bash
ENABLE_CONTENT_LOGGING=false
```

**Database**: SQLite database contains cached content - secure appropriately

---

**Last Updated**: 2025-11-12
**Version**: 1.0.0

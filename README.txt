INTERNSHIP MONITORING BOT
========================

A Python bot that monitors software engineering internships across EU/UK from major tech companies and LinkedIn, sending consolidated updates via Telegram.

SETUP
-----
1. Install Python 3.12+
2. Create virtual environment: python -m venv venv
3. Activate: . venv/bin/activate (Linux/Mac) or venv\Scripts\activate (Windows)
4. Install dependencies: pip install -r requirements.txt
5. Copy .env.example to .env and fill in your Telegram credentials
6. Run: python internship_monitor.py

CONFIGURATION
-------------
Required:
- TELEGRAM_BOT_TOKEN: Get from @BotFather on Telegram
- TELEGRAM_CHAT_ID: Your chat ID (message your bot, then check /getUpdates)

Optional:
- REQUEST_TIMEOUT=30
- RATE_LIMIT_DELAY=2.0 
- MAX_RETRIES=3

FEATURES
--------
- Monitors: Apple, Microsoft, Google, Meta, Nvidia, Spotify, Palantir
- LinkedIn search via jobpilot library for additional companies
- Geographic coverage: All EU countries + UK
- Flexible keyword matching (intern, trainee, graduate, etc.)
- Comprehensive SWE role detection
- Single consolidated Telegram message per run
- Automatic rate limiting and error handling
- Cron job compatible

AUTOMATION
----------
Add to crontab for daily monitoring:
0 9 * * * cd /path/to/int2026-tel-bot && . venv/bin/activate && python internship_monitor.py

TROUBLESHOOTING
---------------
- Check .env file has correct Telegram credentials
- Ensure virtual environment is activated
- Check internship_monitor.log for detailed errors
- LinkedIn rate limits may cause temporary blocks

For issues: Check logs and verify network connectivity
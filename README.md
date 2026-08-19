# SBC24 Text Cleaner Bot

Telegram utility bot for cleaning text and removing duplicate lines.

## Features

- Clean whitespace and blank lines
- Remove common list numbering and bullets
- Remove duplicate lines case-insensitively
- Clean + deduplicate in one operation
- Text statistics
- Process plain `.txt` files up to 5 MB
- Copy-friendly Telegram output

## Run locally

1. Create a bot with `@BotFather` and copy its token.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set the environment variable:

```bash
export TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"
```

4. Start the bot:

```bash
python bot.py
```

## Commands

- `/start`
- `/help`
- `/clean`
- `/dedupe`
- `/both`
- `/stats`
- `/cancel`

## Security

Never commit your real Telegram bot token to GitHub. Store it in an environment variable or your hosting provider's secret manager.

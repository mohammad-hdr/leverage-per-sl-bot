# Leverage Calculator Telegram Bot

A secure Telegram bot that calculates the leverage needed to lose 100% of margin if the price hits a stop loss.

## Features

-   🔒 **Secure**: Webhook signature verification, input validation, session management
-   📊 **Accurate**: Precise leverage calculations with proper error handling
-   🧹 **Clean**: Automatic session cleanup and memory management
-   📱 **User-friendly**: Clear instructions and helpful error messages

## Security Features

-   ✅ Webhook signature verification
-   ✅ Input validation with bounds checking
-   ✅ Session timeout and cleanup
-   ✅ Environment variable configuration
-   ✅ Comprehensive error handling
-   ✅ Rate limiting protection

## Deployment on Render

### 1. Environment Variables Setup

In your Render dashboard, set these environment variables:

```
BOT_TOKEN=your_telegram_bot_token
WEBHOOK_SECRET=your_secure_webhook_secret
WEBHOOK_URL=https://your-app-name.onrender.com
DEBUG=False
```

### 2. Bot Token Setup

1. Create a bot with [@BotFather](https://t.me/botfather)
2. Get your bot token
3. Set it as `BOT_TOKEN` in Render

### 3. Webhook Configuration

The bot automatically sets up the webhook on startup. Make sure your `WEBHOOK_URL` points to your Render app URL.

## Local Development

### Prerequisites

-   Python 3.8+
-   Telegram Bot Token

### Setup

1. Clone the repository
2. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Set environment variables:

    ```bash
    export BOT_TOKEN="your_bot_token"
    export WEBHOOK_SECRET="your_secret"
    export WEBHOOK_URL="https://your-domain.com"
    export DEBUG="True"
    ```

4. Run the bot:
    ```bash
    python bot.py
    ```

## Usage

1. Start the bot with `/start`
2. Enter your entry price in USDT
3. Enter your stop loss price in USDT
4. Enter your margin amount in USDT
5. Get your leverage calculation

## API Endpoints

-   `GET /` - Health check
-   `GET /health` - Detailed health status
-   `POST /{webhook_secret}` - Telegram webhook endpoint

## Security Considerations

### ✅ Implemented

-   Webhook signature verification
-   Input validation and sanitization
-   Session management with timeouts
-   Environment variable configuration
-   Comprehensive error handling

### ⚠️ Additional Recommendations

-   Use HTTPS in production
-   Implement rate limiting
-   Add monitoring and alerting
-   Regular security audits
-   Keep dependencies updated

## Error Handling

The bot handles various error scenarios:

-   Invalid input validation
-   Division by zero protection
-   Session expiration
-   API failures
-   Network issues

## Performance Optimizations

-   Automatic session cleanup
-   Efficient memory usage
-   Minimal API calls
-   Structured logging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Disclaimer

This bot is for educational purposes only. Trading with leverage involves significant risk. Always do your own research and consider consulting with financial advisors before making trading decisions.

import os
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from flask import Flask, request, abort
from telegram import Update, Bot
import hmac
import hashlib

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# Configuration
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    # Validation
    if not all([BOT_TOKEN, WEBHOOK_SECRET, WEBHOOK_URL]):
        raise ValueError("Missing required environment variables")


# Data structures
@dataclass
class UserData:
    entry_price: float
    stop_loss: float
    margin: float
    timestamp: datetime


class UserState:
    def __init__(self):
        self._states: Dict[int, str] = {}
        self._data: Dict[int, UserData] = {}
        self._timestamps: Dict[int, datetime] = {}
        self._cleanup_interval = timedelta(hours=1)
        self._last_cleanup = datetime.now()

    def set_state(self, chat_id: int, state: str) -> None:
        self._states[chat_id] = state
        self._timestamps[chat_id] = datetime.now()

    def get_state(self, chat_id: int) -> Optional[str]:
        return self._states.get(chat_id)

    def set_data(self, chat_id: int, data: UserData) -> None:
        self._data[chat_id] = data

    def get_data(self, chat_id: int) -> Optional[UserData]:
        return self._data.get(chat_id)

    def clear_user(self, chat_id: int) -> None:
        self._states.pop(chat_id, None)
        self._data.pop(chat_id, None)
        self._timestamps.pop(chat_id, None)

    def cleanup_old_sessions(self) -> None:
        """Remove sessions older than 1 hour"""
        now = datetime.now()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        expired_chats = [
            chat_id
            for chat_id, timestamp in self._timestamps.items()
            if now - timestamp > timedelta(hours=1)
        ]

        for chat_id in expired_chats:
            self.clear_user(chat_id)
            logger.info(f"Cleaned up expired session for chat_id: {chat_id}")

        self._last_cleanup = now


# Input validation
def validate_number(
    text: str, min_value: float = 0.01, max_value: float = 1000000
) -> Optional[float]:
    """Validate and convert string to float with bounds checking"""
    try:
        value = float(text)
        if value <= min_value or value > max_value:
            return None
        return value
    except ValueError:
        return None


def calculate_leverage(entry_price: float, stop_loss: float) -> Tuple[float, float]:
    """Calculate leverage and percentage difference"""
    if entry_price == 0:
        raise ValueError("Entry price cannot be zero")

    diff = abs(stop_loss - entry_price)
    if diff == 0:
        raise ValueError("Entry price and stop loss cannot be the same")

    percentage_diff = (diff / entry_price) * 100
    leverage = 100 / percentage_diff

    return round(percentage_diff, 2), round(leverage, 2)


# Webhook signature verification
def verify_webhook_signature(request_data: bytes, signature: str) -> bool:
    """Verify Telegram webhook signature"""
    if not signature:
        return False

    secret_key = Config.WEBHOOK_SECRET.encode()
    expected_signature = hmac.new(secret_key, request_data, hashlib.sha256).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


# Initialize Flask app and user state
app = Flask(__name__)
user_state = UserState()
bot = Bot(token=Config.BOT_TOKEN)


@app.route(f"/{Config.WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    """Handle incoming webhook from Telegram"""
    try:
        # Verify webhook signature
        signature = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if not verify_webhook_signature(request.data, signature):
            logger.warning("Invalid webhook signature")
            abort(403)

        # Parse update
        update = Update.de_json(request.get_json(force=True), bot)

        if not update.message or not update.message.text:
            return "ok"

        chat_id = update.message.chat.id
        text = update.message.text.strip()

        # Cleanup old sessions periodically
        user_state.cleanup_old_sessions()

        # Handle commands
        if text == "/start":
            handle_start(chat_id)
        elif text == "/help":
            handle_help(chat_id)
        else:
            handle_message(chat_id, text)

        return "ok"

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return "error", 500


def handle_start(chat_id: int) -> None:
    """Handle /start command"""
    try:
        bot.send_message(
            chat_id,
            "🚀 Welcome to the Leverage Calculator!\n\n"
            "I'll help you calculate the leverage needed to lose 100% of your margin "
            "if the price hits your stop loss.\n\n"
            "📥 Please enter your Entry Price (USDT):",
        )
        user_state.set_state(chat_id, "entry")
    except Exception as e:
        logger.error(f"Error in handle_start: {e}")


def handle_help(chat_id: int) -> None:
    """Handle /help command"""
    try:
        help_text = (
            "📚 **How to use this bot:**\n\n"
            "1. Use /start to begin a new calculation\n"
            "2. Enter your entry price in USDT\n"
            "3. Enter your stop loss price in USDT\n"
            "4. Enter your margin amount in USDT\n\n"
            "The bot will calculate:\n"
            "• Percentage distance to stop loss\n"
            "• Required leverage to lose 100% of margin\n\n"
        )
        bot.send_message(chat_id, help_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in handle_help: {e}")


def handle_message(chat_id: int, text: str) -> None:
    """Handle incoming messages based on user state"""
    try:
        state = user_state.get_state(chat_id)

        if not state:
            bot.send_message(chat_id, "Use /start to begin or /help for instructions.")
            return

        if state == "entry":
            handle_entry_price(chat_id, text)
        elif state == "sl":
            handle_stop_loss(chat_id, text)
        elif state == "margin":
            handle_margin(chat_id, text)

    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        bot.send_message(chat_id, "❌ An error occurred. Please try /start again.")


def handle_entry_price(chat_id: int, text: str) -> None:
    """Handle entry price input"""
    entry_price = validate_number(text)

    if entry_price is None:
        bot.send_message(
            chat_id, "⛔ Please enter a valid number between 0.01 and 1,000,000 USDT."
        )
        return

    user_data = UserData(
        entry_price=entry_price, stop_loss=0.0, margin=0.0, timestamp=datetime.now()
    )
    user_state.set_data(chat_id, user_data)
    user_state.set_state(chat_id, "sl")

    bot.send_message(chat_id, "📉 Please enter your Stop Loss (USDT):")


def handle_stop_loss(chat_id: int, text: str) -> None:
    """Handle stop loss input"""
    stop_loss = validate_number(text)

    if stop_loss is None:
        bot.send_message(
            chat_id, "⛔ Please enter a valid number between 0.01 and 1,000,000 USDT."
        )
        return

    user_data = user_state.get_data(chat_id)
    if not user_data:
        bot.send_message(chat_id, "❌ Session expired. Please use /start again.")
        user_state.clear_user(chat_id)
        return

    user_data.stop_loss = stop_loss
    user_state.set_state(chat_id, "margin")

    bot.send_message(chat_id, "💵 Please enter your margin amount in USDT:")


def handle_margin(chat_id: int, text: str) -> None:
    """Handle margin input and calculate results"""
    margin = validate_number(text)

    if margin is None:
        bot.send_message(
            chat_id, "⛔ Please enter a valid number between 0.01 and 1,000,000 USDT."
        )
        return

    user_data = user_state.get_data(chat_id)
    if not user_data:
        bot.send_message(chat_id, "❌ Session expired. Please use /start again.")
        user_state.clear_user(chat_id)
        return

    user_data.margin = margin

    try:
        # Calculate results
        percentage_diff, leverage = calculate_leverage(
            user_data.entry_price, user_data.stop_loss
        )

        # Format message
        message = (
            f"📊 **Calculation Results:**\n\n"
            f"📥 Entry Price: {user_data.entry_price:,.2f} USDT\n"
            f"📉 Stop Loss: {user_data.stop_loss:,.2f} USDT\n"
            f"💰 Margin: {user_data.margin:,.2f} USDT\n\n"
            f"🔻 Distance to SL: {percentage_diff}%\n"
            f"📈 Required Leverage: {leverage}x\n\n"
            f"⚠️ **Risk Warning:** Using {leverage}x leverage means your margin "
            f"will be completely lost if the price reaches {user_data.stop_loss:,.2f} USDT.\n\n"
            f"💡 Use /start for a new calculation"
        )

        bot.send_message(chat_id, message, parse_mode="Markdown")

    except ValueError as e:
        bot.send_message(chat_id, f"❌ Calculation error: {str(e)}")
    except Exception as e:
        logger.error(f"Error in calculation: {e}")
        bot.send_message(chat_id, "❌ An error occurred during calculation.")
    finally:
        # Clear user session
        user_state.clear_user(chat_id)


@app.route("/")
def index():
    """Health check endpoint"""
    return "Bot is running and healthy! 🚀"


@app.route("/health")
def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(user_state._states),
    }


def setup_webhook():
    """Setup webhook with error handling"""
    try:
        # Delete existing webhook
        bot.delete_webhook()

        # Set new webhook
        webhook_url = f"{Config.WEBHOOK_URL}/{Config.WEBHOOK_SECRET}"
        success = bot.set_webhook(webhook_url)

        if success:
            logger.info(f"Webhook set successfully: {webhook_url}")
        else:
            logger.error("Failed to set webhook")

    except Exception as e:
        logger.error(f"Error setting up webhook: {e}")


# Initialize webhook on startup
if __name__ == "__main__":
    setup_webhook()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=Config.DEBUG, host="0.0.0.0", port=port)

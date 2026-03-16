# config.py - Smart Money Divergence Detector
# Fill in your keys below, then run: python detector.py

# -- Telegram --
# Step 1: Message @BotFather on Telegram -> /newbot -> copy the token
# Step 2: Message your bot once, then visit:
#         https://api.telegram.org/bot<TOKEN>/getUpdates
# Step 3: Find "id" inside "chat" - that is your Chat ID
TELEGRAM_BOT_TOKEN = "8700001711:AAFjIfzem9flIBcSmkTlbFgNrom5JlNu8NM"
TELEGRAM_CHAT_ID   = "822161264"

# -- Chains to Monitor --
# Available: ethereum, solana, base, bnb, arbitrum, polygon, optimism
CHAINS = ["ethereum", "solana", "base"]

# -- Filters --
MIN_SMART_MONEY_TRADERS = 3

# -- Output --
TOP_N_RESULTS = 10
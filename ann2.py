from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import re

# === Configuration ===
BOT_TOKEN = "7911037262:AAG1H5Rf_cUwUhNKMzCFDKqK2E0Np4w4VrQ"  # Replace with your bot token
GROUP_USERNAME = "@tvhwdgfygeg"  # Replace with your group username

# In-memory user matching
waiting_users = set()
active_chats = {}

# Custom reply keyboard
keyboard = ReplyKeyboardMarkup([
    ["Start Chat", "Next"],
    ["Share Profile", "Stop"]
], resize_keyboard=True)

# Check group membership
async def is_user_joined_group(user_id, context):
    try:
        member = await context.bot.get_chat_member(GROUP_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_user_joined_group(user_id, context):
        join_button = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔗 Join Group", url=f"https://t.me/{GROUP_USERNAME.lstrip('@')}"),
        ]])
        await update.message.reply_text(
            "🚫 You must join our group to use the bot.",
            reply_markup=join_button
        )
        return

    await update.message.reply_text(
        "👋 Welcome to Anonymous Chat Bot!\n\n"
        "🧑‍🤝‍🧑 Chat with strangers anonymously.\n"
        "▶ Press 'Start Chat' to begin.",
        reply_markup=keyboard
    )

# Handle user input
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if not await is_user_joined_group(user_id, context):
        join_button = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔗 Join Group", url=f"https://t.me/{GROUP_USERNAME.lstrip('@')}"),
        ]])
        await update.message.reply_text(
            "🚫 Please join our group to use the bot.",
            reply_markup=join_button
        )
        return

    if text == "Start Chat":
        if user_id in active_chats:
            await update.message.reply_text("⚠️ You are already in a chat. Press 'Stop' or 'Next'.")
            return

        if user_id in waiting_users:
            await update.message.reply_text("⏳ Still waiting for a partner...")
            return

        if waiting_users:
            partner_id = waiting_users.pop()
            if partner_id == user_id:
                waiting_users.add(partner_id)
                await update.message.reply_text("⏳ Still waiting for a partner...")
                return

            active_chats[user_id] = partner_id
            active_chats[partner_id] = user_id
            await context.bot.send_message(partner_id, "✅ You are now connected to a stranger!")
            await update.message.reply_text("✅ You are now connected to a stranger!")
        else:
            waiting_users.add(user_id)
            await update.message.reply_text("⏳ Waiting for a partner...")

    elif text == "Next":
        await disconnect_user(user_id, context, notify=True)
        if waiting_users:
            partner_id = waiting_users.pop()
            if partner_id == user_id:
                waiting_users.add(partner_id)
                await update.message.reply_text("⏳ Still waiting for a new partner...")
                return

            active_chats[user_id] = partner_id
            active_chats[partner_id] = user_id
            await context.bot.send_message(partner_id, "✅ New stranger connected!")
            await update.message.reply_text("✅ New stranger connected!")
        else:
            waiting_users.add(user_id)
            await update.message.reply_text("⏳ Waiting for a new partner...")

    elif text == "Stop":
        await disconnect_user(user_id, context, notify=True)

    elif text == "Share Profile":
        if user_id in active_chats:
            partner_id = active_chats[user_id]
            user = update.effective_user

            if user.username:
                profile_link = f"@{user.username}"
            else:
                profile_link = f"[{user.first_name}](tg://user?id={user.id})"

            await context.bot.send_message(
                partner_id,
                f"👤 Your partner has shared their profile: {profile_link}",
                parse_mode="Markdown"
            )
            await update.message.reply_text("✅ Your profile has been shared.")
        else:
            await update.message.reply_text("⚠️ You're not in a chat.")

    else:
        if user_id in active_chats:
            partner_id = active_chats[user_id]

            # Block URLs and usernames
            if re.search(r"(https?://|www\.)\S+", text.lower()) or re.search(r"@\w+", text):
                await update.message.reply_text("⚠️ You are not allowed to send links or usernames.")
                return

            if partner_id in active_chats:
                await context.bot.send_message(partner_id, text)
            else:
                await update.message.reply_text("⚠️ Your partner left the chat.")
                await disconnect_user(user_id, context, notify=True)
        else:
            await update.message.reply_text("❗ You're not in a chat. Use 'Start Chat' to connect.")

# Disconnect helper
async def disconnect_user(user_id: int, context: ContextTypes.DEFAULT_TYPE, notify=False):
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        if notify:
            await context.bot.send_message(partner_id, "❌ Stranger has left the chat.")
            await context.bot.send_message(user_id, "🛑 You left the chat.")
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        if notify:
            await context.bot.send_message(user_id, "🛑 Removed from waiting queue.")
    else:
        if notify:
            await context.bot.send_message(user_id, "⚠️ You're not in any chat or queue.")

# Main
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Anonymous Chat Bot is running...")
    app.run_polling()

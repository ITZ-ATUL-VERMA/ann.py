from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import re

# === Configuration ===
BOT_TOKEN = "8126685057:AAGFOyrQDZZUhFfWBzTRlawK7IxJL2Ur_4Q"
GROUP_USERNAME = "@omegle_chat1"
OWNER_ID = 5674660386 # Replace with your Telegram numeric ID

# In-memory databases
waiting_users = set()
active_chats = {}
all_users = set()  # ✅ Track all unique users who started the bot

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
    all_users.add(user_id)  # Add user to all_users when they start the bot

    if not await is_user_joined_group(user_id, context):
        join_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Join Group", url=f"https://t.me/{GROUP_USERNAME.lstrip('@')}")]
        ])
        await update.message.reply_text("🚫 You must join our group to use the bot.", reply_markup=join_button)
        return

    await update.message.reply_text(
        "👋 Welcome to Anonymous Chat Bot!\n\n"
        "🧑‍🤝‍🧑 Chat with strangers anonymously.\n"
        "▶ Press 'Start Chat' to begin.",
        reply_markup=keyboard
    )

# /broadcast (owner only)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Usage: /broadcast Your message here")
        return

    # Debugging line to print arguments
    print("Broadcast Message:", " ".join(context.args))

    message = "📢 Broadcast:\n" + " ".join(context.args)
    count = 0
    for user_id in all_users:
        try:
            await context.bot.send_message(user_id, message)
            count += 1
        except Exception as e:
            print(f"Error sending message to {user_id}: {e}")
            continue

    await update.message.reply_text(f"✅ Broadcast sent to {count} users.")

# /users command (owner only) to see the total number of users
async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return

    total_users = len(all_users)
    await update.message.reply_text(f"👥 Total users who have interacted with the bot: {total_users}")

# Handle user input
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    all_users.add(user_id)  # Add user to all_users when they start the bot
    text = update.message.text.strip()

    if not await is_user_joined_group(user_id, context):
        join_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Join Group", url=f"https://t.me/{GROUP_USERNAME.lstrip('@')}")]
        ])
        await update.message.reply_text("🚫 Please join our group to use the bot.", reply_markup=join_button)
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

                # 👁️ Send monitoring copy to owner with linkable ID
                sender = update.effective_user
                sender_link = f"[{sender.first_name}](tg://user?id={sender.id})"
                await context.bot.send_message(
                    OWNER_ID,
                    f"📩 New Message:\n"
                    f"👤 From: {sender_link} (`{sender.id}`)\n"
                    f"👤 To: `{partner_id}`\n"
                    f"💬 Message: {text}",
                    parse_mode="Markdown"
                )
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
    app.add_handler(CommandHandler("broadcast", broadcast))  # ✅ Owner broadcast command
    app.add_handler(CommandHandler("users", users))  # ✅ Owner users command
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Anonymous Chat Bot is running...")
    app.run_polling()

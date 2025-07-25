#!/usr/bin/env python3

"""
A simple Telegram bot that reminds the user 10 minutes and 5 minutes
before a long-running Claude session ends.

The bot responds to the ``/start_session`` command with a single
argument specifying the total length of your Claude session in minutes.
For example, ``/start_session 30`` will set up a 30‑minute timer and
schedule reminders at the 20‑minute and 25‑minute mark, corresponding
to 10 and 5 minutes remaining. When the session finishes the bot sends
an end‑of‑session message.

This bot uses python‑telegram‑bot v20+ and its built‑in job queue to
schedule reminders. When run on Render as a worker service the bot
polls Telegram for updates and executes scheduled jobs.

To deploy this bot you must provide the ``TELEGRAM_BOT_TOKEN``
environment variable. On Render you can add this as an environment
variable in the dashboard. Locally you can set it in your shell.

Usage:
    python main.py

Commands:
    /start - show a welcome message and basic usage
    /start_session <minutes> - begin a session of the specified length

"""

import logging
import os
from typing import Optional

from telegram import Update
from telegram.ext import (ApplicationBuilder, CommandHandler,
                          ContextTypes, JobQueue)


# Read the bot token from the environment. You must set this in
# Render or your local environment for the bot to authenticate.
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")


def _validate_minutes(text: str) -> Optional[int]:
    """Attempt to convert a string argument into a positive integer.

    Returns None if the argument is invalid.
    """
    try:
        minutes = int(text)
    except ValueError:
        return None
    return minutes if minutes > 0 else None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command and display usage instructions."""
    message = (
        "שלום! אני בוט התראה לזמן כתיבת Claude.\n\n"
        "השתמש ב־/start_session <מספר דקות> כדי להתחיל מעקב אחר שיחה.\n"
        "לדוגמה: /start_session 30 יתחיל ספירה לאחור של 30 דקות,"
        " עם התראות כאשר נותרו 10 ו־5 דקות."
    )
    await update.message.reply_text(message)


async def start_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start a new session and schedule reminders for 10 and 5 minutes remaining."""
    chat_id = update.effective_chat.id
    args = context.args

    if not args:
        await update.message.reply_text(
            "עליך לציין את אורך השיחה בדקות. לדוגמה: /start_session 20"
        )
        return

    total_minutes = _validate_minutes(args[0])
    if total_minutes is None:
        await update.message.reply_text(
            "המספר שסיפקת אינו חוקי. אנא הזן מספר שלם חיובי המייצג דקות."
        )
        return

    # Cancel any existing jobs for this chat
    if "sessions" not in context.chat_data:
        context.chat_data["sessions"] = {}
    session_jobs = context.chat_data["sessions"].get(chat_id)
    if session_jobs:
        for job in session_jobs:
            job.schedule_removal()

    job_queue: JobQueue = context.job_queue

    # Helper function to schedule a reminder
    def schedule_reminder(minutes_left: int):
        # Only schedule if the session length exceeds the reminder offset
        if total_minutes > minutes_left:
            due_seconds = (total_minutes - minutes_left) * 60
            return job_queue.run_once(
                send_reminder,
                when=due_seconds,
                chat_id=chat_id,
                data={"minutes_left": minutes_left, "total": total_minutes},
                name=f"reminder_{minutes_left}_{chat_id}"
            )
        return None

    # Schedule 10- and 5-minute reminders
    job_10 = schedule_reminder(10)
    job_5 = schedule_reminder(5)

    # Schedule end-of-session message
    job_end = job_queue.run_once(
        send_session_end,
        when=total_minutes * 60,
        chat_id=chat_id,
        data={"total": total_minutes},
        name=f"session_end_{chat_id}"
    )

    # Store jobs so they can be cancelled on a new /start_session
    context.chat_data["sessions"][chat_id] = [job for job in (job_10, job_5, job_end) if job]

    # Confirm to the user
    await update.message.reply_text(
        f"התחלתי מעקב של {total_minutes} דקות. אשלח התראה כאשר יישארו 10 ו־5 דקות."
    )


async def send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a reminder message when a scheduled job triggers."""
    job = context.job
    minutes_left = job.data.get("minutes_left")
    total = job.data.get("total")
    if minutes_left and total:
        await context.bot.send_message(
            chat_id=job.chat_id,
            text=(
                f"⚠️ נשארו {minutes_left} דקות לשיחה שלך עם Claude (מתוך {total} דקות)."
            ),
        )


async def send_session_end(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Notify the user that the session has ended."""
    job = context.job
    total = job.data.get("total")
    await context.bot.send_message(
        chat_id=job.chat_id,
        text=(
            f"⏰ הזמן של השיחה עם Claude הסתיים לאחר {total} דקות. תקבע זמן חדש עם /start_session."
        ),
    )


def main() -> None:
    """Entry point: set up the bot and begin polling."""
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "Missing TELEGRAM_BOT_TOKEN environment variable. Please set it to your bot token."
        )

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("start_session", start_session))

    # Run the bot until Ctrl-C is pressed
    application.run_polling()


if __name__ == "__main__":
    main()

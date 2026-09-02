"""Generate TELEGRAM_SESSION string for Pyrogram user account.

Usage:
  set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env, then:
  python scripts/gen_user_session.py
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()


async def main() -> None:
    api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
    api_hash = os.getenv("TELEGRAM_API_HASH", "")
    if not api_id or not api_hash:
        print("Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env")
        sys.exit(1)

    from pyrogram import Client

    app = Client("profilemark_session_gen", api_id=api_id, api_hash=api_hash)
    async with app:
        session = await app.export_session_string()
    print("\nAdd to .env:\n")
    print(f"TELEGRAM_SESSION={session}")


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import collections
import json
import os
import re

import bottom
from dotenv import load_dotenv

from lib import get_client, new_chat

load_dotenv()

HOST = os.getenv("IRC_HOST")
assert HOST, "IRC_HOST is required"
PORT = int(os.getenv("IRC_PORT") or 6667)
NICK = os.getenv("NICK") or "caibot"
PASSWORD = os.getenv("PASSWORD") or None
CHANNELS = json.loads(os.getenv("CHANNELS") or "[]")
CHAR = os.getenv("CHAR")
CHAT_ID = os.getenv("CHAT_ID")

assert CHAR, "CHAR is required"
assert CHAT_ID, "CHAT_ID is required"


class Python310Client(bottom.Client):
    def __init__(
        self,
        host: str,
        port: int,
        *,
        encoding: str = "utf-8",
        ssl: bool = True,
        loop: asyncio.AbstractEventLoop | None = None
    ) -> None:
        """Fix 3.10 error"""
        super().__init__(host, port, encoding=encoding, ssl=ssl, loop=loop)
        self._events = collections.defaultdict(lambda: asyncio.Event())


bot = bottom.Client(HOST, PORT, ssl=False)


# @bot.regex_cmd_with_messsage(rf"(?i)^((?:.*\s)?{NICK}([\s|,|\.|\;|\?|!|:]*)(?:\s.*)?)$", False)
# async def mention(bot: IrcBot, args: re.Match, message: Message):
#     text = args[1].strip()
#     nick = message.sender_nick
#     answer = await trio_asyncio.aio_as_trio(reply)(text)
#     return f"{nick}: {answer}"


# async def reply(text: str) -> str:
#     async with new_chat(CHAT_ID) as (new, answer, conn):
#         anwer = await conn.send_message(CHAR, new.chat_id, text)
#     return answer.text


@bot.on("PING")
def keepalive(message, **kwargs):
    bot.send("PONG", message=message)


@bot.on("CLIENT_CONNECT")
async def connet(**kwargs):
    await get_client()

    bot.send("NICK", nick=NICK)
    bot.send("USER", user=NICK, realname=NICK)

    # Don't try to join channels until the server has
    # sent the MOTD, or signaled that there's no MOTD.
    done, pending = await asyncio.wait(
        [bot.wait("RPL_ENDOFMOTD"), bot.wait("ERR_NOMOTD")], return_when=asyncio.FIRST_COMPLETED
    )

    # Cancel whichever waiter's event didn't come in.
    for future in pending:
        future.cancel()

    for channel in CHANNELS:
        bot.send("JOIN", channel=channel)

    async with new_chat(CHAT_ID) as (new, answer, conn):
        for channel in CHANNELS:
            bot.send("PRIVMSG", target=channel, message=answer.text)


if __name__ == "__main__":
    bot.loop.create_task(bot.connect())
    bot.loop.run_forever()

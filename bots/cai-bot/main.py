import asyncio
import json
import os
import re

import trio_asyncio
from dotenv import load_dotenv
from IrcBot.bot import IrcBot, Message, utils
from PyCAI2 import PyAsyncCAI2

load_dotenv()

HOST = os.getenv("HOST")
assert HOST, "HOST is required"

PORT = int(os.getenv("PORT") or 6667)
NICK = os.getenv("NICK") or "caibot"
PASSWORD = os.getenv("PASSWORD") or None
CHANNELS = json.loads(os.getenv("CHANNELS") or "[]")
OWNER_ID = os.getenv("OWNER_ID")
AUTHOR = os.getenv("AUTHOR")
assert AUTHOR, "AUTHOR is required"

AUTHOR_ID = os.getenv("AUTHOR_ID")
CHAR = os.getenv("CHAR")
CHAT_ID = os.getenv("CHAT_ID")

aut_set = {
    "author_id": AUTHOR_ID,  # CREATOR ID
    "is_human": True,  # PLEASE DON'T WRITE TO FALSE
    "name": "YOU:",  # YOUR CAI NAME
}


client = PyAsyncCAI2(OWNER_ID)  # IMPORT OWNER ID


@utils.regex_cmd_with_messsage(rf"(?i)^((?:.*\s)?{NICK}([\s|,|\.|\;|\?|!|:]*)(?:\s.*)?)$", False)
async def mention(bot: IrcBot, args: re.Match, message: Message):
    text = args[1].strip()
    last = args[2] if args[2] else ""
    text.replace(f" {NICK}{last}", " ")
    nick = message.sender_nick
    answer = await trio_asyncio.aio_as_trio(reply)(text)
    return f"{nick}: {answer}"


async def reply(text: str) -> str:
    async with client.connect(OWNER_ID) as chat2:  # Make a connection to the server
        r = await chat2.send_message(CHAR, text, AUTHOR, Return_name=False)  # ALL VARIABLES WILL BE SENT TO SERVER
    return r


async def onConnect(bot: IrcBot):
    for channel in CHANNELS:
        await bot.join(channel)
    await bot.send_message("Hello everyone !!!")


async def repl_loop():
    message = input("You:")  # INPUT TEXT
    async with client.connect(OWNER_ID) as chat2:  # Make a connection to the server
        r = await chat2.send_message(CHAR, message, AUTHOR, Return_name=True)  # ALL VARIABLES WILL BE SENT TO SERVER
        print(r)


# Useful in case we need testing locally
def repl():
    while True:
        asyncio.run(repl_loop())


if __name__ == "__main__":
    # repl()
    bot = IrcBot(HOST, PORT, NICK, CHANNELS, PASSWORD)
    bot.runWithCallback(onConnect)

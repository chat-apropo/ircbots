import json
import logging
import os
import re
from dataclasses import dataclass, field
from multiprocessing import Process

from characterai.types.other import QueryChar
from dotenv import load_dotenv
from ircbot import IrcBot, Message, utils

from lib import get_client, new_chat, open_chat

load_dotenv()

HOST = os.getenv("IRC_HOST")
assert HOST, "IRC_HOST is required"
PORT = int(os.getenv("IRC_PORT") or 6667)
NICK = os.getenv("NICK") or "caibot"
PASSWORD = os.getenv("PASSWORD") or None
CHANNELS = json.loads(os.getenv("CHANNELS") or "[]")
CHAR = os.getenv("CHAR")
CHAT_ID = os.getenv("CHAT_ID")

MAX_SEARCH_RESULTS = 3
MAX_CHARACTERS = 3

assert CHAR, "CHAR is required"
assert CHAT_ID, "CHAT_ID is required"


@dataclass
class UserData:
    search_results: list[QueryChar]
    shown_results: list[QueryChar]


@dataclass
class ChannelData:
    users: dict[str, UserData] = field(default_factory=dict)
    children: dict[str, Process] = field(default_factory=dict)


@dataclass
class BotData:
    channels: dict[str, ChannelData] = field(default_factory=dict)


class CustomBot(IrcBot):
    data: BotData = field(default_factory=BotData)


def irc_sanitize_nick(s: str) -> str:
    return s.replace(" ", "_").replace("-", "_").replace(".", "_").replace("#", "_").casefold()


bot = CustomBot(HOST, PORT, NICK, CHANNELS, PASSWORD)
utils.set_loglevel(logging.DEBUG)
bot.set_prefix("+")


def install_conversation_hooks(mybot: IrcBot, nick: str = NICK, char: str = CHAR, chat_id: str = CHAT_ID):
    @mybot.regex_cmd_with_messsage(rf"(?i)^((?:.*\s)?{nick}([\s|,|\.|\;|\?|!|:]*)(?:\s.*)?)$", False)
    async def mention(args: re.Match, message: Message):
        text = args[1].strip()
        nick = message.sender_nick
        async with open_chat() as conn:
            answer = await conn.send_message(char, chat_id, text)
        return f"{nick}: {answer.text}"


def add_character_to_channel(channel: str, nick: str, char: QueryChar):
    new_bot = CustomBot(HOST, PORT, nick, channel)

    async def get_char():
        await new_bot.join(channel)
        async with new_chat(char.external_id) as (new, answer, conn):
            await new_bot.send_message(f"{answer.name}: {answer.text}")
            install_conversation_hooks(new_bot, nick=new_bot.nick, char=char.external_id, chat_id=new.chat_id)
            bot._install_hooks()

    new_bot.run_with_callback(get_char)


def get_search_results_lines(message: Message, search_results: list[QueryChar]) -> list[str]:
    lines = []
    user_data = bot.data.channels[message.channel].users.get(message.sender_nick)
    if not user_data:
        return ["No search results available"]
    for i, char in enumerate(search_results):
        lines.append(f"{i+1}) \x02{char.participant__name}\x02 {char.title} ({char.greeting})")
        user_data.shown_results.append(char)
        del search_results[i]
        if i == MAX_SEARCH_RESULTS - 1:
            break
    return lines


@bot.arg_command("search", "Search for a character", "search <query>")
async def search(args: re.Match, message: Message):
    client = await get_client()
    query = "+".join(utils.m2list(args))
    search_results = await client.search(query)
    bot.data.channels[message.channel].users[message.sender_nick] = UserData(
        search_results=search_results, shown_results=[]
    )
    return get_search_results_lines(message, search_results)


@bot.arg_command("more", "Get more search results", "more")
async def more(args: re.Match, message: Message):
    user_data = bot.data.channels[message.channel].users.get(message.sender_nick)
    if not user_data:
        return "No search results available"
    search_results = bot.data.channels[message.channel].users[message.sender_nick].search_results
    if not search_results:
        return "No search results available"
    return get_search_results_lines(message, search_results)


@bot.arg_command("add", "Add a character to the conversation", "add <number>")
async def add(args: re.Match, message: Message):
    user_data = bot.data.channels[message.channel].users.get(message.sender_nick)
    if not user_data:
        return "No search results available"
    if not user_data.search_results:
        return "No search results available"

    if len(bot.data.channels[message.channel].children) >= MAX_CHARACTERS:
        return "Maximum number of characters reached"

    if not args[1].isdigit():
        return "Invalid number"

    number = int(args[1])
    if number < 1 or number - 1 > len(user_data.shown_results):
        return "Invalid number"

    char = user_data.shown_results[number - 1]
    nick = irc_sanitize_nick(char.participant__name)
    process = Process(target=add_character_to_channel, args=(message.channel, nick, char))
    process.start()
    bot.data.channels[message.channel].children[nick] = process


@bot.arg_command("del", "Remove a character from the conversation", "del <nick>")
async def delete(args: re.Match, message: Message):
    if args[1] not in bot.data.channels[message.channel].children:
        return f"Character '{args[1]}' not found"

    bot.data.channels[message.channel].children[args[1]].terminate()


async def on_connect():
    bot.data = BotData(channels={})
    await get_client()
    for channel in CHANNELS:
        await bot.join(channel)
        bot.data.channels[channel] = ChannelData()
    await bot.send_message("Hello everyone !!!")


if __name__ == "__main__":
    install_conversation_hooks(bot)
    bot.run_with_callback(on_connect)

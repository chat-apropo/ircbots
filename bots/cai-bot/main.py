import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from multiprocessing import Process

from characterai.types.other import QueryChar
from dotenv import load_dotenv
from ircbot import IrcBot, Message, utils

from lib import ClientWrapper, get_token

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
    token: str
    client: ClientWrapper
    channels: dict[str, ChannelData] = field(default_factory=dict)


class CustomBot(IrcBot):
    _data: BotData

    @property
    def data(self) -> BotData:
        return self._data

    @data.setter
    def data(self, value: BotData):
        self._data = value


def irc_sanitize_nick(s: str) -> str:
    return s.replace(" ", "_").replace("-", "_").replace(".", "_").replace("#", "_").casefold()


bot = CustomBot(HOST, PORT, NICK, CHANNELS, PASSWORD)
utils.set_loglevel(logging.INFO)
bot.set_prefix("+")


def install_conversation_hooks(mybot: CustomBot, nick: str = NICK, char: str = CHAR, chat_id: str = CHAT_ID):
    @mybot.regex_cmd_with_messsage(rf"(?i)^((?:.*\s)?{nick}([\s|,|\.|\;|\?|!|:]*)(?:\s.*)?)$", False)
    async def mention(args: re.Match, message: Message):
        text = args[1].strip()
        async with mybot.data.client.open_chat() as conn:
            answer = await conn.send_message(char, chat_id, text)
        lines = []
        for part in answer.text.split("\n"):
            lines.extend(utils.split_in_lines(part))
        await mybot.reply(message, lines)


def add_character_to_channel(token: str, channel: str, nick: str, char: QueryChar):
    new_bot = CustomBot(HOST, PORT, nick, channel)
    new_bot.data = BotData(channels={}, token=token, client=ClientWrapper(token))

    async def get_char():
        await new_bot.join(channel)
        async with new_bot.data.client.new_chat(char.external_id) as (new, answer, conn):
            await new_bot.send_message(answer.text)
            install_conversation_hooks(new_bot, nick=new_bot.nick, char=char.external_id, chat_id=new.chat_id)
            bot.install_hooks()

    new_bot.run_with_callback(get_char)


def get_search_results_lines(message: Message, search_results: list[QueryChar]) -> list[str]:
    lines = []
    user_data = bot.data.channels[message.channel].users.get(message.sender_nick)
    if not user_data or len(search_results) == 0:
        return ["No search results available"]
    for i, char in enumerate(search_results):
        lines.append(f"{i+1}) \x02{char.participant__name}\x02 {char.title} ({char.greeting})")
        user_data.shown_results.append(char)
        del search_results[i]
        if i == MAX_SEARCH_RESULTS - 1:
            break
    return [utils.truncate(line, 400) for line in lines]


@bot.arg_command("search", "Search for a character", "search <query>")
async def search(args: re.Match, message: Message):
    client = bot.data.client
    query = "+".join(utils.m2list(args))
    search_results = await client.aiocai.search(query)
    bot.data.channels[message.channel].users[message.sender_nick] = UserData(
        search_results=search_results, shown_results=[]
    )
    await bot.reply(message, get_search_results_lines(message, search_results))


@bot.arg_command("more", "Get more search results", "more")
async def more(args: re.Match, message: Message):
    user_data = bot.data.channels[message.channel].users.get(message.sender_nick)
    if not user_data:
        await bot.reply(message, "No search results available")
        return
    search_results = bot.data.channels[message.channel].users[message.sender_nick].search_results
    if not search_results or len(search_results) == 0:
        await bot.reply(message, "No search results available")
        return
    await bot.reply(message, get_search_results_lines(message, search_results))


@bot.arg_command("add", "Add a character to the conversation", "add <number>")
async def add(args: re.Match, message: Message):
    user_data = bot.data.channels[message.channel].users.get(message.sender_nick)
    if user_data is None:
        await bot.reply(message, "No search results available")
        return

    if not user_data.search_results:
        await bot.reply(message, "No search results available")
        return

    if len(bot.data.channels[message.channel].children) >= MAX_CHARACTERS:
        await bot.reply(message, "Maximum number of characters reached")
        return

    if not args[1].isdigit():
        await bot.reply(message, "Invalid number")
        return

    number = int(args[1])
    if number < 1 or number - 1 > len(user_data.shown_results):
        await bot.reply(message, "Invalid number")
        return

    char = user_data.shown_results[number - 1]
    nick = irc_sanitize_nick(char.participant__name)
    process = Process(target=add_character_to_channel, args=(bot.data.token, message.channel, nick, char), daemon=True)
    process.start()
    bot.data.channels[message.channel].children[nick] = process


async def kill_process(process: Process):
    process.terminate()
    await asyncio.sleep(0.5)
    if process.is_alive() and process.pid:
        os.kill(process.pid, 9)


@bot.arg_command("delete", "Remove a character from the conversation", "del <nick>", alias="remove")
async def delete(args: re.Match, message: Message):
    if args[1] not in bot.data.channels[message.channel].children:
        await bot.reply(message, f"Character '{args[1]}' not found")
        return

    process: Process = bot.data.channels[message.channel].children[args[1]]
    await kill_process(process)


@bot.arg_command("restart", "Remove all characters from the conversation", "wipeout")
async def wipeout(args: re.Match, message: Message):
    for nick, process in bot.data.channels[message.channel].children.items():
        await kill_process(process)
    bot.data.channels[message.channel].children = {}
    await bot.reply(message, "All characters removed")


async def on_connect():
    token = await get_token()
    bot.data = BotData(channels={}, token=token, client=ClientWrapper(token))

    for channel in CHANNELS:
        await bot.join(channel)
        bot.data.channels[channel] = ChannelData()

    await bot.send_message("Hello everyone !!!")


if __name__ == "__main__":
    install_conversation_hooks(bot)
    bot.run_with_callback(on_connect)

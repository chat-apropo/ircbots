# Simple echo bot example with random color echo because why not
from IrcBot.bot import IrcBot, utils, Color
import requests
import json

headers = {
    'accept': 'application/json',
    'Content-Type': 'application/json',
}

params = {
    'model': 'gpt-4-turbo',
}

# TODO: make the command the or provider argument like the old gpt bot did

@utils.arg_command("echo")
def echo(args, message):
    json_data = {
        'messages': [
            {
                'role': 'user',
                'content':  " ".join(utils.m2list(args)),
            },
        ],
    }
    request = requests.post('https://g4f-api.fly.dev/api/completions', params=params, headers=headers, json=json_data).json()
    completion = request["completion"]
    return request["completion"]

async def onConnect(bot: IrcBot):
    await bot.join("#bots")

if __name__ == "__main__":
    bot = IrcBot("irc.dot.org.es", nick="ThePrototype")
    bot.runWithCallback(onConnect)


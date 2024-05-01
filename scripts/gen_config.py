# Description: Generate a global config file for all bots
import json
from pathlib import Path

from dotenv import dotenv_values

global_config = {}

bots = Path("bots").glob("*/.env.example")
for bot in bots:
    env = dotenv_values(bot, interpolate=True)
    global_config[f"bots/{bot.parent.name}"] = dict(env)

print(json.dumps(global_config, indent=2))

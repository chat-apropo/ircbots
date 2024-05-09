from ircbot import IrcBot, Message, utils
import lib
import pprint
from google.cloud import bigquery

bot = (
    IrcBot("irc.dot.org.es", nick="bigquery", channels=["#bots"])
    .set_prefix("bq")
    .set_max_arguments(99999)
    .set_simplify_commands(False)
)  

query_dict = {}
@bot.arg_command("run")
def run(args, message):
    query = " ".join(utils.m2list(args))
    try:
        json = lib.query(query)
    except Exception:
        return "Will exceed 2GB limit"
    return pprint.pformat(json)
if __name__ == "__main__":
    bot.run()

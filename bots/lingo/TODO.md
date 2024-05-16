# Language learning bot
A bot to rule them all. Not really, but it will help you learn a new language.

Scroll to the bottom for the most important part.

## User Story
As a user, I am a lazy fuck who cannot practice a language with another humans and don't really want to learn a new language at all. I am already a good listener but
not a good writer or speaker so I need to practice that. This bot will interact with the user without being requested to do so, forcing one to join conversation and to
have automatic nazi grammar friendly corrections for everything that is said!

I want to register with the bot and with the language I want to learn, and once I register I can remove myself from it. The bot will randomly come up with some subject
speaking only in the learning_language and whatever input it gets from me it will correct the spelling and grammar. From time to time it does that and also always acts 
like a normal bot but having custom responses in their own prefered languages for each user.

I want it to be possible to reduce the amount of messages or the chance of getting from this bot if it gets too spammy or even set it to 0 to turn it off.


## Features
This is basically a bot in reverse. That requires interaction and spam users instead of waiting for them to ask for something.

- [ ] Register with the bot
- [ ] Unregister with the bot
- [ ] Only speaks in the learning language of the user. Maybe you have to inject in every prompt f"Repond in {language}: {user_input}". The bot acts like a normal gpt bot when mentioned.
- [ ] Automatically Correct spelling and grammar of the user input. You can query good gpt models with something like "Correct the grammar sentence in {language} of '{user_input}'"
- [ ] Randomly interact with each of the users from time to time.
- [ ] Control level or spam. Would be nice if this this happened independently for each user.
- [ ] Keep the track of history in memory at least (not in DB), so the bot knows what we are talking about. That also means there must be a command
to clear the history of a user that you can only use for your own data.

Do not worry about prompt injection for now. That is ok.

### Extras (+50)
- [ ] Randomize if the bot does a DM or a public message. Maybe a 50% chance of each.
- [ ] Scoring system. Compute a score of how close the correction and user input was. Maybe use the https://pypi.org/project/python-Levenshtein/ to compute the distance between the two strings.
- [ ] Reward system. AI waifus? Custom prompt for each user? Idk but something to make it fun. Maybe steal this code https://github.com/chat-apropo/CloudBot/blob/main/plugins/huggingface.py
- [ ] Message persistence. Store all interactions with each user. Keep the context forever respecting the API and AI limits, which means not forever but for a long time.


## Technical Requirements

### IRC
Use the latest dev version of re-ircbot.
When you are pushing to this branch the bots wont be automatically deployed to the IRC so chill out and keep things up to date here.
Lets interact with the bot using `f"{NICK}: "` as a prefix. We cannot have more prefixes for bots anymore.
### Filling forms:
ReplyIntents are your friends. Look at flirtbot for reference: https://github.com/matheusfillipe/ircbot/blob/v2/examples/flirtbot.py

### Triggering random interactions
This is a tricky part. We dont want to talk to all users at the same time. You need to store the last interaction time for each user at least in the DB. Then every minute
run a check with the spam chance of triggering a message for each user. If the user has a spam chance of 0, do not trigger a message. If the user has a spam chance of 100
it will happen every minute. But don't do it at the exact minute, do a `asyncio.sleep(random.randint(0, 60))` before sending it so it is completely random.

This lib comes to mind: https://schedule.readthedocs.io/en/stable/

But I think that is not needed. Just make a `on_start` like:
```python

async def on_start():
    while True:
        await asyncio.sleep(60)
        for user in get_all_users():
            if user.spam_level > random.randint(0, 100):
                target = random.choice([user.name] + bot.channels)
                await bot.send_message(channel, "Hello there!")
```
Remember that with async sleeping means you are giving time for the bot and runtime to do other things and breath.

### Data persistence
This bot stores user data and it will need a database for this. Since we are using coolify and cloudbots, I will introduce a postgres instance to coolify.

You can make the db public in https://cloud.mattf.one/project/akgssgs/production/database/v08ssg0#general "Make it publicly available". Do not leave that on forever
so remember to uncheck it, just in case.

For db exploration I recommend pgcli:
```bash
pip install pgcli

# Wil only work when it is public
pgcli -U lingo -h 168.138.71.130 -p 5432
```
https://www.pgcli.com/commands


DM asking me the password for lingo.
The user and database are called `lingo`.

We should use [sqlalchemy 2](https://pypi.org/project/SQLAlchemy/) for this. It will also need [psycopg2](https://pypi.org/project/psycopg2-binary/) Don't be scared, here is an example of what we need:

```python
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String
from sqlalchemy.orm import sessionmaker

url = URL.create(
    drivername="postgresql",
    username="lingo",
    host="cloud.mattf.one",
    database="lingo"
)

engine = create_engine(url)

# To create a table
Base = declarative_base(metadata=metadata)

class User(Base):
    id: int = Column(Integer, primary_key=True)
    name: str = Column(String)
    learning_language: str = Column(String)
    spam_level: int = Column(Integer)

# Save all messages with the bot
class UserInteraction(Base):
    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(Integer)
    message: str = Column(String)
    corrected_message: str = Column(String)


metadata = Base.metadata

# To create the table
def create_table():
    metadata.create_all(engine)

# To insert a user
def insert_user(name: str, learning_language: str):
    session = sessionmaker(bind=engine)()
    user = User(name=name, learning_language=learning_language)
    session.add(user)
    session.commit()

# To get a user by name
def get_user(name: str) -> User:
    session = sessionmaker(bind=engine)()
    return session.query(User).filter(User.name == name).first()
```

Not tested but that should be almost it.


### AI
Our gf4 API is still fucked up and finished. Having it is a must for this bot. It is already usable but not reliable. The url has changed to:
https://g4f.cloud.mattf.one/docs
Something like the gptbot in this repo. https://github.com/chat-apropo/ircbots/tree/main/bots/gptbot

Btw instead of requests, to be async (meaning you let the bot do other things while a request doesn't arrive) maybe better use httpx:
https://www.python-httpx.org/

```python
import httpx

async def some_async_handler():
    async with httpx.AsyncClient() as client:
        json_data = {
            "messages": [
                {
                    "role": "user",
                    "content": " ".join(utils.m2list(args)),
                },
            ],
        }
        request = await client.post(
            url, params=params, headers=headers, json=json_data
        ).json()
        completion = request["completion"]
        client.post
```
Again make this a separate testable client thing.

### Code
Keep the code uncoupled. Maybe for this we need more than a `lib.py`. Probably a `gpt_client.py`, `tranlator.py`, `spellcheck.py`, `corrector.py`, `db.py`, idk 
just don't put everythin inside the IRC hook function.

Think about it like this, things will be wrong and will break. Can we test each of the things individually in a `if __name__ == "__main__":` block
for each individual peace of funtionality so we can test each one of them separately without having to test it over IRC. This is almost doing actual
tests but we are too lazy for that so we wont.

Keep the pattern of `main.py`, `Requirements.txt` as the other bots here.

Make sure all configuration like database stuff, api url, anything is using dotenv and has a .env.example.

## How to approach it

So here is how I recommend you to do all this:

0. First of all it is AI age so just give this file to chatgpt or gpt engineer and it will do everything for you and that is ok, you will still
need to get it actually working.

1. Figure out the AI client first. Remember to make all code async. You can test it with a simple `if __name__ == "__main__":` block. Write a repl like:
```python
import asyncio
# Code here for doing ai requests, maybe a Client class

async def main():
    client = AI()
    while True:
        user_input = input("You: ")
        correction = await client.correct_message(user_input)
        response = await client.send_message(user_input)
        print(f"Bot: {correction}")
        print(f"Bot: {response}")
        

if __name__ == "__main__":
    asyncio.run(main())
```
There you will have to figure out how to wrap the AI requests and get the AI to always respond in the learning language of the user, and also to correct.
Don't worry about it not being perfect. AI means that it is all fucked up.

2. Figure out keeping history. Use as reference: https://github.com/chat-apropo/ircbots/blob/main/bots/g4firc/main.py#L175-L179
I think the API works the same way. So yeah is just keeping a global state. Make it so the repl does it first:

```python
import asyncio
# Code here for doing ai requests, maybe a Client class and Message

async def main():
    client = AI()
    history = []
    while True:
        user_input = input("You: ")
        history.append(Message(role="user", content=user_input))
        correction = await client.correct_message(user_input)
        response = await client.get_completion(history)
        print(f"Bot: {correction}")
        print(f"Bot: {response}")
        history.appendMessage(role="bot", content=response))
        

if __name__ == "__main__":
    asyncio.run(main())
```

Maybe AI is stupid and refuses to respond in the proper language. You could use the google translate detect language before sending it to the user, so that 
we are sure. As reference from translatebot: https://github.com/matheusfillipe/ircbot/blob/main/examples/translator.py#L115

It uses this lib: https://py-googletrans.readthedocs.io/en/latest/

In case the response lang is wrong you can just translate it back to the user language. It is not perfect but it is something. Remember the point of the bot
is more to annoy the user than to actually help them learn a language. The learning is happening only on trying to come up with my own words.

3. Figure out the database. The example code in the Technical Requirements part should be enough to get you started. You will need to dump the bad tables
so expect using pgcli and doing some sql. https://www.postgresql.org/docs/current/index.html
Basically:
```sql
DROP TABLE users;
DROP TABLE messages;

-- See everything
SELECT * FROM users;

-- Insert a user
INSERT INTO users (name, learning_language, spam_level) VALUES ('loudercake', 'pt', 50);
```

In the bot we wont write queries like that but use the ORM so that this doesn't happen: https://xkcd.com/327/

Basically we need to store users and messages wouln't be so hard. Create functions for that and also encapsulate that.

4. Figure out the random triggering logic. Test this locally, don't torture yourself through IRC. It can be tricky to simulate that but we don't need it perfect.

5. If you have all that, then you can finally worry about the IRC part. Just copy the new echobot https://github.com/matheusfillipe/ircbot/blob/v2/examples/echobot.py
You will need to use some ReplyIntents in DM for register and unregister. You can do:
```python
await bot.send_message("Hey smelly nerd", "mattf") # To send a DM
```

There is also these new things I added to the lib:

```python
from ircbot.format import format_line_breaks, markdown_to_irc
@bot.some_whatever_deco_with_msg("asdfasdfsd")
async def some_hook(args, message: Message):
    text = m2list(args)
    response = some_ai_function(text)
    lines = format_line_breaks(markdown_to_irc(resposne)) # This will format the response to be IRC friendly, multiple lines
    await bot.reply(message, lines) # Prepend the nick to all lines
```

To make the lines DM's `[Message(channel=message.nick, message=line) for line in lines]` and to make it public `[Message(channel=message.channel, message=line) for line in lines]`.

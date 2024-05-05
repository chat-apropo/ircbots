import asyncio
import logging
import os
import poplib
from contextlib import asynccontextmanager
from email.parser import Parser
from typing import AsyncIterator
from urllib.parse import quote

from async_lru import alru_cache
from bs4 import BeautifulSoup
from characterai import aiocai, authUser, sendCode
from characterai.aiocai.client import WSConnect
from characterai.types.chat2 import BotAnswer, ChatData
from dotenv import load_dotenv

load_dotenv()

POP3_SERVER = os.getenv("POP3_SERVER")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
PASSWORD = os.getenv("PASSWORD")
assert POP3_SERVER, "POP3_SERVER is required"
assert EMAIL_ADDRESS, "EMAIL_ADDRESS is required"
assert PASSWORD, "PASSWORD is required"


def get_token_from_email():
    pop_conn = poplib.POP3_SSL(POP3_SERVER)
    pop_conn.user(EMAIL_ADDRESS)
    pop_conn.pass_(PASSWORD)

    # Get the latest email
    num_messages = len(pop_conn.list()[1])
    response, raw_messages, octets = pop_conn.retr(num_messages)
    raw_message = b"\n".join(raw_messages)

    # Parse the email
    email_parser = Parser()
    msg = email_parser.parsestr(raw_message.decode("utf-8"))
    # subject = msg["subject"]

    url = None
    # Iterate over the parts of the email
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            html_content = part.get_payload(decode=True).decode(part.get_content_charset())
            soup = BeautifulSoup(html_content, "html.parser")
            links = soup.find_all("a")

            for link in links:
                url = link.get("href")

    pop_conn.quit()
    return url


@alru_cache
async def get_client() -> aiocai.Client:
    sendCode(EMAIL_ADDRESS)
    await asyncio.sleep(5)
    url = get_token_from_email()
    if not url:
        raise ValueError("Could not get token from email")

    token = authUser(url, EMAIL_ADDRESS)
    logging.info(f"Got token: {token}")
    return aiocai.Client(token=token)


async def refresh_client() -> aiocai.Client:
    # drop cache for get_client
    get_client.cache_clear()
    return await get_client()


@asynccontextmanager
async def new_chat(char_id: str) -> AsyncIterator[tuple[ChatData, BotAnswer, WSConnect]]:
    client = await get_client()
    me = await client.get_me()
    async with await client.connect() as conn:
        new, answer = await conn.new_chat(char_id, str(me.id))
        yield new, answer, conn


@asynccontextmanager
async def open_chat() -> AsyncIterator[WSConnect]:
    client = await get_client()
    async with await client.connect() as conn:
        yield conn


async def main():
    """REPL for testing"""
    client = await get_client()
    me = await client.get_me()
    print(me)

    c = await client.search(quote("jesus"))
    char = c[0]
    print(f"{char.title} ({char.greeting}) - {char.external_id}")
    print(f"{char.title} ({char.greeting}) - {char.external_id}")

    async with new_chat(char.external_id) as (new, answer, conn):
        print(f"{answer.name}: {answer.text}")
        for i in range(3):
            text = input("YOU: ")
            message = await conn.send_message(char.external_id, new.chat_id, text)
            print(f"{message.name}: {message.text}")

    c = await client.search(quote("elon"))
    char = c[0]
    print(f"{char.title} ({char.greeting}) - {char.external_id}")
    async with new_chat(char.external_id) as (new, answer, conn):
        print(f"{answer.name}: {answer.text}")
        while True:
            text = input("YOU: ")
            message = await conn.send_message(char.external_id, new.chat_id, text)
            print(f"{message.name}: {message.text}")


if __name__ == "__main__":
    asyncio.run(main())

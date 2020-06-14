import logging
from itertools import groupby
from db import db_notes, db_users, db_chats
from config import REQUEST_TIMEOUT_S, bot, BOT_UIN
from pyaspeller import Word
from const import Const
import functools
import pendulum
import asyncio
import aiohttp
import json


loop = asyncio.get_event_loop()
log = logging.getLogger(__name__)

default_tz = "Europe/Moscow"


def get_offset(timezone=default_tz):
    return int(pendulum.now(timezone).offset_hours * 60 * -1)


async def markup_dusi_request(text):
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_S),
        headers={"User-agent": bot.user_agent},
    ) as session:
        async with session.get(
            url="http://markup.dusi.mobi/api/text",
            ssl=False,
            params={"text": text, "offset": get_offset()},
        ) as response:
            text = await response.text()
            log.debug(text)
            return json.loads(text)


def is_group(event):
    return "@chat.agent" in event.data["chat"]["chatId"]


def exists_mention(event):
    return bool(
        "parts" in event.data
        and [
            p
            for p in event.data["parts"]
            if p["type"] == "mention" and p["payload"]["userId"] == BOT_UIN
        ]
    )


def speller(text):
    correct = text
    try:
        for word in set(text.split(" ")):
            if len(word) >= 2:
                check = Word(word)
                if not check.correct and check.spellsafe:
                    correct = text.replace(word, check.spellsafe)
    except Exception:
        pass
    finally:
        return correct


def short_text(text, length=100):
    text = text.replace("\n", "")
    return text[:length]


async def alarm(user_id, chat_id, msg_id):
    await bot.send_text(
        chat_id=chat_id,
        reply_msg_id=msg_id,
        text=Const.alarm.format(user_id),
        inline_keyboard_markup=move_schema(user_id, chat_id, msg_id),
    )
    db_notes.delete(user_id, chat_id, msg_id)


def set_alarm(user_id, chat_id, msg_id, dt):
    log.debug(locals())
    total_seconds = (dt - pendulum.now()).total_seconds()
    log.debug(int(total_seconds))
    db_users.upsert(user_id, time_zone=default_tz)
    if "@chat.agent" in chat_id:
        db_chats.upsert(chat_id, time_zone=default_tz)

    db_notes.upsert(user_id, chat_id, msg_id, dt.int_timestamp)

    loop.call_later(
        int(total_seconds),
        functools.partial(loop.create_task, alarm(user_id, chat_id, msg_id)),
    )


def human_time(dt):
    date = dt.format("DD.MM.Y")
    time = dt.format("HH:mm") if dt.second == 0 else dt.format("HH:mm:ss")

    if dt.is_same_day(pendulum.now()):
        date = "cегодня"
    else:
        now = pendulum.now()
        if dt.year == now.year and dt.month == now.month and (dt.day - now.day) == 1:
            date = "завтра"
    return f"{date} в {time}"


def machine_time(dt):
    date = dt.format("DD.MM.Y")
    time = dt.format("HH:mm") if dt.second == 0 else dt.format("HH:mm:ss")
    return f"{date} {time}"


async def notes_loader():
    notes = db_notes.select()
    for group, items in groupby(notes, lambda i: f"{i['user_id']}_{i['chat_id']}"):
        items = [i for i in items]
        if bool(
            [
                i
                for i in items
                if pendulum.from_timestamp(i["timestamp"]) < pendulum.now()
            ]
        ):
            await bot.send_text(
                chat_id=group.split("_")[-1], text=Const.sorry_after_fail
            )
        for note in items:
            if pendulum.from_timestamp(note["timestamp"]) < pendulum.now():
                await alarm(
                    user_id=note["user_id"],
                    chat_id=note["chat_id"],
                    msg_id=note["msg_id"],
                )
            else:
                set_alarm(
                    user_id=note["user_id"],
                    chat_id=note["chat_id"],
                    msg_id=note["msg_id"],
                    dt=pendulum.from_timestamp(note["timestamp"]),
                )


def get_granted_users(event):
    _, user_id, chat_id, msg_id, *args = event.data["callbackData"].split("_")
    users = []

    users.extend(
        [
            p["payload"]["message"]["from"]["userId"]
            for p in event.data["message"]["parts"]
            if p["type"] in ("reply", "forward")
            if p["payload"]["message"]["from"]["userId"] != BOT_UIN
        ]
    )
    for p in event.data["message"]["parts"]:
        if p["type"] == "reply" and "parts" in p["payload"]["message"]:
            for inp in p["payload"]["message"]["parts"]:
                if inp["type"] == "mention" and inp["payload"]["userId"] != BOT_UIN:
                    users.append(inp["payload"]["userId"])

    if user_id == event.data["from"]["userId"]:
        users.append(event.data["from"]["userId"])

    return users


def change_del_schema(user_id, chat_id, msg_id):
    return json.dumps(
        [
            [
                {
                    "text": "изменить время",
                    "style": "primary",
                    "callbackData": f"change_{user_id}_{chat_id}_{msg_id}",
                },
                {
                    "text": "удалить",
                    "style": "attention",
                    "callbackData": f"del_{user_id}_{chat_id}_{msg_id}",
                },
            ]
        ]
    )


def move_schema(user_id, chat_id, msg_id):
    return json.dumps(
        [
            [
                {
                    "text": "+ 10 минут",
                    "style": "base",
                    "callbackData": f"move_{user_id}_{chat_id}_{msg_id}_10_m",
                },
                {
                    "text": "+ 30 минут",
                    "style": "base",
                    "callbackData": f"move_{user_id}_{chat_id}_{msg_id}_30_m",
                },
                {
                    "text": "на завтра",
                    "style": "base",
                    "callbackData": f"move_{user_id}_{chat_id}_{msg_id}_1_day",
                },
            ]
        ]
    )

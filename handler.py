import asyncio
import functools
import json
from collections import namedtuple

from dateutil import parser as dateutil_parser
import aiohttp
import pendulum
from pyaspeller import Word
from config import REQUEST_TIMEOUT_S, bot, BOT_UIN
from const import Const

users = {}
UserAlarm = namedtuple('UserAlarm', ['dt', 'msg_id', 'short_text', 'task_id'])

loop = asyncio.get_event_loop()


def get_offset(timezone='Europe/Moscow'):
    return int(pendulum.now(timezone).offset_hours*60*-1)


async def markup_dusi_request(text):
    async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_S),
            headers={'User-agent': bot.user_agent}
    ) as session:
        async with session.get(
                url="http://markup.dusi.mobi/api/text", ssl=False,
                params={
                    "text": text,
                    "offset": get_offset()
                }
        ) as response:
            return json.loads(await response.text())


def get_datetime_by_dateutil(text):
    try:
        return dateutil_parser.parse(text)
    except:
        return False


def get_datetime_by_pendulum(text, tz='Europe/Moscow'):
    try:
        return pendulum.parse(text, tz=tz, strict=False)
    except:
        return False


async def parse_by_markup_dusi(text):
    dtf = {}
    parsed_text = None
    try:
        objects = await markup_dusi_request(text)

        for token in objects['tokens']:
            if token['type'] in ("Time", "Date"):
                dtf[token['type']] = token['formatted']
            if token['type'] == "Text":
                parsed_text = token['value']
        dt = f"{dtf.get('Date', '')}{'T' if dtf.get('Date') else ''}{dtf.get('Time', '')}"
        return pendulum.parse(dt, tz='Europe/Moscow', strict=False), parsed_text
    except:
        return False, parsed_text


async def parser(text):
    for f in [get_datetime_by_dateutil, get_datetime_by_pendulum]:
        dt = f(text)
        if dt:
            return dt, None

    dt, parsed_text = await parse_by_markup_dusi(text)
    if dt:
        return dt, parsed_text

    dt, parsed_text = await parse_by_markup_dusi(speller(text))
    if dt:
        return dt, parsed_text

    return False, None


def is_group(event):
    return '@chat.agent' in event.data['chat']['chatId']


def exists_mention(event):
    return 'parts' in event.data \
           and [p for p in event.data['parts'] if p['type'] == 'mention'
                and p['payload']['userId'] == BOT_UIN]


def speller(text):
    correct = text
    try:
        for word in set(text.split(" ")):
            check = Word(word)
            if not check.correct and check.spellsafe:
                correct = text.replace(word, check.spellsafe)
    except:
        pass
    finally:
        return correct


def short_text(text, length=50):
    text = text.replace("\n", "")
    return text[:length]


async def alarm(chat_id, msg_id):
    await bot.send_text(
        chat_id=chat_id, reply_msg_id=msg_id, text=Const.alarm.format(chat_id)
    )
    users[chat_id].remove([ua for ua in users[chat_id] if ua.msg_id == msg_id].pop())


def set_alarm(dt, chat_id, msg_id, short_text):
    if chat_id not in users:
        users[chat_id] = []

    task_id = loop.call_later(
        (dt - pendulum.now()).seconds,
        functools.partial(loop.create_task, alarm(chat_id, msg_id))
    )
    users[chat_id].append(UserAlarm(dt, msg_id, short_text, task_id))


def human_time(dt):
    date = dt.format('D.MM.Y')
    time = dt.format('HH:mm') if dt.second == 0 else dt.format('HH:mm:ss')

    if dt.is_same_day(pendulum.now()):
        date = "cегодня"
    else:
        now = pendulum.now()
        if dt.year == now.year and dt.month == now.month and (dt.day - now.day) == 1:
            date = "завтра"
    return f"{date} в {time}"


def machine_time(dt):
    date = dt.format('D.MM.Y')
    time = dt.format('HH:mm') if dt.second == 0 else dt.format('HH:mm:ss')
    return f"{date} {time}"


async def message_cb(bot, event):
    if is_group(event) and exists_mention(event):
        return

    dt, text = await parser(event.data['text'])
    if not dt:
        await bot.send_text(chat_id=event.data['chat']['chatId'], text=Const.sorry)
    elif dt < pendulum.now():
        await bot.send_text(chat_id=event.data['chat']['chatId'], text=Const.less_time)
    else:
        set_alarm(
            dt=dt, chat_id=event.data['chat']['chatId'],
            msg_id=event.data['msgId'], short_text=short_text(event.data['text'] if text is None else text)
        )
        await bot.send_text(
            chat_id=event.data['chat']['chatId'],
            text=f"{Const.remind_at.format(human_time(dt))}"
        )


async def list_cb(bot, event):
    user_alarms = users.get(event.data['chat']['chatId'], [])
    if not user_alarms:
        await bot.send_text(
            chat_id=event.data['chat']['chatId'], text=Const.empty
        )
    else:
        await bot.send_text(
            chat_id=event.data['chat']['chatId'],
            text="\n".join([f"[{machine_time(ua.dt)}] {ua.short_text}" for ua in user_alarms])
        )

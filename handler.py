import json
from dateutil import parser as dateutil_parser
import aiohttp
import pendulum
from pyaspeller import Word

from config import REQUEST_TIMEOUT_S, bot, BOT_UIN
from const import Const


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
        return pendulum.parser.parse(text, tz=tz)
    except:
        return False


async def get_datetime_by_markup_dusi(text):
    try:
        objects = await markup_dusi_request(text)
        dtf = {}
        for token in objects['tokens']:
            if token['type'] in ("Time", "Date"):
                for k, v in token['value'].items():
                    dtf[k] = v
        if dtf:
            if 'part' in dtf:
                dtf['dst_rule'] = "pre" if dtf['part'] == 'AM' else 'post' if dtf['part'] == 'PM' else 'error'
                del dtf['part']
            if 'year' not in dtf:
                pd = pendulum.now()
                dtf['year'] = pd.year
                dtf['day'] = pd.day
                dtf['month'] = pd.month

        return pendulum.datetime(**dtf, tz='Europe/Moscow')
    except:
        return False


async def get_datetime(text):
    dt = get_datetime_by_dateutil(text) or get_datetime_by_pendulum(text) or await get_datetime_by_markup_dusi(text)
    if not dt:
        dt = await get_datetime_by_markup_dusi(speller(text))
    return dt


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


async def message_cb(bot, event):
    if is_group(event) and exists_mention(event):
        return

    dt = await get_datetime(event.data['text'])
    if dt < pendulum.now():
        await bot.send_text(chat_id=event.data['chat']['chatId'], text=Const.less_time)
    else:
        await bot.send_text(chat_id=event.data['chat']['chatId'], text=str(dt))

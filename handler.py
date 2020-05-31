import asyncio
import logging
import pendulum
from config import BOT_UIN
from const import Const
from db import db_notes
from helper import (
    is_group,
    exists_mention,
    set_alarm,
    human_time,
    machine_time,
    default_tz,
    get_granted_users,
    change_del_schema,
)
from parser import parse

loop = asyncio.get_event_loop()

log = logging.getLogger(__name__)


async def message_cb(bot, event):
    if is_group(event):
        if not exists_mention(event):
            return
        else:
            event.data["text"] = event.data["text"].replace(BOT_UIN, "")

    dt, text = await parse(event.data["text"])
    if not dt:
        log.debug("match not found")
        await bot.send_text(chat_id=event.data["chat"]["chatId"], text=Const.sorry)
    elif dt < pendulum.now():
        log.debug("match time less then now")
        await bot.send_text(chat_id=event.data["chat"]["chatId"], text=Const.less_time)
    else:
        log.debug(f"match found: {dt}")
        mentions = [
            p["payload"]["userId"]
            for p in event.data.get("parts", [])
            if p["type"] == "mention" and p["payload"]["userId"] != BOT_UIN
        ]

        user_id = event.data["from"]["userId"] if not mentions else mentions[0]
        chat_id = event.data["chat"]["chatId"]
        msg_id = event.data["msgId"]

        set_alarm(user_id, chat_id, msg_id, dt)

        await bot.send_text(
            chat_id=event.data["chat"]["chatId"],
            text=f"{Const.remind_at.format(human_time(dt))}",
            reply_msg_id=msg_id,
            inline_keyboard_markup=change_del_schema(user_id, chat_id, msg_id),
        )


async def forward_cb(bot, event, user):
    if is_group(event) and not exists_mention(event):
        return

    await bot.send_text(chat_id=event.data["chat"]["chatId"], text=Const.when)
    response = await user.wait_response()
    dt, text = await parse(response.data["text"])
    while not dt:
        await bot.send_text(chat_id=event.data["chat"]["chatId"], text=Const.sorry)
        response = await user.wait_response()
        dt, text = await parse(response.data["text"])

        if dt < pendulum.now():
            await bot.send_text(
                chat_id=event.data["chat"]["chatId"], text=Const.less_time
            )
            dt = False

    user_id = event.data["from"]["userId"]
    chat_id = event.data["chat"]["chatId"]
    msg_id = event.data["msgId"]

    set_alarm(user_id, chat_id, msg_id, dt)

    await bot.send_text(
        chat_id=event.data["chat"]["chatId"],
        text=f"{Const.remind_at.format(human_time(dt))}",
        reply_msg_id=msg_id,
        inline_keyboard_markup=change_del_schema(user_id, chat_id, msg_id),
    )


async def list_cb(bot, event):
    if is_group(event) and not exists_mention(event):
        return

    # TODO: табуляция для красоты
    user_notes = sorted(
        db_notes.select_by_chat_id(event.data["chat"]["chatId"]),
        key=lambda x: x["timestamp"],
    )
    if not user_notes:
        await bot.send_text(chat_id=event.data["chat"]["chatId"], text=Const.empty)

    for note in user_notes:
        await bot.send_text(
            chat_id=event.data["chat"]["chatId"],
            text=machine_time(pendulum.from_timestamp(note["timestamp"], default_tz)),
            reply_msg_id=note["msg_id"],
            inline_keyboard_markup=change_del_schema(
                note["user_id"], note["chat_id"], note["msg_id"]
            ),
        )


async def start_cb(bot, event):
    if is_group(event) and not exists_mention(event):
        return

    await bot.send_text(chat_id=event.data["chat"]["chatId"], text=Const.start)


async def button_change_cb(bot, event, user):
    _, user_id, chat_id, msg_id = event.data["callbackData"].split("_")

    granted_users = get_granted_users(event)

    if (
        event.data["from"]["userId"] in granted_users
        and chat_id == event.data["message"]["chat"]["chatId"]
    ):
        if db_notes.select_by_uniq(user_id, chat_id, msg_id):
            await bot.answer_callback_query(
                query_id=event.data["queryId"], text="", show_alert=False
            )
            await bot.send_text(chat_id=chat_id, text=Const.when_change)

            response = await user.wait_response()
            dt, text = await parse(response.data["text"])
            while not dt:
                await bot.send_text(
                    chat_id=event.data["chat"]["chatId"], text=Const.sorry
                )
                response = await user.wait_response()
                dt, text = await parse(response)

                if dt < pendulum.now():
                    await bot.send_text(
                        chat_id=event.data["chat"]["chatId"], text=Const.less_time
                    )
                    dt = False

            set_alarm(user_id, chat_id, msg_id, dt)
            await bot.send_text(
                chat_id=chat_id,
                text=f"{Const.remind_at.format(human_time(dt))}",
                reply_msg_id=msg_id,
                inline_keyboard_markup=change_del_schema(user_id, chat_id, msg_id),
            )
        else:
            await bot.answer_callback_query(
                query_id=event.data["queryId"],
                text=Const.already_noticed,
                show_alert=False,
            )
    else:
        await bot.answer_callback_query(
            query_id=event.data["queryId"],
            text=Const.permission_denied,
            show_alert=False,
        )


async def button_delete_cb(bot, event):
    _, user_id, chat_id, msg_id = event.data["callbackData"].split("_")

    granted_users = get_granted_users(event)

    if (
        event.data["from"]["userId"] in granted_users
        and chat_id == event.data["message"]["chat"]["chatId"]
    ):
        if db_notes.delete(user_id, chat_id, msg_id):
            await bot.delete_messages(
                chat_id=event.data["message"]["chat"]["chatId"],
                msg_id=event.data["message"]["msgId"],
            )
            await bot.answer_callback_query(
                query_id=event.data["queryId"], text=Const.deleted, show_alert=False
            )
        else:
            await bot.answer_callback_query(
                query_id=event.data["queryId"],
                text=Const.something_wrong,
                show_alert=False,
            )
            # await bot.send_text(chat_id=chat_id, text=Const.deleted, reply_msg_id=msg_id)
    else:
        await bot.answer_callback_query(
            query_id=event.data["queryId"],
            text=Const.permission_denied,
            show_alert=False,
        )


async def button_move_cb(bot, event):
    _, user_id, chat_id, msg_id, offset_time, offset_type = event.data[
        "callbackData"
    ].split("_")
    granted_users = get_granted_users(event)

    await bot.answer_callback_query(
        query_id=event.data["queryId"], text="", show_alert=False
    )

    if (
        event.data["from"]["userId"] in granted_users
        and chat_id == event.data["message"]["chat"]["chatId"]
    ):
        offset = {}
        if offset_type == "m":
            offset["minutes"] = int(offset_time)

        if offset_type == "day":
            offset["days"] = int(offset_time)

        new_dt = pendulum.now().add(**offset)
        set_alarm(user_id, chat_id, msg_id, new_dt)
        await bot.send_text(
            chat_id=chat_id,
            text=f"{Const.remind_at.format(human_time(new_dt))}",
            reply_msg_id=msg_id,
            inline_keyboard_markup=change_del_schema(user_id, chat_id, msg_id),
        )


async def help_cb(bot, event):
    if is_group(event) and not exists_mention(event):
        return

    await bot.send_text(chat_id=event.data["chat"]["chatId"], text=Const.help)


async def example_cb(bot, event):
    if is_group(event) and not exists_mention(event):
        return

    await bot.send_text(chat_id=event.data["chat"]["chatId"], text=Const.example)


async def description_cb(bot, event):
    if is_group(event) and not exists_mention(event):
        return

    await bot.send_text(chat_id=event.data["chat"]["chatId"], text=Const.description)

from config import bot, NAME, OWNER, PID_NAME
from mailru_im_async_bot.handler import (
    MessageHandler,
    CommandHandler,
    BotButtonCommandHandler,
    FeedbackCommandHandler,
)
from mailru_im_async_bot.filter import Filter

from const import Const
from handler import (
    message_cb,
    list_cb,
    start_cb,
    forward_cb,
    button_delete_cb,
    help_cb,
    button_change_cb,
    button_move_cb,
    example_cb,
    description_cb,
)
from signal import signal, SIGUSR1
from mailru_im_async_bot.util import do_rollover_log
from pid import PidFile
import asyncio
import logging
from helper import notes_loader

# register signal for rotate log
signal(SIGUSR1, do_rollover_log)

loop = asyncio.get_event_loop()

log = logging.getLogger(__name__)


# Register your handlers here
# ---------------------------------------------------------------------
mhfcb = MessageHandler(
    callback=forward_cb, filters=~Filter.regexp("^/") & Filter.forward, multiline=True
)
cbcb = BotButtonCommandHandler(
    callback=button_change_cb,
    filters=Filter.callback_data_regexp("^change"),
    multiline=True,
)


# [i for i in handler.ignore if i is user.handler]
mhmcb = MessageHandler(
    callback=message_cb,
    filters=~Filter.regexp("^/") & ~Filter.forward,
    ignore=[mhfcb, cbcb],
)
bot.dispatcher.add_handler(mhfcb)
bot.dispatcher.add_handler(mhmcb)
bot.dispatcher.add_handler(cbcb)
bot.dispatcher.add_handler(CommandHandler(callback=list_cb, command="list"))
bot.dispatcher.add_handler(CommandHandler(callback=start_cb, command="start"))
bot.dispatcher.add_handler(CommandHandler(callback=help_cb, command="help"))
bot.dispatcher.add_handler(CommandHandler(callback=example_cb, command="example"))
bot.dispatcher.add_handler(
    CommandHandler(callback=description_cb, command="description")
)
bot.dispatcher.add_handler(
    FeedbackCommandHandler(
        target=OWNER,
        message=Const.feedback_get,
        reply=Const.feedback_reply,
        error_reply=Const.feedback_error,
    )
)
bot.dispatcher.add_handler(
    BotButtonCommandHandler(
        callback=button_delete_cb, filters=Filter.callback_data_regexp("^del")
    )
)
bot.dispatcher.add_handler(
    BotButtonCommandHandler(
        callback=button_move_cb, filters=Filter.callback_data_regexp("^move")
    )
)
# ---------------------------------------------------------------------


def role_change(current, new):
    if current == new:
        log.info(f"the role remained the same: {current}")
    else:
        if new == "main":
            loop.create_task(bot.start_polling())
            loop.create_task(notes_loader())
        else:
            loop.create_task(bot.stop_polling())
        log.info(f"role was change from {current} to {new}")


# async def process(rq: IncomingRequest):
#     log.info('{}: process called'.format(rq))
#     rq.reply(200, 'ok')


with PidFile(PID_NAME):
    # pypros.ctlr.G_git_hash = HASH_ if HASH_ else VERSION
    # pypros.ctlr.role_changed_cb = lambda current, new: role_change(current, new)
    # pypros.ctlr.IncomingHandlers.CHECK = lambda cn, p: cn.reply(p, 200, 'ok')
    # pypros.ctlr.init(self_alias=config['main']['alias'], host=config['ctlr']['host'], port=config['ctlr']['port'])
    server = None
    try:
        loop.run_until_complete(bot.init())
        role_change("None", "main")
        # server = loop.run_until_complete(pypros.listen(config['main']['host'], int(config['main']['port']), process))
        loop.run_forever()
    finally:
        if server:
            server.close()
        # loop.run_until_complete(pypros.ipros.shutdown())
        loop.close()

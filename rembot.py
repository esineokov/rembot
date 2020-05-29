
from config import bot, NAME
from mailru_im_async_bot.handler import MessageHandler, CommandHandler
from mailru_im_async_bot.filter import Filter

from db import save, load
from handler import message_cb, list_cb
from signal import signal, SIGUSR1
from mailru_im_async_bot.util import do_rollover_log
from pid import PidFile
import asyncio
import logging


log = logging.getLogger(__name__)

# register signal for rotate log
signal(SIGUSR1, do_rollover_log)

loop = asyncio.get_event_loop()


# Register your handlers here
# ---------------------------------------------------------------------
bot.dispatcher.add_handler(MessageHandler(callback=message_cb, filters=~Filter.regexp("^/")))
bot.dispatcher.add_handler(CommandHandler(callback=list_cb, command='list'))
# ---------------------------------------------------------------------


def role_change(current, new):
    if current == new:
        log.info(f"the role remained the same: {current}")
    else:
        if new == 'main':
            loop.create_task(bot.start_polling())
        else:
            loop.create_task(bot.stop_polling())
        log.info(f"role was change from {current} to {new}")


# async def process(rq: IncomingRequest):
#     log.info('{}: process called'.format(rq))
#     rq.reply(200, 'ok')


with PidFile(NAME):
    # pypros.ctlr.G_git_hash = HASH_ if HASH_ else VERSION
    # pypros.ctlr.role_changed_cb = lambda current, new: role_change(current, new)
    # pypros.ctlr.IncomingHandlers.CHECK = lambda cn, p: cn.reply(p, 200, 'ok')
    # pypros.ctlr.init(self_alias=config['main']['alias'], host=config['ctlr']['host'], port=config['ctlr']['port'])
    server = None
    try:
        loop.run_until_complete(bot.init())
        load()
        role_change('None', 'main')
        # server = loop.run_until_complete(pypros.listen(config['main']['host'], int(config['main']['port']), process))
        loop.run_forever()
    finally:
        save()
        if server:
            server.close()
        # loop.run_until_complete(pypros.ipros.shutdown())
        loop.close()
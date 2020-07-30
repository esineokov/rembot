import configparser
import logging.config
import os
import sys

import graphyte
from mailru_im_async_bot.bot import Bot

configs_path = "./"

# Get config path from args
if len(sys.argv) > 1:
    configs_path = sys.argv[1]


# Check exists config
for config in ["config.ini", "logging.ini"]:
    if not os.path.isfile(os.path.join(configs_path, config)):
        raise FileExistsError(f"File {config} not found in path {configs_path}")

# Read config
config = configparser.ConfigParser()
config.read(os.path.join(configs_path, "config.ini"))
logging.config.fileConfig(
    os.path.join(configs_path, "logging.ini"), disable_existing_loggers=False
)


# init graphite sender
if config.getboolean("graphite", "enable"):
    graphyte.init(
        config.get("graphite", "server"),
        prefix=f"{config.get('graphite', 'prefix')}.{config.get('main', 'alias')}",
    )

NAME = "RemBot"
VERSION = "0.0.1"
HASH_ = None
TOKEN = config.get("icq_bot", "token")
OWNER = config.get("icq_bot", "owner")
BOT_UIN = TOKEN.split(":")[-1]
POLL_TIMEOUT_S = int(config.get("icq_bot", "poll_time_s"))
REQUEST_TIMEOUT_S = int(config.get("icq_bot", "request_timeout_s"))
TASK_TIMEOUT_S = int(config.get("icq_bot", "task_timeout_s"))
TASK_MAX_LEN = int(config.get("icq_bot", "task_max_len"))
BOT_API_HOST = config.get("icq_bot", "host")

PID_NAME = config.get("main", "pid")

COORDINATE_LINK_PATTERN = r"(?<=^https://www\.google\.com/maps/search\/\?api=1&query=)\d+\.\d+,\d+\.\d+(?=$)"

bot = Bot(
    token=TOKEN,
    version=VERSION,
    name=NAME,
    poll_time_s=POLL_TIMEOUT_S,
    request_timeout_s=REQUEST_TIMEOUT_S,
    task_max_len=TASK_MAX_LEN,
    task_timeout_s=TASK_TIMEOUT_S,
    api_url_base=BOT_API_HOST,
)

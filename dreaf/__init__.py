import pathlib
import sys
from logging import handlers

import pendulum
import logging

from dreaf.context import ctx

__all__ = ('ctx',)

pendulum.set_local_timezone()

debug_flag = True

logging.getLogger().setLevel(logging.DEBUG)
discord_log = logging.getLogger("discord")
discord_log.setLevel(logging.INFO)
dreaf_log = logging.getLogger("dreaf")

# setup log directory
log_path = pathlib.Path("logs")
if not log_path.exists():
    log_path.mkdir()


# file handler factory
def create_fh(file_name):
    fh_path = log_path/file_name
    return handlers.RotatingFileHandler(
        filename=fh_path, encoding='utf-8', mode='a',
        maxBytes=400000, backupCount=20
    )


# set log formatting
log_format = logging.Formatter(
    '%(asctime)s %(name)s %(levelname)s %(module)s %(funcName)s %(lineno)d: '
    '%(message)s',
    datefmt="[%d/%m/%Y %H:%M]"
)

# create file handlers
dreaf_fh = create_fh('dreaf.log')
dreaf_fh.setLevel(logging.INFO)
dreaf_fh.setFormatter(log_format)
discord_fh = create_fh('discord.log')
discord_fh.setLevel(logging.INFO)
discord_fh.setFormatter(log_format)
discord_log.addHandler(discord_fh)

# create console handler
console_std = sys.stdout if debug_flag else sys.stderr
dreaf_console = logging.StreamHandler(console_std)
dreaf_console.setLevel(logging.INFO if debug_flag else logging.ERROR)
dreaf_console.setFormatter(log_format)
dreaf_log.addHandler(dreaf_console)
discord_console = logging.StreamHandler(console_std)
discord_console.setLevel(logging.ERROR)
discord_console.setFormatter(log_format)
discord_log.addHandler(discord_console)

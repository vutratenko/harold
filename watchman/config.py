
from dynaconf import Dynaconf
import logging


settings = Dynaconf(
    envvar_prefix="WATCHMAN",
    settings_files=['settings.toml', '.secrets.toml'],
)
# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.

if settings["log_level"] == "DEBUG":
    level = logging.DEBUG
elif settings["log_level"] == "INFO":
    level = logging.INFO
elif settings["log_level"] == "ERROR":
    level = logging.ERROR
elif settings["log_level"] == "FATAL":
    level = logging.FATAL
else:
    level = logging.ERROR
from harold import app
from waitress import serve
from paste.translogger import TransLogger
serve(TransLogger(app, setup_console_handler=False))
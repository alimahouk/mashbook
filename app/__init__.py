from flask import Flask
from flask_socketio import SocketIO
import openai
import os
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import Configuration


APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# Open AI configuration.
openai.api_base = Configuration.OPENAI_API_BASE
openai.api_key = Configuration.OPENAI_API_KEY
openai.api_type = Configuration.OPENAI_API_TYPE
openai.api_version = Configuration.OPENAI_API_VERSION

os.environ["OPENAI_API_BASE"] = Configuration.OPENAI_API_BASE
os.environ["OPENAI_API_KEY"] = Configuration.OPENAI_API_KEY
os.environ["OPENAI_API_TYPE"] = Configuration.OPENAI_API_TYPE
os.environ["OPENAI_API_VERSION"] = Configuration.OPENAI_API_VERSION

if not Configuration.DEBUG:
    os.environ["TRANSFORMERS_CACHE"] = "/var/www/html/etmeh"

app = Flask(__name__)
app.config["PREFERRED_URL_SCHEME"] = "https"
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config["TEMPLATES_AUTO_RELOAD"] = True
# This fixes issues when running behind Nginx as a proxy.
app.wsgi_app = ProxyFix(app.wsgi_app)

if Configuration.DEBUG:
    socketio = SocketIO(app)
else:
    socketio = SocketIO(app, async_mode="gevent_uwsgi")


from app import routes


if __name__ == "__main__":
    socketio.run(app, async_mode="gevent_uwsgi")

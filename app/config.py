import os
from enum import Enum, IntEnum

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class AzureOpenAIDeployment:
    DAVINCI = "davinci"
    GPT_35 = "chat"
    GPT_35_16K = "gpt-35-turbo-16k"
    TEXT_EMBEDDING = "text-embedding-ada-002"


class ChatMessageSenderRole(str, Enum):
    ASSISTANT = "assistant"
    SYSTEM = "system"
    USER = "user"


class Configuration:
    DEBUG = os.getenv('FLASK_DEBUG', '1') == '1'
    # --
    APP_ROOT = os.path.dirname(os.path.abspath(__file__))
    AWS_EC2_PROD_DATABASE_01 = os.getenv('DB_HOST', 'localhost')
    BASE_URL = "http://127.0.0.1:8000" if DEBUG else "https://mashbook.co"  # Make sure this matches your local development server.
    CHAT_PURGE_CHECK_INTERVAL = 60  # Seconds
    DATABASE_NAME = os.getenv('DB_NAME', 'mashbook')
    DATABASE_USER = os.getenv('DB_USER', 'postgres')
    OPENAI_API_BASE = os.getenv('OPENAI_API_BASE')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_API_TYPE = os.getenv('OPENAI_API_TYPE', 'azure')
    OPENAI_API_VERSION = os.getenv('OPENAI_API_VERSION', '2023-08-01-preview')
    OPENAI_RETRY_MAX_ATTEMPTS = 5
    OPENAI_RETRY_DELAY = 3  # Seconds.
    OPENAI_TOKEN_LIMIT = 15500
    USER_ACCOUNT_MAX_COUNT = 5
    # --
    # DIRECTORY PATHS
    # --
    STATIC_DIR = os.path.join(APP_ROOT, "static")
    DOCS_DIR = os.path.join(STATIC_DIR, "docs")
    IMAGES_DIR = os.path.join(STATIC_DIR, "images")


class DatabaseTable:
    CHAT = "chat_"
    CHAT_MESSAGE = "chat_message_"
    MODEL = "model_"
    USER = "user_"
    USER_SESSION = "user_session_"


class LLMOption(IntEnum):
    GPT3 = 1
    GPT4 = 2


class ProtocolKey(str):
    CHAT = "chat"
    CHAT_ID = "chat_id"
    CONTENT_HTML = "content_html"
    CONTENT_MARKDOWN = "content_md"
    CONTEXT_RANGE_LEN = "context_range_length"
    CONTEXT_RANGE_START = "context_range_start"
    CREATION_DATE = "creation_date"
    CREATION_TIMESTAMP = "creation_timestamp"
    EMAIL_ADDRESS = "email_address"
    ERROR = "error"
    ERROR_CODE = "error_code"
    ERROR_MESSAGE = "error_message"
    FORK_MESSAGE_ID = "fork_message_id"
    ID = "id"
    IP_ADDRESS = "ip_address"
    LAST_ACTIVITY = "last_activity"
    LOCATION = "location"
    MAC_ADDRESS = "mac_address"
    MESSAGE = "message"
    MESSAGE_ID = "message_id"
    MESSAGES = "messages"
    MODEL = "model"
    MODEL_ID = "model_id"
    NAME = "name"
    OFFSET = "offset"
    PARENT_CHAT_ID = "parent_chat_id"
    PASSWORD = "password"
    PERMALINK = "permalink"
    SALT = "salt"
    SENDER = "sender"
    SENDER_ID = "sender_id"
    SENDER_ROLE = "sender_role"
    SESSION_ID = "session_id"
    TOPIC = "topic"
    USER = "user"
    USER_ID = "user_id"
    USER_SESSION = "user_session"
    USER_SESSION_ID = "user_session_id"
    USER_SESSIONS = "user_sessions"
    USERS = "users"
    USER_ID = "user_id"
    URL = "url"


class ResponseStatus(IntEnum):
    # Generic
    OK = 0
    BAD_REQUEST = 1
    FORBIDDEN = 2
    INTERNAL_SERVER_ERROR = 3
    NOT_FOUND = 4
    NOT_IMPLEMENTED = 5
    PAYLOAD_TOO_LARGE = 6
    TOO_MANY_REQUESTS = 7
    UNAUTHORIZED = 8
    # Specific
    CREDENTIALS_INVALID = 9
    EMAIL_FORMAT_INVALID = 10
    EMAIL_IN_USE = 11
    PASSWORD_FORMAT_INVALID = 12
    SESSION_INVALID = 13
    USER_ACCOUNT_MAX_COUNT_REACHED = 14
    USER_NOT_FOUND = 15
    CONTENT_MAX_LEN_EXCEEDED = 16
    MESSAGE_CONTEXT_INVALID = 17

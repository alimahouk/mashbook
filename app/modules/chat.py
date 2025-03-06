from bs4 import BeautifulSoup
from datetime import datetime
from flask import request
from flask_socketio import disconnect, Namespace, send
import markdown
import sched
import threading
import time
from typing import TypeVar, Type
import uuid

from app.config import (ChatMessageSenderRole, Configuration,
                        DatabaseTable, LLMOption, ProtocolKey, ResponseStatus)
from app.llm import gpt
from app.modules.db import RelationalDB
from app.modules.chat_message import ChatMessage
from app.modules.model import Model
from app.modules.user import User
from app.modules.user_session import UserSession


###########
# CLASSES #
###########


T = TypeVar("T", bound="Chat")


class ChatNamespace(Namespace):
    def __init__(self,
                 namespace: str = None):
        super().__init__(namespace)
        self.sessions: dict[str, ChatSession] = {}  # Holds the chats of each connected user (keyed by session ID).

    def on_connect(self) -> None:
        session_id = _session_id()
        if session_id:
            session: UserSession = UserSession.get_by_id(session_id)
            if session:
                user_id = session.user_id
            else:
                user_id = None
        else:
            user_id = None

        chat_session = self.sessions.get(session_id)
        if chat_session:
            chat_session.ref_count += 1
        elif session_id:
            self.sessions[session_id] = ChatSession(user_id)
            if user_id:
                print(f"User {user_id} connected.")
            else:
                print(f"Unregistered user with session {session_id} connected.")

        send({"session_id": session_id})

    def on_disconnect(self) -> None:
        session_id = _session_id()
        if session_id:
            chat_session = self.sessions.get(session_id)
            if chat_session:
                chat_session.ref_count -= 1
                if chat_session.ref_count < 1:
                    self.sessions.pop(session_id, None)
                    if chat_session.user_id:
                        print(f"User {chat_session.user_id} disconnected.")
                    else:
                        print(f"Unregistered user with session {session_id} disconnected.")
        else:
            print("Socket client kicked.")

    def on_message(self,
                   data: dict) -> None:
        session_id = _session_id()
        if not session_id:
            print("Socket client messaged with an invalid session - kicking…")
            send({ProtocolKey.ERROR: "Invalid session."})
            disconnect()  # Kick this client.

        chat_session = self.sessions.get(session_id)
        if not chat_session:
            print("Socket client messaged with an invalid session - kicking…")
            send({ProtocolKey.ERROR: "Invalid session."})
            disconnect()  # Kick this client.

        if chat_session.user_id:
            print(f"User {chat_session.user_id} sent: {data}")
        else:
            print(f"Unregistered user with session {session_id} sent: {data}")

        content_md = data.get(ProtocolKey.CONTENT_MARKDOWN)
        if not content_md:
            send({ProtocolKey.ERROR: "Empty message content."})

        if not isinstance(content_md, str):
            send({ProtocolKey.ERROR: "Invalid message content."})
            return

        chat_id = data.get(ProtocolKey.CHAT_ID)
        if chat_id:
            chat_id = uuid.UUID(chat_id)
        else:
            send({ProtocolKey.ERROR: "Missing chat ID."})
            return

        if not chat_session.chat or chat_session.chat.id != chat_id:
            chat_session.chat = Chat.get_by_id(chat_id)

        if chat_session.chat.user_id != chat_session.user_id:
            send({ProtocolKey.ERROR: "Current user ID does not match current chat creator ID."})
            return

        content_md = content_md.strip()
        if len(content_md) > Configuration.OPENAI_TOKEN_LIMIT - 100:
            send({ProtocolKey.ERROR: "Message exceeds maximum length allowed."})
            return

        md_extension_configs = {
            "pymdownx.highlight": {
                "auto_title": True,
                "auto_title_map": {
                    "Python Console Session": "Python"
                }
            }
        }
        content_html = markdown.markdown(
            content_md,
            extensions=["pymdownx.superfences"],
            extension_configs=md_extension_configs
        )

        if not chat_session.chat.messages:
            # Message history of the chat might not be loaded yet.
            # Load it now (if no messages exist it'll be an empty list
            # anyway).
            if chat_session.chat.fork_message_id:
                # Get the messages of the parent chat.
                fork_message: ChatMessage = ChatMessage.get_by_id(chat_session.chat.fork_message_id)
                chat_session.chat.messages = fork_message.get_all_prior()

            chat_session.chat.messages += ChatMessage.get_all_by_chat(chat_id)

        # Create a new message object.
        message: ChatMessage = ChatMessage.create(
            chat_id=chat_id,
            content_html=content_html,
            content_md=content_md,
            sender_id=chat_session.chat.user_id,
            sender_role=ChatMessageSenderRole.USER
        )
        chat_session.chat.messages.append(message)

        model: Model = Model.get_by_id(chat_session.chat.model_id)
        if model:
            # Get a response from OpenAI.
            llm_response_md = gpt.chat(chat_session.chat.messages, model)
            llm_response_html = markdown.markdown(
                llm_response_md,
                extensions=["pymdownx.superfences"],
                extension_configs=md_extension_configs
            )
            response: ChatMessage = ChatMessage.create(
                chat_id=chat_id,
                content_html=llm_response_html,
                content_md=llm_response_md,
                sender_role=ChatMessageSenderRole.ASSISTANT
            )
            chat_session.chat.messages.append(response)
            send({ProtocolKey.MESSAGE: response.as_dict()})
        else:
            send({ProtocolKey.ERROR: "No model exists for the given model ID."})


class ChatSession:
    def __init__(self, user_id: int = None) -> None:
        self.chat: Chat | None = None
        """
        Whenever a socket for a given session ID connects,
        increment the reference count. When one disconnects,
        decrement it. When the count drops to 0, that means the
        user is completely offline.
        """
        self.ref_count: int = 1
        self.user_id: int | None = user_id


class ChatPurgeJob(threading.Thread):
    """
    Periodically delete stale chats from unregistered users.
    """

    def __init__(self) -> None:
        super().__init__(daemon=True)

    def purge(self,
              scheduled_task) -> None:
        Chat.purge()
        scheduled_task.enter(
            Configuration.CHAT_PURGE_CHECK_INTERVAL,
            1,
            self.purge,
            (scheduled_task,)
        )

    def run(self) -> None:
        chat_purge_scheduled_task = sched.scheduler(time.time, time.sleep)
        chat_purge_scheduled_task.enter(
            Configuration.CHAT_PURGE_CHECK_INTERVAL,
            1,
            self.purge,
            (chat_purge_scheduled_task,)
        )
        chat_purge_scheduled_task.run()


class Chat:
    def __init__(self,
                 data: dict) -> None:
        self.creation_timestamp: datetime = None
        self.fork_message_id: uuid.UUID = None
        self.id: uuid.UUID = None
        self.messages: list = []
        self.model_id: int = None
        self.permalink: str = None
        self.topic: str = None
        self.user: User = None
        self.user_id: int = None

        if data:
            if ProtocolKey.CREATION_TIMESTAMP in data:
                self.email_address: datetime = data[ProtocolKey.CREATION_TIMESTAMP]

            if ProtocolKey.FORK_MESSAGE_ID in data:
                self.fork_message_id: uuid.UUID = data[ProtocolKey.FORK_MESSAGE_ID]

            if ProtocolKey.ID in data:
                self.id: uuid.UUID = data[ProtocolKey.ID]

            if ProtocolKey.MODEL_ID in data:
                self.model_id: int = data[ProtocolKey.MODEL_ID]

            if ProtocolKey.TOPIC in data:
                self.topic: str = data[ProtocolKey.TOPIC]

            if ProtocolKey.USER in data:
                self.user: User = User(data[ProtocolKey.USER])

            if ProtocolKey.USER_ID in data:
                self.user_id: int = data[ProtocolKey.USER_ID]

        if self.id:
            self.permalink = f"{Configuration.BASE_URL}/c/{str(self.id)}"

    def __eq__(self,
               __o: object) -> bool:
        ret = False
        if isinstance(__o, type(self)) and \
                self.id == __o.id:
            ret = True
        return ret

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        ret = ""
        if self.id:
            ret += f"Chat {self.id} ('{self.topic}')"
        return ret

    def as_dict(self) -> dict:
        serialized = {
            ProtocolKey.ID: str(self.id),
            ProtocolKey.MODEL_ID: self.model_id,
            ProtocolKey.PERMALINK: self.permalink,
            ProtocolKey.TOPIC: self.topic
        }
        if self.creation_timestamp:
            serialized[ProtocolKey.CREATION_DATE] = self.creation_timestamp.strftime("%e %b %Y")
            serialized[ProtocolKey.CREATION_TIMESTAMP] = self.creation_timestamp.astimezone().isoformat()

        messages_serialized = []
        for message in self.messages:
            messages_serialized.append(message.as_dict())
        serialized[ProtocolKey.MESSAGES] = messages_serialized

        if self.user:
            serialized[ProtocolKey.USER] = self.user.as_dict()

        if self.user_id:
            serialized[ProtocolKey.USER_ID] = self.user_id

        return serialized

    @classmethod
    def create(cls: Type,
               fork_message_id: uuid.UUID = None,
               model_id: int = None,
               topic: str = None,
               user_id: int = None) -> T:
        """
        Call this method to create a Chat object.
        """

        if fork_message_id and not isinstance(fork_message_id, uuid.UUID):
            raise TypeError(f"Argument 'fork_message_id' must be of type UUID, not {type(fork_message_id)}.")

        if not isinstance(model_id, int):
            raise TypeError(f"Argument 'model_id' must be of type int, not {type(model_id)}.")

        if model_id <= 0:
            raise ValueError("Argument 'model_id' must be a positive, non-zero integer.")

        if topic and not isinstance(topic, str):
            raise TypeError(f"Argument 'topic' must be of type str, not {type(topic)}.")

        if topic is not None:
            topic = topic.strip()

        if not topic:
            topic = f"Chat on {datetime.now().strftime('%d/%m/%Y')}"

        if user_id:
            if not isinstance(user_id, int):
                raise TypeError(f"Argument 'user_id' must be of type int, not {type(user_id)}.")

            if user_id <= 0:
                raise ValueError("Argument 'user_id' must be a positive, non-zero integer.")

        ret: Type = None
        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                INSERT INTO
                    {DatabaseTable.CHAT}
                    ({ProtocolKey.FORK_MESSAGE_ID}, {ProtocolKey.MODEL_ID}, {ProtocolKey.TOPIC},
                     {ProtocolKey.USER_ID})
                VALUES
                    (%s, %s, %s,
                     %s)
                RETURNING *;
                """,
                (fork_message_id, model_id, topic, user_id)
            )
            result = cursor.fetchone()
            db.connection.commit()
            if result:
                ret = cls(result)
                ret.user = User.get_by_id(user_id)
        except Exception as e:
            print(e)
        finally:
            db.close()

        return ret

    def delete(self) -> None:
        if not self.id:
            raise Exception("Chat deletion requires a chat ID.")

        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                DELETE FROM
                    {DatabaseTable.CHAT}
                WHERE
                    {ProtocolKey.ID} = %s;
                """,
                (self.id,)
            )
            db.connection.commit()
        except Exception as e:
            print(e)
        finally:
            db.close()

    @classmethod
    def get_all_by_user(cls: Type,
                        user_id: int,
                        offset: int = 0) -> list:
        if not isinstance(user_id, int):
            raise TypeError(f"Argument 'user_id' must be of type int, not {type(user_id)}.")

        if user_id <= 0:
            raise ValueError("Argument 'user_id' must be a positive, non-zero integer.")

        ret = []
        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                SELECT 
                    c.*,
                    u.{ProtocolKey.USER}
                FROM 
                    {DatabaseTable.CHAT} AS c
                LEFT JOIN (
                    SELECT
                        {ProtocolKey.ID},
                        ROW_TO_JSON(u) AS {ProtocolKey.USER}
                    FROM 
                        {DatabaseTable.USER} AS u
                ) AS u ON c.{ProtocolKey.USER_ID} = u.{ProtocolKey.ID}
                WHERE
                    c.{ProtocolKey.USER_ID} = %s
                ORDER BY
                    c.{ProtocolKey.CREATION_TIMESTAMP} DESC
                LIMIT
                    50 
                OFFSET
                    %s;
                """,
                (user_id, offset)
            )
            results = cursor.fetchall()
            db.connection.commit()
            for result in results:
                ret.append(cls(result))
        except Exception as e:
            print(e)
        finally:
            db.close()

        return ret

    @classmethod
    def get_by_id(cls: Type,
                  chat_id: uuid.UUID) -> T:
        if not isinstance(chat_id, uuid.UUID):
            raise TypeError(f"Argument 'chat_id' must be of type UUID, not {type(chat_id)}.")

        ret: Type = None
        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                SELECT
                    *
                FROM
                    {DatabaseTable.CHAT}
                WHERE
                    {ProtocolKey.ID} = %s;
                """,
                (chat_id,)
            )
            result = cursor.fetchone()
            db.connection.commit()
            if result:
                ret = cls(result)
        except Exception as e:
            print(e)
        finally:
            db.close()

        return ret

    @staticmethod
    def purge() -> None:
        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                DELETE FROM
                    {DatabaseTable.CHAT}
                WHERE
                    {ProtocolKey.CREATION_TIMESTAMP} < NOW() - INTERVAL '1 minute' AND {ProtocolKey.USER_ID} IS NULL;
                """
            )
            db.connection.commit()
        except Exception as e:
            print(e)
        finally:
            db.close()

    def set_topic(self,
                  topic: str) -> None:
        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                UPDATE
                    {DatabaseTable.CHAT}
                SET
                    {ProtocolKey.TOPIC} = %s
                WHERE
                    {ProtocolKey.ID} = %s;
                """,
                (topic, self.id)
            )
            db.connection.commit()
            self.topic = topic
        except Exception as e:
            print(e)
        finally:
            db.close()


####################
# MODULE FUNCTIONS #
####################


def _session_id() -> str:
    session_id = request.cookies.get(ProtocolKey.USER_SESSION_ID)
    if not session_id:
        session_id = request.cookies.get(ProtocolKey.SESSION_ID)
    return session_id


def _find_corresponding_markdown_indices(plain_text: str,
                                         md_str: str,
                                         start: int,
                                         length: int):
    # Extract the selected text from the plain text.
    selected_text = plain_text[start:start + length]
    # Try to find this exact text in the markdown.
    md_start_index = md_str.find(selected_text)

    if md_start_index == -1:
        return None, None

    md_end_index = md_start_index + length
    return md_start_index, md_end_index


def get_chat(session_id: str,
             chat_id: uuid.UUID) -> tuple[dict, ResponseStatus]:
    if not chat_id:
        response_status = ResponseStatus.BAD_REQUEST
        response = {
            ProtocolKey.ERROR: {
                ProtocolKey.ERROR_CODE: response_status.value,
                ProtocolKey.ERROR_MESSAGE: "Missing argument: 'chat_id'."
            }
        }
    else:
        chat: Chat = Chat.get_by_id(chat_id)
        if chat:
            chat.messages = ChatMessage.get_all_by_chat(chat_id)
            response_status = ResponseStatus.OK
            response = chat.as_dict()
        else:
            response_status = ResponseStatus.NOT_FOUND
            response = {
                ProtocolKey.ERROR: {
                    ProtocolKey.ERROR_CODE: response_status.value,
                    ProtocolKey.ERROR_MESSAGE: "No chat exists for the given ID."
                }
            }

    return (response, response_status)


def make(session_id: str,
         context_range_length: int = None,
         context_range_start: int = None,
         content_md: str = None,
         message_id: uuid.UUID = None) -> tuple[dict, ResponseStatus]:
    if content_md:
        content_md = content_md.strip()
    else:
        content_md = None

    if context_range_length:
        try:
            context_range_length = int(context_range_length)
        except:
            context_range_length = None
    else:
        context_range_length = None

    if context_range_start:
        try:
            context_range_start = int(context_range_start)
        except:
            context_range_start = None
    else:
        context_range_start = None

    if not content_md:
        response_status = ResponseStatus.BAD_REQUEST
        error_message = "A chat message must have content."
        response = {
            ProtocolKey.ERROR: {
                ProtocolKey.ERROR_CODE: response_status.value,
                ProtocolKey.ERROR_MESSAGE: error_message
            }
        }
    else:
        response_status = ResponseStatus.OK

        if message_id:
            message: ChatMessage = ChatMessage.get_by_id(message_id)
        else:
            message = None

        md_extension_configs = {
            "pymdownx.highlight": {
                "auto_title": True,
                "auto_title_map": {
                    "Python Console Session": "Python"
                }
            }
        }

        if len(content_md) > Configuration.OPENAI_TOKEN_LIMIT - 100:
            response_status = ResponseStatus.BAD_REQUEST
            response = {
                ProtocolKey.ERROR: {
                    ProtocolKey.ERROR_CODE: ResponseStatus.CONTENT_MAX_LEN_EXCEEDED.value,
                    ProtocolKey.ERROR_MESSAGE: "Message exceeds maximum length allowed."
                }
            }

        if context_range_length and context_range_start and message_id:
            if context_range_start < 0 or \
                    context_range_start >= len(message.content_md) or \
                    context_range_length < 0 or \
                    context_range_start + context_range_length > len(message.content_md):
                response_status = ResponseStatus.BAD_REQUEST
                response = {
                    ProtocolKey.ERROR: {
                        ProtocolKey.ERROR_CODE: ResponseStatus.MESSAGE_CONTEXT_INVALID.value,
                        ProtocolKey.ERROR_MESSAGE: "The provided context range is invalid."
                    }
                }

        if response_status == ResponseStatus.OK:
            model_id = LLMOption.GPT3.value
            model = Model.get_by_id(model_id)
            creator = User.get_by_session(session_id)

            if creator:
                sender_id = creator.id
            else:
                sender_id = None

            if message_id:
                fork_message_id = message_id

                if context_range_length and context_range_start:
                    # Extract the context string from the quoted message using the given range.
                    soup = BeautifulSoup(message.content_html, "html.parser")
                    message_plain_text = soup.get_text()
                    context = message_plain_text[context_range_start:context_range_start + context_range_length]
                    # Prepend the context to the user's markdown.
                    content_md = f"###\n> {context}\n###\n{content_md}"
            else:
                fork_message_id = None

            topic = gpt.get_topic(content_md, model)
            chat: Chat = Chat.create(
                fork_message_id=fork_message_id,
                model_id=model_id,
                topic=topic,
                user_id=sender_id
            )

            if chat:
                if context_range_length and context_range_start and message_id:
                    # We need to hyperlink the selection in the message to the new chat.
                    md_start, md_end = _find_corresponding_markdown_indices(
                        message_plain_text,
                        message.content_md,
                        context_range_start,
                        context_range_length
                    )
                    updated_md = message.content_md[:md_start] + "[" + message.content_md[md_start:md_end] + f"](/c/{str(chat.id)})" + message.content_md[md_end:]
                    updated_html = markdown.markdown(
                        updated_md,
                        extensions=["pymdownx.superfences"],
                        extension_configs=md_extension_configs
                    )
                    message.content_html = updated_html
                    message.content_md = updated_md
                    message.update()

                content_html = markdown.markdown(
                    content_md,
                    extensions=["pymdownx.superfences"],
                    extension_configs=md_extension_configs
                )

                if message:
                    chat_history = message.get_all_prior()
                    chat.messages = chat_history

                first_user_message = ChatMessage.create(
                    chat.id,
                    content_html=content_html,
                    content_md=content_md,
                    sender_id=sender_id,
                    sender_role=ChatMessageSenderRole.USER
                )
                chat.messages.append(first_user_message)
                # Get a response from OpenAI.
                llm_response_md = gpt.chat(chat.messages, model)
                llm_response_html = markdown.markdown(
                    llm_response_md,
                    extensions=["pymdownx.superfences"],
                    extension_configs=md_extension_configs
                )

                llm_response: ChatMessage = ChatMessage.create(
                    chat_id=chat.id,
                    content_html=llm_response_html,
                    content_md=llm_response_md,
                    sender_role=ChatMessageSenderRole.ASSISTANT
                )
                chat.messages.append(llm_response)

                response = chat.as_dict()
            else:
                response_status = ResponseStatus.INTERNAL_SERVER_ERROR
                response = {
                    ProtocolKey.ERROR: {
                        ProtocolKey.ERROR_CODE: response_status.value,
                        ProtocolKey.ERROR_MESSAGE: "An internal server error occurred."
                    }
                }

    return (response, response_status)


def edit_chat_topic(chat_id: uuid.UUID,
                    topic: str) -> tuple[dict, ResponseStatus]:
    if topic:
        topic = topic.strip()

    if not chat_id:
        response_status = ResponseStatus.BAD_REQUEST
        response = {
            ProtocolKey.ERROR: {
                ProtocolKey.ERROR_CODE: ResponseStatus.BAD_REQUEST.value,
                ProtocolKey.ERROR_MESSAGE: "Missing chat ID."
            }
        }
    elif not topic:
        response_status = ResponseStatus.BAD_REQUEST
        response = {
            ProtocolKey.ERROR: {
                ProtocolKey.ERROR_CODE: ResponseStatus.BAD_REQUEST.value,
                ProtocolKey.ERROR_MESSAGE: "Missing topic."
            }
        }
    else:
        chat: Chat = Chat.get_by_id(chat_id)
        if chat:
            session_id = request.cookies.get(ProtocolKey.USER_SESSION_ID)
            session: UserSession = UserSession.get_by_id(session_id)
            user_id = session.user_id

            if chat.user_id == user_id:
                response_status = ResponseStatus.OK
                response = {}
                chat.set_topic(topic)
                # We're not updating the RAM copy stored in the chat namespace's sessions.
            else:
                response_status = ResponseStatus.FORBIDDEN
                response = {
                    ProtocolKey.ERROR: {
                        ProtocolKey.ERROR_CODE: response_status.value,
                        ProtocolKey.ERROR_MESSAGE: "Chat is not owned by this user."
                    }
                }
        else:
            response_status = ResponseStatus.NOT_FOUND
            response = {
                ProtocolKey.ERROR: {
                    ProtocolKey.ERROR_CODE: ResponseStatus.NOT_FOUND.value,
                    ProtocolKey.ERROR_MESSAGE: "No chat found for this chat ID."
                }
            }

    return (response, response_status)


def get_chats(session_id: str) -> tuple[list, ResponseStatus]:
    if session_id:
        response_status = ResponseStatus.OK
        session: UserSession = UserSession.get_by_id(session_id)
        user_id = session.user_id
        chats = Chat.get_all_by_user(user_id)
        chats_serialized = []
        for chat in chats:
            chats_serialized.append(chat.as_dict())
        response = chats_serialized
    else:
        response_status = ResponseStatus.BAD_REQUEST
        response = {
            ProtocolKey.ERROR: {
                ProtocolKey.ERROR_CODE: ResponseStatus.BAD_REQUEST.value,
                ProtocolKey.ERROR_MESSAGE: "Missing session ID."
            }
        }

    return (response, response_status)


def remove(session_id: str,
           chat_id: uuid.UUID):
    if not chat_id:
        response_status = ResponseStatus.BAD_REQUEST
        response = {
            ProtocolKey.ERROR: {
                ProtocolKey.ERROR_CODE: response_status.value,
                ProtocolKey.ERROR_MESSAGE: "Missing argument: 'chat_id'."
            }
        }
    else:
        chat: Chat = Chat.get_by_id(chat_id)
        if chat:
            current_account = User.get_by_session(session_id)
            if current_account and current_account.id == chat.user_id:
                chat.delete()
                response_status = ResponseStatus.OK
                response = {}
            else:
                response_status = ResponseStatus.UNAUTHORIZED
                response = {
                    ProtocolKey.ERROR: {
                        ProtocolKey.ERROR_CODE: response_status.value,
                        ProtocolKey.ERROR_MESSAGE: "Only the chat creator can delete their post."
                    }
                }
        else:
            response_status = ResponseStatus.NOT_FOUND
            response = {
                ProtocolKey.ERROR: {
                    ProtocolKey.ERROR_CODE: response_status.value,
                    ProtocolKey.ERROR_MESSAGE: "No chat exists for the given ID."
                }
            }

    return (response, response_status)


chat_purge_scheduled_task = ChatPurgeJob()
chat_purge_scheduled_task.start()

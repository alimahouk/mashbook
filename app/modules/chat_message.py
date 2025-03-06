from datetime import datetime
from flask import request
from typing import TypeVar, Type
import uuid

from app.config import (ChatMessageSenderRole, DatabaseTable, ProtocolKey,
                        ResponseStatus)
from app.modules.db import RelationalDB
from app.modules.user import User


###########
# CLASSES #
###########


T = TypeVar("T", bound="ChatMessage")


class ChatMessage:
    def __init__(self,
                 data: dict) -> None:
        self.chat_id: uuid.UUID = None
        self.content_html: str = None
        self.content_md: str = None
        self.creation_timestamp: datetime = None
        self.id: uuid.UUID = None
        self.sender_id: int = None
        self.sender: User = None
        self.sender_role: ChatMessageSenderRole = None

        if ProtocolKey.CHAT_ID in data:
            self.chat_id: uuid.UUID = data[ProtocolKey.CHAT_ID]

        if ProtocolKey.CONTENT_HTML in data:
            self.content_html: str = data[ProtocolKey.CONTENT_HTML]

        if ProtocolKey.CONTENT_MARKDOWN in data:
            self.content_md: str = data[ProtocolKey.CONTENT_MARKDOWN]

        if ProtocolKey.CREATION_TIMESTAMP in data:
            self.creation_timestamp: datetime = data[ProtocolKey.CREATION_TIMESTAMP]

        if ProtocolKey.ID in data:
            self.id: uuid.UUID = data[ProtocolKey.ID]

        if ProtocolKey.SENDER in data:
            self.sender: User = User(data[ProtocolKey.SENDER])

        if ProtocolKey.SENDER_ID in data:
            self.sender_id: int = data[ProtocolKey.SENDER_ID]

        if ProtocolKey.SENDER_ROLE in data:
            self.sender_role = ChatMessageSenderRole(data[ProtocolKey.SENDER_ROLE])

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
            ret += f"Chat Message {self.id}: {self.content_md}"
        return ret

    def as_dict(self) -> dict:
        serialized = {
            ProtocolKey.CHAT_ID: str(self.chat_id),
            ProtocolKey.CONTENT_HTML: self.content_html,
            ProtocolKey.CONTENT_MARKDOWN: self.content_md,
            ProtocolKey.ID: str(self.id),
            ProtocolKey.SENDER_ROLE: self.sender_role.value
        }

        if self.creation_timestamp:
            serialized[ProtocolKey.CREATION_DATE] = self.creation_timestamp.strftime("%e %b %Y")
            serialized[ProtocolKey.CREATION_TIMESTAMP] = self.creation_timestamp.astimezone().isoformat()

        if self.sender:
            serialized[ProtocolKey.SENDER] = self.sender.as_dict()

        if self.sender_id:
            serialized[ProtocolKey.SENDER_ID] = self.sender_id

        return serialized

    def chat_format(self) -> str:
        if self.sender_role.value == ChatMessageSenderRole.ASSISTANT:
            role = "you"
        else:
            role = self.sender_role.value
        return f"{role}: {self.content_md}"

    @classmethod
    def create(cls: Type,
               chat_id: uuid.UUID = None,
               content_html: str = None,
               content_md: str = None,
               sender_id: int = None,
               sender_role: ChatMessageSenderRole = None) -> T:
        """
        Call this method to create a ChatMessage object.
        """

        if not isinstance(chat_id, uuid.UUID):
            raise TypeError(f"Argument 'chat_id' must be of type UUID, not {type(chat_id)}.")

        if not isinstance(content_html, str):
            raise TypeError(f"Argument 'content_html' must be of type str, not {type(content_html)}.")

        content_html = content_html.strip()
        if not content_html:
            raise ValueError("Argument 'content_html' must be a non-empty string.")

        if not isinstance(content_md, str):
            raise TypeError(f"Argument 'content_md' must be of type str, not {type(content_md)}.")

        content_md = content_md.strip()
        if not content_md:
            raise ValueError("Argument 'content_md' must be a non-empty string.")

        if sender_id and not isinstance(sender_id, int):
            raise TypeError(f"Argument 'sender_id' must be of type int, not {type(sender_id)}.")

        if sender_id and sender_id <= 0:
            raise ValueError("Argument 'sender_id' must be a positive, non-zero integer.")

        if not isinstance(sender_role, ChatMessageSenderRole):
            raise TypeError(f"Argument 'sender_role' must be of type ChatMessageSenderRole, not {type(sender_role)}.")

        ret: Type = None
        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            if sender_id:
                cursor.execute(
                    f"""
                    INSERT INTO
                        {DatabaseTable.CHAT_MESSAGE}
                        ({ProtocolKey.CHAT_ID}, {ProtocolKey.CONTENT_HTML}, {ProtocolKey.CONTENT_MARKDOWN},
                        {ProtocolKey.SENDER_ID}, {ProtocolKey.SENDER_ROLE})
                    VALUES
                        (%s, %s, %s,
                         %s, %s)
                    RETURNING *;
                    """,
                    (chat_id, content_html, content_md,
                     sender_id, sender_role.value)
                )
            else:
                cursor.execute(
                    f"""
                    INSERT INTO
                        {DatabaseTable.CHAT_MESSAGE}
                        ({ProtocolKey.CHAT_ID}, {ProtocolKey.CONTENT_HTML}, {ProtocolKey.CONTENT_MARKDOWN},
                        {ProtocolKey.SENDER_ROLE})
                    VALUES
                        (%s, %s, %s,
                         %s)
                    RETURNING *;
                    """,
                    (chat_id, content_html, content_md,
                     sender_role.value)
                )
            result = cursor.fetchone()
            db.connection.commit()
            if result:
                ret = cls(result)
                if sender_id:
                    ret.sender = User.get_by_id(sender_id)
        except Exception as e:
            print(e)
        finally:
            db.close()

        return ret

    @classmethod
    def get_all_by_chat(cls: Type,
                        chat_id: uuid.UUID,
                        offset: int = 0) -> list:
        """
        Returns the last 20 messages in chronological order.
        """

        if not isinstance(chat_id, uuid.UUID):
            raise TypeError(f"Argument 'chat_id' must be of type UUID, not {type(chat_id)}.")

        ret = []
        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                SELECT
                    *
                FROM (
                    SELECT 
                        c.*,
                        u.{ProtocolKey.USER}
                    FROM 
                        {DatabaseTable.CHAT_MESSAGE} AS c
                    LEFT JOIN (
                        SELECT
                            {ProtocolKey.ID},
                            ROW_TO_JSON(u) AS {ProtocolKey.USER}
                        FROM 
                            {DatabaseTable.USER} AS u
                    ) AS u ON c.{ProtocolKey.SENDER_ID} = u.{ProtocolKey.ID}
                    WHERE
                        c.{ProtocolKey.CHAT_ID} = %s
                    ORDER BY
                        c.{ProtocolKey.CREATION_TIMESTAMP} DESC
                    OFFSET
                        %s) AS sub
                ORDER BY
                    {ProtocolKey.CREATION_TIMESTAMP} ASC;
                """,
                (chat_id, offset)
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

    def get_all_prior(self) -> list:
        if not self.id:
            raise ValueError(f"Missing message ID.")

        ret = []
        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                SELECT
                    *
                FROM (
                    SELECT 
                        c.*,
                        u.{ProtocolKey.USER}
                    FROM 
                        {DatabaseTable.CHAT_MESSAGE} AS c
                    LEFT JOIN (
                        SELECT
                            {ProtocolKey.ID},
                            ROW_TO_JSON(u) AS {ProtocolKey.USER}
                        FROM 
                            {DatabaseTable.USER} AS u
                    ) AS u ON c.{ProtocolKey.SENDER_ID} = u.{ProtocolKey.ID}
                    WHERE
                        c.{ProtocolKey.CHAT_ID} = %s AND c.{ProtocolKey.CREATION_TIMESTAMP} <= %s
                    ORDER BY
                        c.{ProtocolKey.CREATION_TIMESTAMP} ASC
                    LIMIT
                        100) AS sub
                ORDER BY
                    {ProtocolKey.CREATION_TIMESTAMP} ASC;
                """,
                (self.chat_id, self.creation_timestamp)
            )
            results = cursor.fetchall()
            db.connection.commit()
            for result in results:
                ret.append(ChatMessage(result))
        except Exception as e:
            print(e)
        finally:
            db.close()

        return ret

    @classmethod
    def get_by_id(cls: Type,
                  message_id: uuid.UUID) -> T:
        if not isinstance(message_id, uuid.UUID):
            raise TypeError(f"Argument 'message_id' must be of type UUID, not {type(message_id)}.")

        ret: Type = None
        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                SELECT
                    *
                FROM
                    {DatabaseTable.CHAT_MESSAGE}
                WHERE
                    {ProtocolKey.ID} = %s;
                """,
                (message_id,)
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

    def prompt_format(self) -> dict:
        serialized = {
            "content": self.content_md,
            "role": self.sender_role.value
        }
        return serialized

    def update(self) -> None:
        if not self.id:
            raise ValueError(f"Missing message ID.")

        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                UPDATE
                    {DatabaseTable.CHAT_MESSAGE}
                SET
                    {ProtocolKey.CONTENT_HTML} = %s, {ProtocolKey.CONTENT_MARKDOWN} = %s
                WHERE
                    {ProtocolKey.ID} = %s;
                """,
                (self.content_html, self.content_md, self.id)
            )
            db.connection.commit()
        except Exception as e:
            print(e)
        finally:
            db.close()


####################
# MODULE FUNCTIONS #
####################


def get_chat(chat_id: str,
             offset: str = 0) -> list:
    if chat_id:
        try:
            chat_id = int(chat_id)
        except:
            chat_id = None

    if offset:
        try:
            offset = int(offset)
        except:
            offset = 0
    else:
        offset = 0

    if not chat_id:
        response_status = ResponseStatus.BAD_REQUEST
        response = {
            ProtocolKey.ERROR: {
                ProtocolKey.ERROR_CODE: ResponseStatus.BAD_REQUEST.value,
                ProtocolKey.ERROR_MESSAGE: "Missing chat ID."
            }
        }
    else:
        session_id = request.cookies.get(ProtocolKey.USER_SESSION_ID)
        if session_id:
            response_status = ResponseStatus.OK
            messages = ChatMessage.get_all_by_chat(chat_id, offset=offset)
            messages_serialized = []
            for message in messages:
                messages_serialized.append(message.as_dict())
            response = messages_serialized
        else:
            response_status = ResponseStatus.BAD_REQUEST
            response = {
                ProtocolKey.ERROR: {
                    ProtocolKey.ERROR_CODE: ResponseStatus.BAD_REQUEST.value,
                    ProtocolKey.ERROR_MESSAGE: "Missing session ID."
                }
            }

    return (response, response_status)

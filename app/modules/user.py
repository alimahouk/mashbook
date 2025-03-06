from datetime import datetime
from dateutil import parser as date_parser
from flask import request
import hashlib
import re
import string
from typing import Any, TypeVar, Type

from app.config import (DatabaseTable, ProtocolKey,
                        ResponseStatus)
from app.modules import user_session, util
from app.modules.db import RelationalDB
from app.modules.user_session import UserSession


###########
# CLASSES #
###########


T = TypeVar("T", bound="User")


class User:
    def __init__(self,
                 data: dict) -> None:
        self.creation_timestamp: datetime = None
        self.email_address: str = None
        self.id: int = None
        self.password: str = None
        self.salt: str = None
        self.sessions: list[UserSession] = []

        if data:
            if ProtocolKey.CREATION_TIMESTAMP in data and data[ProtocolKey.CREATION_TIMESTAMP]:
                creation_timestamp = data[ProtocolKey.CREATION_TIMESTAMP]
                if isinstance(creation_timestamp, datetime):
                    self.creation_timestamp: datetime = creation_timestamp
                elif isinstance(creation_timestamp, str):
                    self.creation_timestamp: datetime = date_parser.parse(creation_timestamp)

            if ProtocolKey.EMAIL_ADDRESS in data:
                self.email_address: str = data[ProtocolKey.EMAIL_ADDRESS]

            if ProtocolKey.ID in data:
                self.id: str = data[ProtocolKey.ID]

            if ProtocolKey.PASSWORD in data:
                self.password: str = data[ProtocolKey.PASSWORD]

            if ProtocolKey.SALT in data and data[ProtocolKey.SALT]:
                self.salt: str = data[ProtocolKey.SALT]

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
            ret += f"User {self.id}"
        return ret

    def as_dict(self,
                is_public=True) -> dict[ProtocolKey, Any]:
        serialized = {
            ProtocolKey.EMAIL_ADDRESS: self.email_address,
            ProtocolKey.ID: self.id
        }

        if self.creation_timestamp:
            serialized[ProtocolKey.CREATION_TIMESTAMP] = self.creation_timestamp.astimezone().isoformat()

        if not is_public and self.sessions:
            sessions_serialized = []
            for session in self.sessions:
                sessions_serialized.append(session.as_dict())

            serialized[ProtocolKey.USER_SESSIONS] = sessions_serialized

        return serialized

    @classmethod
    def create(cls: Type[T],
               email_address: str,
               password: str,
               salt: str) -> T:
        if not isinstance(email_address, str):
            raise TypeError(f"Argument 'email_address' must be of type str, not {type(email_address)}.")

        if not email_address:
            raise ValueError("Argument 'email_address' must be a non-empty string.")

        if not isinstance(password, str):
            raise TypeError(f"Argument 'password' must be of type str, not {type(password)}.")

        if not password:
            raise ValueError("Argument 'password' must be a non-empty string.")

        if not isinstance(salt, str):
            raise TypeError(f"Argument 'salt' must be of type str, not {type(salt)}.")

        if not salt:
            raise ValueError("Argument 'salt' must be a non-empty string.")

        ret: Type[T] = None
        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                INSERT INTO
                    {DatabaseTable.USER}
                    ({ProtocolKey.EMAIL_ADDRESS}, {ProtocolKey.PASSWORD}, {ProtocolKey.SALT})
                VALUES
                    (%s, %s, %s)
                RETURNING
                    *;
                """,
                (email_address, password, salt)
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
    def email_valid(email_address: str) -> bool:
        ret = True
        if not email_address or not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email_address):
            ret = False
        return ret

    @classmethod
    def get_by_email(cls: Type,
                     email_address: str) -> T | None:
        if not isinstance(email_address, str):
            raise TypeError(f"Argument 'email_address' must be of type str, not {type(email_address)}.")

        ret: Type = None
        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                SELECT
                    *
                FROM
                    {DatabaseTable.USER}
                WHERE
                    {ProtocolKey.EMAIL_ADDRESS} = %s;
                """,
                (email_address,)
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

    @classmethod
    def get_by_id(cls: Type,
                  user_id: int) -> T | None:
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
                SELECT
                    *
                FROM
                    {DatabaseTable.USER}
                WHERE
                    {ProtocolKey.ID} = %s;
                """,
                (user_id,)
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

    @classmethod
    def get_by_session(cls: Type[T],
                       session_id: int) -> T | None:
        if not isinstance(session_id, str):
            raise TypeError(f"Argument 'session_id' must be of type str, not {type(session_id)}.")

        if not session_id:
            raise ValueError("Argument 'session_id' must be a non-empty string.")

        ret: Type[T] = None
        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                SELECT
                    *
                FROM
                    {DatabaseTable.USER_SESSION}
                LEFT JOIN
                    {DatabaseTable.USER}
                ON
                    {DatabaseTable.USER_SESSION}.{ProtocolKey.USER_ID} = {DatabaseTable.USER}.{ProtocolKey.ID}
                WHERE
                    {DatabaseTable.USER_SESSION}.{ProtocolKey.ID} = %s;
                """,
                (session_id,)
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


####################
# MODULE FUNCTIONS #
####################


def get_account(email_address: str = None,
                account_id: str = None) -> tuple[dict, ResponseStatus]:
    if account_id:
        try:
            account_id = int(account_id)

            if account_id <= 0:
                account_id = None
        except ValueError:
            account_id = None

    if not email_address and \
            not account_id:
        response_status = ResponseStatus.BAD_REQUEST
        error_message = "Invalid or missing parameter: 'email_address' must be a non-empty string or 'account_id' must be a positive, non-zero integer."

        response = {
            ProtocolKey.ERROR: {
                ProtocolKey.ERROR_CODE: response_status.value,
                ProtocolKey.ERROR_MESSAGE: error_message
            }
        }
    else:
        response_status = ResponseStatus.OK
        response = {}
        if account_id:
            user_account = User.get_by_id(account_id)
        else:
            if User.email_valid(email_address):
                user_account = User.get_by_email(email_address)
            else:
                # Invalid email.
                response_status = ResponseStatus.BAD_REQUEST
                response = {
                    ProtocolKey.ERROR: {
                        ProtocolKey.ERROR_CODE: ResponseStatus.EMAIL_FORMAT_INVALID.value,
                        ProtocolKey.ERROR_MESSAGE: f"Email_address format is invalid."
                    }
                }

        if response_status == ResponseStatus.OK:
            if user_account:
                response = {
                    ProtocolKey.USER: user_account.as_dict()
                }
            else:
                response_status = ResponseStatus.NOT_FOUND
                response = {
                    ProtocolKey.ERROR: {
                        ProtocolKey.ERROR_CODE: ResponseStatus.USER_NOT_FOUND.value,
                        ProtocolKey.ERROR_MESSAGE: "No user account exists for this ID."
                    }
                }

    return (response, response_status)


def get_current() -> tuple[dict, ResponseStatus]:
    session_id = request.cookies.get(ProtocolKey.USER_SESSION_ID.value)
    if session_id:
        current_user = User.get_by_session(session_id)

        if current_user:
            response_status = ResponseStatus.OK
            response = {
                ProtocolKey.USER: current_user.as_dict(is_public=False)
            }
        else:
            response_status = ResponseStatus.NOT_FOUND
            response = {
                ProtocolKey.ERROR: {
                    ProtocolKey.ERROR_CODE: ResponseStatus.USER_NOT_FOUND.value,
                    ProtocolKey.ERROR_MESSAGE: "No user exists for this ID."
                }
            }
    else:
        response_status = ResponseStatus.BAD_REQUEST
        response = {
            ProtocolKey.ERROR: {
                ProtocolKey.ERROR_CODE: response_status.value,
                ProtocolKey.ERROR_MESSAGE: "Invalid session."
            }
        }

    return (response, response_status)


def join(email_address: str,
         password: str) -> tuple[dict, ResponseStatus]:
    """
    For new users signing up.
    """

    if email_address:
        email_address = "".join(char for char in email_address if char in string.printable)
    else:
        email_address = None

    if not email_address or \
            not password:
        response_status = ResponseStatus.BAD_REQUEST
        error_message = "Invalid or missing parameter"

        if not email_address:
            error_message += ": 'email_address' must be a non-empty string."
        elif not password:
            error_message += ": 'password' must be a non-empty string."

        response = {
            ProtocolKey.ERROR: {
                ProtocolKey.ERROR_CODE: response_status.value,
                ProtocolKey.ERROR_MESSAGE: error_message
            }
        }
    else:
        response_status = ResponseStatus.OK
        response = {}

        if User.email_valid(email_address):
            user = User.get_by_email(email_address)
            if not user:
                salt = util.generate_salt()
                hashed_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
                hashed_password += salt
                hashed_password = hashlib.sha256(hashed_password.encode("utf-8")).hexdigest()

                new_account = User.create(email_address, hashed_password, salt)
                new_session = user_session.create_session(new_account.id)
                if new_session:
                    response = {
                        ProtocolKey.USER: new_account.as_dict(is_public=False),
                        ProtocolKey.USER_SESSION: {
                            ProtocolKey.CREATION_TIMESTAMP: new_session.creation_timestamp,
                            ProtocolKey.ID: new_session.id,
                            ProtocolKey.USER_ID: new_account.id
                        }
                    }
            else:
                # Invalid email.
                response_status = ResponseStatus.BAD_REQUEST
                response = {
                    ProtocolKey.ERROR: {
                        ProtocolKey.ERROR_CODE: ResponseStatus.EMAIL_IN_USE.value,
                        ProtocolKey.ERROR_MESSAGE: f"A user already exists for this email address."
                    }
                }
        else:
            # Invalid email.
            response_status = ResponseStatus.BAD_REQUEST
            response = {
                ProtocolKey.ERROR: {
                    ProtocolKey.ERROR_CODE: ResponseStatus.EMAIL_FORMAT_INVALID.value,
                    ProtocolKey.ERROR_MESSAGE: f"Email address format is invalid."
                }
            }

    return (response, response_status)


def log_in(email_address: str,
           password: str) -> tuple[dict, ResponseStatus]:
    if email_address:
        email_address = "".join(char for char in email_address if char in string.printable)
    else:
        email_address = None

    if not email_address or \
            not password:
        response_status = ResponseStatus.BAD_REQUEST
        error_message = "Invalid or missing parameter"

        if not email_address:
            error_message += ": 'email_address' must be an ASCII non-empty string."
        elif not password:
            error_message += ": 'password' must be a non-empty string."

        response = {
            ProtocolKey.ERROR: {
                ProtocolKey.ERROR_CODE: response_status.value,
                ProtocolKey.ERROR_MESSAGE: error_message
            }
        }
    else:
        response_status = ResponseStatus.OK
        response = {}

        account: User = User.get_by_email(email_address)
        if account:
            hashed_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
            hashed_password += account.salt
            hashed_password = hashlib.sha256(hashed_password.encode("utf-8")).hexdigest()

            if hashed_password == account.password:
                new_session = user_session.create_session(account.id)
                response = {
                    ProtocolKey.USER: account.as_dict(is_public=False),
                    ProtocolKey.USER_SESSION: {
                        ProtocolKey.CREATION_TIMESTAMP: new_session.creation_timestamp,
                        ProtocolKey.ID: new_session.id,
                        ProtocolKey.USER_ID: account.id
                    }
                }
            else:
                response_status = ResponseStatus.BAD_REQUEST
                response = {
                    ProtocolKey.ERROR: {
                        ProtocolKey.ERROR_CODE: ResponseStatus.CREDENTIALS_INVALID.value,
                        ProtocolKey.ERROR_MESSAGE: "Entered username/password is incorrect."
                    }
                }
        else:
            response_status = ResponseStatus.BAD_REQUEST
            response = {
                ProtocolKey.ERROR: {
                    ProtocolKey.ERROR_CODE: ResponseStatus.CREDENTIALS_INVALID.value,
                    ProtocolKey.ERROR_MESSAGE: "Entered username/password is incorrect."
                }
            }

    return (response, response_status)


def log_out() -> tuple[dict, ResponseStatus]:
    session_id = request.cookies.get(ProtocolKey.USER_SESSION_ID)
    if session_id:
        session = UserSession.get_by_id(session_id)
    else:
        session = None

    if session:
        session.delete()
        response_status = ResponseStatus.OK
        response = {
            ProtocolKey.USER_ID: session.user_id
        }
    else:
        response_status = ResponseStatus.UNAUTHORIZED
        response = {
            ProtocolKey.ERROR: {
                ProtocolKey.ERROR_CODE: response_status.value,
                ProtocolKey.ERROR_MESSAGE: "Cannot log out; this is an invalid session."
            }
        }

    return (response, response_status)

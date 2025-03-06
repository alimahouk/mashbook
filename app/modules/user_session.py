from datetime import datetime
from dateutil import parser as date_parser
import hashlib
import ipaddress
from typing import Any, TypeVar, Type
import uuid

from app.config import DatabaseTable, ProtocolKey, ResponseStatus
from app.modules import util
from app.modules.db import RelationalDB


###########
# CLASSES #
###########


T = TypeVar("T", bound="UserSession")


class UserSession:
    def __init__(self,
                 data: dict) -> None:
        self.creation_timestamp: datetime = None
        self.id: str = None
        self.ip_address: ipaddress.IPv4Address = None
        self.last_activity: datetime = None
        self.location: str = None
        self.mac_address: str = None
        self.user_id: int = None

        if data:
            if ProtocolKey.CREATION_TIMESTAMP in data:
                self.creation_timestamp: datetime = data[ProtocolKey.CREATION_TIMESTAMP]

            if ProtocolKey.ID in data:
                self.id: str = data[ProtocolKey.ID]

            if ProtocolKey.IP_ADDRESS in data and data[ProtocolKey.IP_ADDRESS]:
                self.ip_address: ipaddress.IPv4Address = ipaddress.ip_address(data[ProtocolKey.IP_ADDRESS])

            if ProtocolKey.LAST_ACTIVITY in data and data[ProtocolKey.LAST_ACTIVITY]:
                last_activity = data[ProtocolKey.LAST_ACTIVITY]
                if isinstance(last_activity, datetime):
                    self.last_activity: datetime = last_activity
                elif isinstance(last_activity, str):
                    self.last_activity: datetime = date_parser.parse(last_activity)

            if ProtocolKey.LOCATION in data:
                self.location: str = data[ProtocolKey.LOCATION]

            if ProtocolKey.MAC_ADDRESS in data and data[ProtocolKey.MAC_ADDRESS]:
                self.mac_address: str = data[ProtocolKey.MAC_ADDRESS]

            if ProtocolKey.USER_ID in data:
                self.user_id: int = data[ProtocolKey.USER_ID]

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
            ret += f"User Account {self.user_id} Session {self.id}"

        return ret

    def as_dict(self) -> dict[ProtocolKey, Any]:
        serialized = {
            ProtocolKey.ID: self.id,
            ProtocolKey.LOCATION: self.location,
            ProtocolKey.USER_ID: self.user_id
        }

        if self.creation_timestamp:
            serialized[ProtocolKey.CREATION_TIMESTAMP] = self.creation_timestamp.astimezone().isoformat()

        if self.ip_address:
            serialized[ProtocolKey.IP_ADDRESS] = str(self.ip_address)

        if self.last_activity:
            serialized[ProtocolKey.LAST_ACTIVITY] = self.last_activity.astimezone().isoformat()

        if self.mac_address:
            serialized[ProtocolKey.MAC_ADDRESS] = self.mac_address

        return serialized

    @classmethod
    def create(cls: Type[T],
               user_id: int) -> T:
        """
        Call this method to create a session object then populate its
        fields and call its update() method.
        """

        if not isinstance(user_id, int):
            raise TypeError(f"Argument 'user_id' must be of type int, not {type(user_id)}.")

        if user_id <= 0:
            raise ValueError("Argument 'user_id' must be a positive, non-zero integer.")

        ret: Type[T] = None
        db = RelationalDB()
        try:
            session_id = cls.generate_id()
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                INSERT INTO
                    {DatabaseTable.USER_SESSION}
                    ({ProtocolKey.ID}, {ProtocolKey.USER_ID})
                VALUES
                    (%s, %s)
                RETURNING
                    *;
                """,
                (session_id, user_id)
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

    def delete(self) -> None:
        if not self.id:
            raise Exception("Deletion requires a session ID.")

        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                DELETE FROM
                    {DatabaseTable.USER_SESSION}
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

    @staticmethod
    def exists(session_id: str) -> bool:
        if not isinstance(session_id, str):
            raise TypeError(f"Argument 'session_id' must be of type str, not {type(session_id)}.")

        if not session_id:
            raise ValueError("Argument 'session_id' must be a non-empty string.")

        ret = False
        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                SELECT
                    *
                FROM
                    {DatabaseTable.USER_SESSION}
                WHERE
                    {ProtocolKey.ID} = %s;
                """,
                (session_id,)
            )
            result = cursor.fetchone()
            db.connection.commit()
            if result:
                ret = True
        except Exception as e:
            print(e)
        finally:
            db.close()

        return ret

    @staticmethod
    def delete_all_for_user(user_id: int) -> None:
        if not isinstance(user_id, int):
            raise TypeError(f"Argument 'user_id' must be of type int, not {type(user_id)}.")

        if user_id <= 0:
            raise ValueError("Argument 'user_id' must be a positive, non-zero integer.")

        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                DELETE FROM
                    {DatabaseTable.USER_SESSION}
                WHERE
                    {ProtocolKey.USER_ID} = %s;
                """,
                (user_id,)
            )
            db.connection.commit()
        except Exception as e:
            print(e)
        finally:
            db.close()

    @classmethod
    def get_all_for_user(cls: Type[T],
                         user_id: int) -> list[T]:
        if not isinstance(user_id, int):
            raise TypeError(f"Argument 'user_id' must be of type int, not {type(user_id)}")

        if user_id <= 0:
            raise ValueError("Argument 'user_id' must be a positive, non-zero integer.")

        ret = []
        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                SELECT
                    *
                FROM
                    {DatabaseTable.USER_SESSION}
                WHERE
                    {ProtocolKey.USER_ID} = %s;
                """,
                (user_id,)
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
    def get_by_id(cls: Type[T],
                  session_id: str) -> T | None:
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
                WHERE
                    {ProtocolKey.ID} = %s;
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

    @staticmethod
    def generate_id() -> str:
        """
        Generates a session ID.
        """

        rand = uuid.uuid4().hex
        return hashlib.sha256(rand.encode("utf-8")).hexdigest()

    def update(self) -> None:
        if not self.id or not self.user_id:
            raise Exception("Updating requires a session ID and user account ID.")

        db = RelationalDB()
        try:
            if self.ip_address:
                if isinstance(self.ip_address, ipaddress.IPv4Address):
                    ip_address = str(self.ip_address)
                else:
                    ip_address = self.ip_address
            else:
                ip_address = None

            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                UPDATE
                    {DatabaseTable.USER_SESSION}
                SET
                    {ProtocolKey.LAST_ACTIVITY} = %s, {ProtocolKey.IP_ADDRESS} = %s, {ProtocolKey.MAC_ADDRESS} = %s,
                    {ProtocolKey.LOCATION} = %s
                WHERE
                    {ProtocolKey.ID} = %s AND {ProtocolKey.USER_ID} = %s;
                """,
                (self.last_activity, ip_address, self.mac_address,
                 self.location, self.id, self.user_id)
            )
            db.connection.commit()
        except Exception as e:
            print(e)
        finally:
            db.close()

####################
# MODULE FUNCTIONS #
####################


def create_session(user_id: int) -> UserSession:
    if not isinstance(user_id, int):
        raise TypeError(f"Argument 'user_id' must be of type int, not {type(user_id)}")

    if user_id <= 0:
        raise ValueError("Argument 'user_id' must be a positive, non-zero integer.")

    new_session = UserSession.create(user_id)
    return new_session


def update_session(session_id: str) -> tuple[dict, ResponseStatus]:
    """
    Gather details about the current session and update
    them in the database.
    """

    if session_id:
        session = UserSession.get_by_id(session_id)
        if session:
            ip_address = util.get_current_ip_address()
            session.ip_address = ip_address
            session.last_activity = datetime.utcnow()
            session.location = util.determine_location(ip_address)
            session.mac_address = util.determine_mac_address(ip_address)

            session.update()
            response_status = ResponseStatus.OK
            response = {
                ProtocolKey.USER_ID: session.user_id
            }
        else:
            response_status = ResponseStatus.UNAUTHORIZED
            response = {
                ProtocolKey.ERROR: {
                    ProtocolKey.ERROR_CODE: ResponseStatus.SESSION_INVALID.value,
                    ProtocolKey.ERROR_MESSAGE: "Session is not associated with any registered user account."
                }
            }
    else:
        response_status = ResponseStatus.UNAUTHORIZED
        response = {
            ProtocolKey.ERROR: {
                ProtocolKey.ERROR_CODE: ResponseStatus.SESSION_INVALID.value,
                ProtocolKey.ERROR_MESSAGE: "Invalid session."
            }
        }

    return (response, response_status)

from typing import TypeVar, Type

from app.config import DatabaseTable, ProtocolKey, ResponseStatus
from app.modules.db import RelationalDB


###########
# CLASSES #
###########


T = TypeVar("T", bound="Model")


class Model:
    def __init__(self,
                 data: dict) -> None:
        self.id: int = None
        self.name: str = None

        if data:
            if ProtocolKey.ID in data:
                self.id: str = data[ProtocolKey.ID]

            if ProtocolKey.NAME in data:
                self.name: str = data[ProtocolKey.NAME]

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
        return self.name

    def as_dict(self) -> dict:
        serialized = {
            ProtocolKey.ID: self.id,
            ProtocolKey.NAME: self.name,
        }
        return serialized

    @classmethod
    def get_all(cls: Type) -> list:
        ret = []
        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                SELECT
                    *
                FROM
                    {DatabaseTable.MODEL};
                """
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
                  model_id: int) -> T:
        if not isinstance(model_id, int):
            raise TypeError(f"Argument 'model_id' must be of type int, not {type(model_id)}.")

        if model_id <= 0:
            raise ValueError("Argument 'model_id' must be a positive, non-zero integer.")

        ret: Type = None
        db = RelationalDB()
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                f"""
                SELECT
                    *
                FROM
                    {DatabaseTable.MODEL}
                WHERE
                    {ProtocolKey.ID} = %s;
                """,
                (model_id,)
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


def get_models() -> list:
    models = Model.get_all()
    models_serialized = []
    for model in models:
        models_serialized.append(model.as_dict())

    response_status = ResponseStatus.OK
    response = models_serialized

    return (response, response_status)

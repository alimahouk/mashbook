import psycopg2
from psycopg2.extras import RealDictCursor, register_uuid

from app.config import Configuration


class RelationalDB:
    def __init__(self) -> None:
        self.connection = None
        self.cursor = None

        if Configuration.DEBUG:
            host = "localhost"
            password = ""
        else:
            host = Configuration.AWS_EC2_PROD_DATABASE_01
            password = ""

        try:
            self.connection = psycopg2.connect(
                host=host,
                database=Configuration.DATABASE_NAME,
                user=Configuration.DATABASE_USER,
                password=password,
                cursor_factory=RealDictCursor
            )
            register_uuid()
            self.cursor = self.connection.cursor()
        except Exception as e:
            print(e)
            self.close()

    def close(self):
        if self.cursor:
            self.cursor.close()

        if self.connection:
            self.connection.close()

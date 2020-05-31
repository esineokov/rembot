import re
import tarantool
from config import config


def result_to_list_dicts(schema, result):
    """ trtn = tarantool results to namedtuple """
    fields = [
        k for k, v in result.conn.schema.schema[schema].format.items() if type(k) == str
    ]
    return [dict(zip(fields, row)) for row in result]


class Tarantool(object):
    def __init__(self, host=None, port=None, user=None, password=None, space=None):
        self.connection = tarantool.connect(
            host=host, port=port, user=user, password=password
        )
        self.space = space
        self.connection.ping()

    def __getattribute__(self, item):
        def wrapper(*args, **kwargs):
            return result_to_list_dicts(
                self.space, object.__getattribute__(self, item)(*args, **kwargs)
            )

        if re.match("^(select|upsert|delete)", item):
            return wrapper
        else:
            return object.__getattribute__(self, item)


class Users(Tarantool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, space="users")

    def upsert(self, user_id, time_zone):
        return self.connection.upsert(
            space_name=self.space,
            tuple_value=(user_id, time_zone),
            op_list=[("=", 1, time_zone)],
        )

    def select(self, user_id):
        return self.connection.select(
            space_name=self.space, index="user_id", key=[user_id]
        )


class Chats(Tarantool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, space="chats")

    def upsert(self, chat_id, time_zone):
        return self.connection.upsert(
            space_name=self.space,
            tuple_value=(chat_id, time_zone),
            op_list=[("=", 1, time_zone)],
        )

    def select(self, chat_id):
        return self.connection.select(
            space_name=self.space, index="chat_id", key=[chat_id]
        )


class Notes(Tarantool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, space="notes")

    def upsert(self, user_id, chat_id, msg_id, timestamp):
        return self.connection.upsert(
            space_name=self.space,
            tuple_value=(user_id, chat_id, msg_id, timestamp),
            op_list=[("=", 3, timestamp)],
        )

    def select_by_uniq(self, user_id, chat_id, msg_id):
        return self.connection.select(
            space_name=self.space, index="uniq", key=[user_id, chat_id, msg_id]
        )

    def select_by_chat_id(self, chat_id):
        return self.connection.select(
            space_name=self.space, index="chat_id", key=[chat_id]
        )

    def select_by_user_chat(self, user_id, chat_id):
        return self.connection.select(
            space_name=self.space, index="user_chat", key=[user_id, chat_id]
        )

    def delete(self, user_id, chat_id, msg_id):
        return self.connection.delete(
            space_name=self.space, index="uniq", key=[user_id, chat_id, msg_id]
        )

    def select(self):
        return self.connection.select(space_name=self.space)


db_users = Users(host=config["tarantool"]["host"], port=config["tarantool"]["port"])
db_chats = Chats(host=config["tarantool"]["host"], port=config["tarantool"]["port"])
db_notes = Notes(host=config["tarantool"]["host"], port=config["tarantool"]["port"])

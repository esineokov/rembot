import os
import pickle
import handler


def save():
    with open('users.pickle', 'wb') as f:
        pickle.dump(
            {
                k: {'dt': v.dt, 'msg_id': v.msg_id, 'short_text': v.short_text, 'task_id': v.task_id}
                for k, v in handler.users.items()
            }, f
        )


def load():
    if os.path.exists('users.pickle'):
        with open('users.pickle', 'rb') as f:
            users = pickle.load(f)
            test = 1


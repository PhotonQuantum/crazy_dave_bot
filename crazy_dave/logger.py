from dataclasses import asdict, dataclass
from typing import List

from telethon.tl.custom import Message as _Message
from telethon.tl.types import User

from .utils import is_arabic


@dataclass
class Message:
    name: str
    id: int
    time: int
    text: str
    extra: dict


class MessageLogger:
    def __init__(self):
        self.history: List[Message] = []

    def log(self, message: _Message):
        sender: User = message.sender
        if not (msg := message.message.strip()):
            return

        first_name = name if (name := sender.first_name) else ""
        last_name = name if (name := sender.last_name) else ""
        message_obj = Message(
            name=sender.username,
            id=sender.id,
            time=int(message.date.timestamp()),
            text=msg,
            extra={"arabic": is_arabic(msg), "source": "telegram", "display_name": f"{first_name} {last_name}".strip()}
        )
        self.history.append(message_obj)

    @property
    def last_message(self) -> Message:
        return self.last_messages()[0]

    def last_messages(self, n: int = 1) -> List[Message]:
        if self.history:
            return self.history[-n:]
        return []

    def dumps(self):
        return [asdict(message) for message in self.history]

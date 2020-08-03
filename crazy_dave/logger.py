from dataclasses import asdict, dataclass
from datetime import datetime
from typing import List

from telethon.tl.custom import Message as _Message
from telethon.tl.types import User

from .utils import is_arabic


@dataclass
class Message:
    name: str
    id: int
    datetime: datetime
    text: str
    extra: dict


class MessageLogger:
    def __init__(self):
        self.history: List[Message] = []

    def log(self, message: _Message):
        sender: User = message.sender
        if not (msg := message.message.strip()):
            return

        message_obj = Message(
            name=f"{sender.first_name} {sender.last_name}",
            id=sender.id,
            datetime=message.date,
            text=msg,
            extra={"arabic": is_arabic(msg)}
        )
        self.history.append(message_obj)

    @property
    def last_message(self) -> Message:
        return self.last_messages()[0]

    def last_messages(self, n: int = 1) -> List[Message]:
        if self.history:
            return self.history[-n:]

    def dumps(self):
        return [asdict(message) for message in self.history]

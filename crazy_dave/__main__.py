import json
import logging
import os
import random
import secrets
import traceback
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telethon import TelegramClient, connection, events
from telethon.tl.custom import Message as _Message
from telethon.tl.types import InputPeerChat, SendMessageTypingAction, User

from .logger import MessageLogger
from .oss import Uploader
from .predictor import Predictor
from .utils import MaxSizeDict

logging.warning("Starting bot")

api_id = int(os.environ["API_ID"])
api_hash = os.environ["API_HASH"]
bot_token = os.environ["BOT_TOKEN"]
lstm_url = os.environ["LSTM_URL"]
s2s_url = os.environ["S2S_URL"]
oss_endpoint = os.environ["OSS_ENDPOINT"]
oss_bucket = os.environ["OSS_BUCKET"]
aliyun_accesskey_id = os.environ["ALIYUN_ACCESSKEY_ID"]
aliyun_accesskey_secret = os.environ["ALIYUN_ACCESSKEY_SECRET"]
mtproto_server = os.environ.get("MTPROTO_SERVER", None)
mtproto_port = int(os.environ.get("MTPROTO_PORT", 0))
mtproto_secret = os.environ.get("MTPROTO_SECRET", None)

use_proxy = mtproto_server and mtproto_port and mtproto_secret
if use_proxy:
    bot = TelegramClient("bot", api_id, api_hash,
                         connection=connection.ConnectionTcpMTProxyIntermediate,
                         proxy=(mtproto_server, mtproto_port, mtproto_secret))
else:
    bot = TelegramClient("bot", api_id, api_hash)

scheduler = AsyncIOScheduler()
predictor = Predictor(s2s_url, lstm_url)
uploader = Uploader((aliyun_accesskey_id, aliyun_accesskey_secret), oss_endpoint, oss_bucket)
logger = MessageLogger()
responses = MaxSizeDict(128)

me: Optional[User] = None
group: Optional[InputPeerChat] = None
chance: float = 0.1
binding_key = secrets.token_hex(nbytes=16)


@bot.on(events.NewMessage(pattern="/bind_group"))
async def bind_group(event: events.NewMessage.Event):
    global binding_key
    token = event.message.text.split(" ")[-1]
    if token == binding_key:
        try:
            global group
            group = await bot.get_input_entity(event.chat_id)
            if not os.path.exists("/data"):
                os.mkdir("/data")
            with open("/data/chat_group", mode="w") as f:
                f.write(str(event.chat_id))
            await event.reply("Bound to group.")
        except:
            traceback.print_exc()
        binding_key = secrets.token_hex(nbytes=16)
        logging.warning(f"Binding key changed to: {binding_key}")


@bot.on(events.NewMessage(pattern="/blame"))
async def blame(event: events.NewMessage.Event):
    if event.is_reply:
        reply_message: _Message = await event.get_reply_message()
        reply_user: User = reply_message.sender
        if reply_user == me and (rsp := responses.get(reply_message.id, None)):
            # noinspection PyUnboundLocalVariable
            await event.reply(json.dumps(rsp.dumps(), ensure_ascii=False))
        else:
            await event.reply("Log rotated.")
    elif responses:
        await event.reply(json.dumps(list(responses.values())[-1].dumps(), ensure_ascii=False))
    raise events.StopPropagation


# noinspection PyTypeChecker
@bot.on(events.NewMessage)
async def new_message(event: events.NewMessage.Event):
    if not group or not me:
        return
    message: _Message = event.message
    source = await message.get_input_chat()
    if not source == group:
        return
    logger.log(message)

    global responses
    if event.is_reply:
        reply_message: _Message = await event.get_reply_message()
        reply_user: User = reply_message.sender
        if reply_user == me:
            async with bot.action(group, SendMessageTypingAction()):
                sentence = [reply_message.text, message.text] if random.random() < 0.5 else message.text
                rsp = await predictor.predict(sentence)
                req_id = await event.reply(rsp.text)
                responses[req_id.id] = rsp
    elif random.random() < chance or message.text.startswith(f"@{me.username}"):
        async with bot.action(group, SendMessageTypingAction()):
            sentence = [msg.text for msg in
                        logger.last_messages(5)] if random.random() < 0.5 else logger.last_message.text
            rsp = await predictor.predict(sentence)
            req_id = await bot.send_message(group, rsp.text)
            responses[req_id.id] = rsp


@scheduler.scheduled_job("interval", minutes=10)
async def model_update():
    if not group:
        return
    lstm_result, s2s_result = await predictor.update_model()
    if lstm_result.updated:
        await bot.send_message(group,
                               f"Legacy model updated.\n{lstm_result.old_version} -> {lstm_result.current_version}")
    if s2s_result.updated:
        await bot.send_message(group, f"S2S model updated.\n{s2s_result.old_version} -> {s2s_result.current_version}")


@scheduler.scheduled_job("interval", minutes=10)
async def history_upload():
    await uploader.upload(logger.dumps())


async def startup():
    global me
    me = await bot.get_me()
    if os.path.exists("/data/chat_group"):
        with open("/data/chat_group") as f:
            try:
                group_id = int(f.read())
            except ValueError:
                return
            global group
            group = await bot.get_input_entity(group_id)


async def shutdown():
    await history_upload()
    await predictor.close()


bot.start(bot_token=bot_token)
scheduler.start()
logging.warning("Bot started.")
logging.warning(f"Group binding key is: {binding_key}")
bot.loop.run_until_complete(startup())
try:
    bot.run_until_disconnected()
finally:
    logging.warning("Bot shutdown.")
    bot.loop.run_until_complete(shutdown())

from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
from telethon.errors.rpcerrorlist import UserAlreadyParticipantError, FloodWaitError
from telethon.errors.rpcerrorlist import InviteHashExpiredError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.sync import TelegramClient, events
from dotenv import load_dotenv,find_dotenv
from telethon import functions
from os.path import exists
from os import environ
import sqlite3 as sql
import asyncio
import logging
import json
import os
import re


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
                    level=logging.INFO)


LOGGER = logging.getLogger(__name__)


if exists('log.txt'):
  with open('log.txt', 'r+') as f:
    f.truncate(0)



def check_db(admin_peerid) -> None:
  if not exists('data_base.db'):
    try:
      conn = sql.connect("./data_base.db")
      req = "CREATE TABLE admins(peer_id text NOT NULL);"\
            "CREATE TABLE channels(peer_id_channel text, peer_id_tg text, name_channel text);"
      with conn:
        conn.executescript(req)
        conn.execute("INSERT INTO admins VALUES(?)", [admin_peerid])
      conn.close()
    except sql.IntegrityError:
      conn.close()
      if exists('data_base.db'):
        os.remove(('data_base.db'))
      LOGGER.exception("error create tables")
      exit()
    except:
      conn.close()
      if exists('data_base.db'):
        os.remove(('data_base.db'))
      LOGGER.exception("unknow error")
      exit()


class dm_bot(TelegramClient):
  def __init__(self, *a, **kw) -> None:
    self.ADMIN_PEERID:int = int(environ.get('admin_peerid'))
    self.allow_channels: dict
    self.allow_users: list
    self.userid_listchannel: dict
    self.start_text = f"Commands:\n\n"\
                        "!add with link = add channel\n"\
                        "Example:\n        !add https://t.me/scriptopyan\n\n"\
                        "@add with hash link and name = add private channel\n(name must be unique)\n"\
                        "Example:\n        @add https://t.me/+siAYVGUsxowyYmQy amigones\n\n"\
                        "!dell with login channel = delete channel\n"\
                        "Example:\n        !dell @scriptopyan\n\n"\
                        "!channels = list channels\n"\
                        "!addadmin with peerid = add admin to use bot\n"\
                        "!delladmin with peerid = dell admin\n"\
                        "!admins list_peerid admins\n"
    self.set_allow_info()
    super().__init__(*a, **kw)
    self.add_event_handler(self.on_update, events.NewMessage)
  
  
  async def join_channel(self, chanel, private = False) -> list:
    success = False
    chanelid = "Unknow error"
    check_username = False
    
    if not re.search(r"[a-zA-Z][\w\d]{3,30}[a-zA-Z\d]", chanel):
      return success, "enter valid channel link"
    
    if not private:
      check_username = await self(functions.account.CheckUsernameRequest(chanel))
      if check_username:
        return success, "enter valid channel link"
    
    try:
      if not private:
        result = await self(JoinChannelRequest(chanel))
        chanelid = f"-100{result.chats[0].id}"
        success = True
      elif private:
        try:
          if '+' in chanel:
            chanel = str(chanel).split("+")[-1]
          result = await self(ImportChatInviteRequest(hash = chanel))
          chanelid = result.chats[0].id
          success = True
        except UserAlreadyParticipantError:
          result = await self(CheckChatInviteRequest(hash = chanel))
          result = result.to_json()
          result = json.loads(result)
          chanelid = f"-100{result['chat']['id']}"
          success = True
        except FloodWaitError as e:
          chanelid = f"FloodWaitError: {e}"
        except InviteHashExpiredError as e:
          chanelid = f"InviteHashExpiredError: {e}"
    # except Exception as e:
    #   e = f"unknow err = {e}"
    #   LOGGER.exception(e)
    finally:
      return success, chanelid
  
  
  async def connect(self) -> None:
    await super().connect()
    self.me = await self.get_me()
  
  def get_clear_message(self, event) -> list:
    text_msg = event.message.message
    entities = event.entities
    file = event.message.photo if event.message.photo else None
    return text_msg, entities, file

  def set_allow_info(self, conn = None) -> None:
    if conn is None:
      conn = sql.connect("./data_base.db")
    with conn:
      raw_allow_users = conn.execute("SELECT DISTINCT peer_id FROM admins").fetchall()
      raw_allow_channels = conn.execute("SELECT * FROM channels").fetchall()
    conn.close()
    self.allow_users = list(map(lambda x:int(x[0]), raw_allow_users))
    self.set_allow_channels(raw_allow_channels)
  
  def send_req_bd(self, req:str, values:tuple|list, need_result=False) -> bool|list:
    conn = sql.connect("./data_base.db")
    try:
      with conn:
        result = conn.execute(req, values)
      self.set_allow_info(conn)
      if need_result:
        return result.fetchall()
      return True
    except sql.IntegrityError as e:
      LOGGER.exception(e)
      conn.close()
      return False
  
  def set_allow_channels(self, raw_allow_channels) -> dict:
    allow_channels = {}
    userid_listchannel = {}
    for userid in self.allow_users:
      userid_listchannel[userid] = []
    for channel in raw_allow_channels:
      
      channel_id, userid, name_channels = channel
      channel_id = int(channel_id)
      userid = int(userid)
      
      # if not userid_listchannel.get(userid, False):
      #   userid_listchannel[userid] = []
        
      userid_listchannel[userid].append(name_channels)
      
      if not allow_channels.get(channel_id, False):
        allow_channels[channel_id] = []
      
      allow_channels[channel_id].append(userid)

    self.allow_channels = allow_channels
    self.userid_listchannel = userid_listchannel

  async def check_command(self, text:str, peerid:int) -> None:
    text = text.split(" ")
    
    match text:
      case "@add", hash_link, name:
        if "/" in hash_link:
          hash_link = str(hash_link).split("/")[-1]
        if any(("@" in name, "@" in hash_link, "/" in hash_link)):
          text = "Example:\n        @add https://t.me/+siAYVGUsxowyYmQy amigones\n"
          return await self.send_message(peerid, text)
        if f"@{name}" in self.userid_listchannel[peerid]:
          return await self.send_message(peerid, "already in database")
        success, peerid_channel = await self.join_channel(hash_link, private=True)
        if not success:
          text = str(peerid_channel)
        else:
          req = "INSERT INTO channels VALUES(?, ? ,?)"
          if self.send_req_bd(req, (peerid_channel, peerid, f"@{name}")):
            text = "success added to database"
          else:
            text = "NOT success added to database"
        return await self.send_message(peerid, text)
      case "!add", link:
        if "@" in link:
          link = str(link).split("@")[-1]
        elif "/" in link:
          link = str(link).split("/")[-1]
        if f"@{link}" in self.userid_listchannel[peerid]:
          return await self.send_message(peerid, "already in database")
        
        success, peerid_channel = await self.join_channel(link, private=False)
        if not success:
          text = str(peerid_channel)
        else:
          req = "INSERT INTO channels VALUES(?, ? ,?)"
          if self.send_req_bd(req, (peerid_channel, peerid, f"@{link}")):
            text = "success added to database"
          else:
            text = "NOT success added to database"
        return await self.send_message(peerid, text)
      case "!dell", link:
        if not link in self.userid_listchannel[peerid]:
          return await self.send_message(peerid, "not in database")
        else:
          req = "DELETE FROM channels WHERE peer_id_tg = ? AND name_channel = ?"
          if self.send_req_bd(req, (peerid, link)):
            text = "SUCCESS delete from database"
          else:
            text = "NOT SUCCESS delete from database"
          return await self.send_message(peerid, text)
      case "!channels", *_:
        list_channels = "   ".join(self.userid_listchannel[peerid])
        text = f"List channels:\n{list_channels}"
        return await self.send_message(peerid, text)
      case "!admins", *_:
        if not peerid == self.ADMIN_PEERID:
          return await self.send_message(peerid, "not access")
        text = "\n".join(map(str, self.allow_users))
        return await self.send_message(peerid, f"List admins_peerids:\n{text}")
      case "!addadmin", peerid_add:
        if not peerid == self.ADMIN_PEERID:
          return await self.send_message(peerid, "not access")
        try:
          peerid_add = int(peerid_add)
          if peerid_add in self.allow_users:
            return await self.send_message(peerid, "already in database")
        except ValueError:
          return await self.send_message(peerid, "input valide peerid")
        req = "INSERT INTO admins VALUES(?)"
        if self.send_req_bd(req, [peerid_add]):
          text = "SUCCESS add admins peerid to database"
        else:
          text = "NOT SUCCESS add admins peerid to database"
        return await self.send_message(peerid, text)
      case "!delladmin", peerid_dell:
        if not peerid == self.ADMIN_PEERID:
          return await self.send_message(peerid, "not access")
        try:
          peerid_dell = int(peerid_dell)
          if not peerid_dell in self.allow_users:
            return await self.send_message(peerid, "not in database")
          if peerid_dell == self.ADMIN_PEERID:
            return await self.send_message(peerid, "not access")
        except ValueError:
          return await self.send_message(peerid, "input valide peerid")
        req = "DELETE FROM admins WHERE peer_id = ?"
        if self.send_req_bd(req, [peerid_dell]):
          text = "SUCCESS delete admin peerid from database"
        else:
          text = "NOT success delete admin peerid from database"
        return await self.send_message(peerid, text)
      case _:
        return await self.send_message(peerid, self.start_text)
  
  
  async def on_update(self, event:events.NewMessage) -> None:
    if event.is_private:
      peerid_user = int(event.peer_id.user_id)
      msg = str(event.message.message)
      if peerid_user in self.allow_users:
        await self.check_command(msg, peerid_user)
    elif event.is_channel and event.chat_id in self.allow_channels.keys():
      textmsg, entities, file = self.get_clear_message(event)
      send_to_userids = self.allow_channels[event.chat_id]
      text = f"Channel: {event.chat.title}\nText:\n{textmsg}"
      for userid in send_to_userids:
        await self.send_message(userid, text, formatting_entities=entities,file=file)

def find_session() -> str:
  files = os.listdir()
  for file in files:
    if file.endswith("session"):
      return file

def main() -> None:
  dotenv_file = find_dotenv()
  load_dotenv(dotenv_file)
  PATH_SESSION = find_session()
  API_HASH = environ.get('api_hash')
  API_ID = environ.get('api_id')
  ADMIN_PEERID = environ.get('admin_peerid')
  check_db(ADMIN_PEERID)
  
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  bot = dm_bot(PATH_SESSION, API_ID, API_HASH).start()
  bot.run_until_disconnected()


if __name__ == "__main__":
  main()
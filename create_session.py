from telethon.sync import TelegramClient
from telethon.errors.rpcerrorlist import SessionPasswordNeededError
import time
def main():
	phone = str(input('введи номер (пример: +77719999999): '))
	apid = str(input('введи api_id: '))
	ihash = str(input('введи api_hash: '))
	for _ in range(1):
	    try:
		name_sess = "ses" if _ == 0 else "ses1"
		client = TelegramClient(name_sess, apid, ihash)
		client.connect()
		print('connected successfully')
		if not client.is_user_authorized():
		    client.send_code_request(phone)
		    try:
		        client.sign_in(phone, input('Enter the code: '))
		    except SessionPasswordNeededError:
		        client.sign_in(password=input('Password: '))
		client.disconnect()
		print('disconnected...')
	    except Exception as e:
		print(e)
	    time.sleep(3)
if __name__ == "__main__":
	main()
	input('finish ')
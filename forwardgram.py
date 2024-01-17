from telethon import TelegramClient, events, sync
from telethon.tl.types import InputPeerUser
import yaml
import sys
import logging
import discord
import subprocess

''' 
------------------------------------------------------------------------
                LOGGING - Initite logging for the Bot
------------------------------------------------------------------------
'''
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger('telethon').setLevel(level=logging.WARNING)
logger = logging.getLogger(__name__)

''' 
------------------------------------------------------------------------
    BOT FUNCTION - Everything that happens, happens for a reason
------------------------------------------------------------------------
'''
def start(config):
    # Telegram Client Init
    client = TelegramClient(config["session_name"], 
                            config["api_id"], 
                            config["api_hash"])
    # Telegram Client Start
    client.start()

    # Input Messages Telegram Users will be stored in these empty Entities
    input_user_entities = []
    output_user_entities = []

    # Iterating over dialogs is no longer necessary. Directly fetching users:
    for user_id in config["input_user_ids"]:
        user = client.get_input_entity(user_id)
        input_user_entities.append(user)

    # Fetching output users:
    for user_id in config["output_user_ids"]:
        user = client.get_input_entity(user_id)
        output_user_entities.append(user)

    # Check if there are any output users or input users
    if not output_user_entities:
        logger.error(f"Could not find any output users")
        sys.exit(1)

    if not input_user_entities:
        logger.error(f"Could not find any input users")
        sys.exit(1)
    
    # Use logging and print messages on your console.     
    logging.info(f"Listening to {len(input_user_entities)} users. Sending messages to {len(output_user_entities)} users.")
    # TELEGRAM NEW MESSAGE - When new message triggers, come here
    @client.on(events.NewMessage(chats=input_user_entities))
    async def handler(event):
        for output_user in output_user_entities:

            # Uncomment the line below to print full message in structured format on your console.
            #logging.info(f"Message Was: {event.message}")

            # We will parse the items from response. You can first view the full message above,
            # then decide which elements you want to parse from telegram response

            # If our entities contain URL, we want to parse and send Message + URL
            try:
                parsed_response = (event.message.message + '\n' + event.message.entities[0].url )
                parsed_response = ''.join(parsed_response)
            # Or else we only send Message    
            except:
                parsed_response = event.message.message

            # This is probably not the best way to do this but definitely the easiest way. 
            # When message triggers you start discord messanger script in new thread and sends parsed input as sys.argv[1]
            subprocess.call(["python", "discord_messager.py", str(parsed_response)])
            # this will forward your message to channel_recieve in Telegram
#             await client.forward_messages(output_user, event.message)

    client.run_until_disconnected()

''' 
------------------------------------------------------------------------
          MAIN FUNCTION - Can't dream without a brain ...
------------------------------------------------------------------------
'''

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} {{CONFIG_PATH}}")
        sys.exit(1)
    with open(sys.argv[1], 'rb') as f:
        config = yaml.safe_load(f)
    start(config)

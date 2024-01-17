import yaml
import discord
import asyncio
from io import BytesIO
from telethon import TelegramClient, events
import os

# Load configuration
with open('config.yml', 'rb') as f:
    config = yaml.safe_load(f)

# Initialize Discord client
intents = discord.Intents.default()
intents.messages = True  # This is crucial for reading messages
intents.message_content = True
discord_client = discord.Client(intents=intents)

# Initialize Telegram client
telegram_client = TelegramClient(config["session_name"],
                                 config["api_id"],
                                 config["api_hash"])

# Discord event handlers
@discord_client.event
async def on_ready():
    print(f'We have logged in as {discord_client.user}')

@discord_client.event
async def on_message(message):
    print("DiscordRead: "+message.content)
    print("DiscordRead: "+message.author.name)
    #Ignore messages from the bot itself
    if message.author == discord_client.user:
        return

    # Assuming message.channel.id is the channel you want to monitor
    if message.channel.id == config["discord_read_channel_id"]:
        try:
            # Send text message to Telegram user
            if message.content:
                await telegram_client.send_message(config["telegram_user_id"], message.content)

            # Check for file attachments and forward them
            if message.attachments:
                for attachment in message.attachments:
                    file_url = attachment.url
                    file_name = attachment.filename
                    file_data = await attachment.read()
                    await telegram_client.send_file(config["telegram_user_id"], file_data, caption=f"File from Discord: {file_name}")

        except Exception as e:
            print(f"Error in sending message: {e}")

# Telegram event handlers
@telegram_client.on(events.NewMessage(chats=config["telegram_user_id"]))
async def handler(event):
    await discord_client.wait_until_ready()
    channel = discord_client.get_channel(config["discord_write_channel_id"])
    if channel:
        # Send text message to Discord channel
        if event.message.text:
            await channel.send(event.message.message)
        # Check for file attachments and forward them
        if event.message.media:
            file_data = await event.download_media()
            file_name = event.message.file.name
            file = discord.File(file_data, filename=file_name)
            await channel.send(file=file)

            #Delete the file from the server
            os.remove(file_data)

# Function to run the Telegram client
async def run_telegram_client():
    await telegram_client.start()
    await telegram_client.run_until_disconnected()

# Function to run the Discord client
async def run_discord_client():
    await discord_client.start(config["discord_bot_token"])

# Main function to run both clients
async def main():
    # Create tasks for both clients
    discord_task = asyncio.create_task(run_discord_client())
    telegram_task = asyncio.create_task(run_telegram_client())

    # Wait for both tasks to complete
    await asyncio.gather(discord_task, telegram_task)

if __name__ == "__main__":
    asyncio.run(main())

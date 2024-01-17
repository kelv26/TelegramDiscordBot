import discord
import asyncio
from telethon import TelegramClient, events
import os
import tempfile
import shutil
from dotenv import load_dotenv
from keep_alive import keep_alive
keep_alive()

load_dotenv()

message_mappings = {}
session_user = None
everyone_role = None

# Initialize Discord client
intents = discord.Intents.default()
intents.messages = True  # This is crucial for reading messages
intents.message_content = True
discord_client = discord.Client(intents=intents)

# Initialize Telegram client
telegram_client = TelegramClient(os.environ.get("SESSION_NAME"),
                                 int(os.environ.get("API_ID")),
                                 os.environ.get("API_HASH"))

# Discord event handlers
@discord_client.event
async def on_ready():
    print(f'We have logged in as {discord_client.user}')

# READ FROM DISCORD TO TELEGRAM
@discord_client.event
async def on_message(message):
    
    #Ignore messages from the bot itself
    if message.author == discord_client.user:
        return

    # Assuming message.channel.id is the channel you want to monitor
    if message.channel.id == int(os.environ.get("DISCORD_READ_CHANNEL_ID")):
        try:
            # set write channel permission to the message author
            if message.content == "/start":
                global session_user
                # Set the session user to the message author
                session_user = message.author
                
                # Get the @everyone role
                global everyone_role 
                everyone_role = message.guild.default_role

                # Set permissions for @everyone to disallow sending messages but allow read
                await message.channel.set_permissions(everyone_role, send_messages=False, read_messages=True)

                # Set permissions for the message author to allow sending messages until the session ends.
                await message.channel.set_permissions(session_user, send_messages=True, read_messages=True)

                print(f"Set permissions for {session_user.name} to write only.")

            # Send text message to Telegram user
            if message.content:
                await telegram_client.send_message(int(os.environ.get("TELEGRAM_USER_ID")), message.content)

            # Check for file attachments and forward them
            if message.attachments:
                for attachment in message.attachments:
                    file_name = attachment.filename
                    file_data = await attachment.read()

                    # Create a temporary directory to store the file
                    temp_dir = tempfile.mkdtemp()
                    temp_file_path = os.path.join(temp_dir, file_name)

                    # Write the file data to the temporary file
                    with open(temp_file_path, 'wb') as temp_file:
                        temp_file.write(file_data)

                    # Send file with its original name
                    await telegram_client.send_file(int(os.environ.get("TELEGRAM_USER_ID")), temp_file_path)

                    # Clean up the temporary directory and file
                    shutil.rmtree(temp_dir)
                
                try:
                    #Delete the file to prevent other users from seeing it.
                    await message.delete()
                except Exception as e:
                    print(f"Error deleting file: {e}")

        except Exception as e:
            print(f"Error in sending message: {e}")

# Telegram event handlers
@telegram_client.on(events.NewMessage(chats=int(os.environ.get("TELEGRAM_USER_ID"))))
async def handler(event):
    await discord_client.wait_until_ready()
    channel = discord_client.get_channel(int(os.environ.get("DISCORD_WRITE_CHANNEL_ID")))
    if channel:
        try:
            discord_message = None

            if event.message.text:
                # Send the message based on specific conditions
                if(event.message.text.startswith("Your subscription:")):
                    await telegram_client.send_message(int(os.environ.get("TELEGRAM_USER_ID")), "🌐 Turnitin Intl")
                elif(event.message.text.startswith("Do you")):
                    discord_message = await channel.send(event.message.message+"\n(YES/NO) *Case Sensitive*")
                elif(event.message.text.startswith("#Submitted")):
                    discord_message = await channel.send("**Processing, please wait...**\n"+event.message.message)
                else:
                    discord_message = await channel.send(event.message.message)

            # Check for file attachments and forward them
            if event.message.media:
                try:
                    # Download the file from Telegram and save it temporarily
                    temp_dir = tempfile.mkdtemp()
                    file_data = await event.download_media(file=temp_dir)
                    file_name = event.message.file.name

                    # Create a discord.File object from the downloaded file
                    file_path = os.path.join(temp_dir, file_name)
                    file = discord.File(file_path, filename=file_name)

                    # Fetch the user by ID
                    user = await discord_client.fetch_user(session_user.id)
                    
                    # Send a DM to the user and server
                    await user.send(file=file)
                    await channel.send(f"Plagiarism Reports sent to user <@{session_user.id}>.")

                    print(f"Sent file {file_name} to Discord user {session_user.name}")
                    
                    # Set everyone to have write permission and remove the user author custom permission
                    await channel.set_permissions(session_user, overwrite=None)
                    await channel.set_permissions(everyone_role, send_messages=True, read_messages=True)
                    print(f"Set permissions for @everyone to read and write.")

                    # Clean up the temporary file
                    os.remove(file_path)
                    shutil.rmtree(temp_dir)

                except Exception as e:
                    print(f"Error downloading file: {e}")
                    return

            # Store the message ID mapping if a message was sent
            if discord_message:
                message_mappings[event.message.id] = discord_message.id

        except Exception as e:
            print(f"Error in Telegram event handler: {e}")

@telegram_client.on(events.MessageEdited(chats=int(os.environ.get("TELEGRAM_USER_ID"))))
async def edited_handler(event):
    if event.message.id in message_mappings:
        discord_message_id = message_mappings[event.message.id]
        channel = discord_client.get_channel(int(os.environ.get("DISCORD_WRITE_CHANNEL_ID")))

        if channel:
            try:
                discord_message = await channel.fetch_message(discord_message_id)
                await discord_message.edit(content=event.message.text)
            except Exception as e:
                print(f"Error updating Discord message: {e}")

# Function to run the Telegram client
async def run_telegram_client():
    await telegram_client.start()
    await telegram_client.run_until_disconnected()

# Function to run the Discord client
async def run_discord_client():
    await discord_client.start(os.environ.get("DISCORD_BOT_TOKEN"))

# Main function to run both clients
async def main():
    # Create tasks for both clients
    discord_task = asyncio.create_task(run_discord_client())
    telegram_task = asyncio.create_task(run_telegram_client())

    # Wait for both tasks to complete
    await asyncio.gather(discord_task, telegram_task)

if __name__ == "__main__":
    asyncio.run(main())

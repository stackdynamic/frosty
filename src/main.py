import discord
from src.config import PROFILE
from src.commands import commands
from src.message_structs import *

client = discord.Client()


async def process_message(message):
    msg_info = Message_Info(message)
    # Iterates through the commands dict of the form {Trigger: func -> Call}:
    for trigger, func in commands.copy().items():
        if trigger.match(msg_info.content):
            async with message.channel.typing():
                args = trigger.slice(msg_info.content)
                # If so, passes the slice into the corresponding function,
                #     and adds the returned Call object's invoke() method
                #     to the client loop.
                task = await client.loop.run_in_executor(None, func, msg_info, *args)
                if isinstance(task, Call):
                    await task.invoke()
            break


@client.event
async def on_message(message):
    if not message.author.bot:
        try:
            await process_message(message)
        except Exception as e:
            raise e


def main():
    client.run(PROFILE["bot_token"])


if __name__ == "__main__":
    main()

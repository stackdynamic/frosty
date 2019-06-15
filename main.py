# ihscy's over-engineered Discord bot
import discord
import asyncio
import math
import numpy as np
from bsd import SnowAlertSystem
from message_structs import CallType, UserData, UserTypes


client = discord.Client()


class Call:
    def __init__(self, call_type, message, response=None, ignore_auth = False):
        self.call_type = call_type
        self.response = response
        self.message = message
        self.ignore_auth = ignore_auth


    async def invoke(self):
        if self.call_type == CallType.DELETE or self.call_type == CallType.REPLACE:
            await self.delete()
        if self.call_type == CallType.SEND or self.call_type == CallType.REPLACE:
            if self.response is not None:
                await self.send()


    async def send(self):
        if self.response is not None:
            if not self.ignore_auth:
                self.response = self.response.replace("!auth", self.message.author.name)
            await self.message.channel.send(self.response)


    async def delete(self):
        await self.message.delete()


class Trigger:
    def __init__(self, begin, access_level=0, end=None):
        self.begin = begin.lower()
        self.end = end
        if self.end is not None:
            self.end = self.end.lower()
            self.e_words = self.end.split()
        self.b_words = self.begin.split()
        self.access_level = access_level


    def __str__(self):
        if self.end is not None:
            string = "`{0}...{1}`".format(self.begin, self.end)
        else:
            string = "`{0}`".format(self.begin)
        string += " with user status `{0}` or higher".format(
            UserTypes(self.access_level).name.lower()
        )
        return string


    def begins(self, lwords):
        return lwords[:len(self.b_words)] == self.b_words


    def ends(self, lwords):
        return self.end is None or lwords[-len(self.e_words):] == self.e_words


    def begin_index(self, lwords):
            return lwords.index(self.b_words[0]) + len(self.b_words)


    def end_index(self, lwords):
        if self.end is None:
            return len(lwords)
        else:
            return lwords.index(self.e_words[0])


    def slice(self, lwords):
        sliced = " ".join(lwords[
            self.begin_index(lwords):
            self.end_index(lwords)
        ])
        # Removes leading/trailing pairs of ` to allow for code formatting
        i = 0
        while True:
            if i < len(sliced) // 2 and sliced[i] == sliced[-i - 1] == '`':
                i += 1
            else:
                break
        return sliced[i:len(sliced) - i]


class Response:
    safe_characters = "0123456789*/+-%^()"


    def __init__(self, message):
        # Get data from message
        self.message = message
        self.words = self.message.content.split()
        self.lwords = [w.lower() for w in self.words]
        self.author = self.message.author.name
        user_level = UserData.get_level(self.author)
        for trigger, func in Response.commands.copy().items():
            if trigger.begins(self.lwords) and trigger.ends(self.lwords):
                if user_level >= trigger.access_level:
                    message_slice = trigger.slice(self.lwords)
                    task = func(self, message_slice)
                    if isinstance(task, Call):
                        client.loop.create_task(task.invoke())


    def new_command(self, message_slice):
        words = message_slice.split()
        i = words.index(":")
        args = words[0:i]
        if len(args) > 1:
            args[1] = int(args[1])
        trigger = Trigger(*args)
        reply = " ".join(words[i + 1:]).strip()
        if "!del" in reply:
            reply = reply.replace("!del", "")
            call_type = CallType.REPLACE
        else:
            call_type = CallType.SEND

        def call_func(response, message_slice):
            return Call(call_type, response.message, reply)

        call_func.__name__ = args[0].replace("!", "")
        Response.commands[trigger] = call_func
        return Call(
            CallType.SEND,
            self.message,
            "New command: on {0} I'll say `{1}`".format(str(trigger), reply),
            ignore_auth = True

        )


    def remove_command(self, message_slice):
        for trigger in Response.commands:
            if trigger.begin == message_slice:
                return Call(
                    CallType.SEND,
                    self.message,
                    "`{0}` with response `{1}` has been removed".format(
                        str(trigger),
                        Response.commands[trigger].__name__)
                )


    def ban(self, message_slice):
        recipient_level = UserData.get_level(message_slice)
        if recipient_level == -1:
            UserData.levels[UserTypes.BANNED].remove(message_slice)
            return Call(CallType.SEND, self.message, "un-banned {0}".format(message_slice))
        elif recipient_level == 2:
            return Call(CallType.SEND, self.message, "Owners can't be banned")
        else:
            UserData.levels[UserTypes(recipient_level)].remove(message_slice)
            UserData.levels[UserTypes.BANNED].append(message_slice)
            return Call(CallType.SEND, self.message, "{0} has been banned".format(message_slice))


    def give_admin(self, message_slice):
        recipient_level = UserData.get_level(message_slice)
        if recipient_level == 1:
            UserData.levels[UserTypes.ADMIN].remove(message_slice)
            return Call(
                CallType.SEND,
                self.message,
                "{0}'s admin status has been revoked".format(message_slice)
            )
        elif recipient_level == 2:
            return Call(CallType.SEND, self.message, "owners can't be given admin status")
        else:
            UserData.levels[UserTypes(recipient_level)].remove(message_slice)
            UserData.levels[UserTypes.ADMIN].append(message_slice)
            return Call(CallType.SEND, self.message, "{0} is now an admin".format(message_slice))


    def snowman(self, message_slice):
        if UserData.get_level(self.author) == -1:
            return Call(
                CallType.SEND, 
                self.message, 
                "{0} doesn't deserve ANY snowmen".format(self.message.author.name)
            )
        else:
            if message_slice == "a":
                snowman_count = 1
            else:
                if all(char in Response.safe_characters for char in message_slice):
                    snowman_count = int(eval(message_slice))
                else:
                    snowman_count = 0
            if snowman_count > 0:
                return Call(CallType.SEND, self.message, "☃" * min(snowman_count, 128))


    def frosty_say(self, message_slice):
        return Call(CallType.REPLACE, self.message, message_slice)


    def command_list(self, message_slice):
        message = "**Commands:**\n" 
        message += "\n".join(
            "{0} will run `{1}`\n".format(str(trigger), func.__name__)
            for trigger, func in Response.commands.items()
        )
        return Call(CallType.SEND, self.message, message)


    commands = {
        Trigger("give me", end="snowman"): snowman,
        Trigger("give me", end="snowmen"): snowman,
        Trigger("!ban", access_level=1): ban,
        Trigger("!admin", access_level=1): give_admin,
        Trigger("!say"): frosty_say,
        Trigger("!add", access_level=1): new_command,
        Trigger("!remove", access_level=1): remove_command,
        Trigger("!list"): command_list
    }


@client.event
async def on_message(message):
    if not message.author.bot:
        try:
            Response(message)
        except Exception as e:
            raise e


snow_alert = SnowAlertSystem(client)
client.loop.create_task(snow_alert.check_bsd())

client.run(input("Token: "))

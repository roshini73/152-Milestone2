from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    AWAITING_REASON = auto()
    AWAITING_VT_TYPE = auto()
    AWAITING_LIVESTREAM = auto()

#MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    YES_KEYWORD = "Y"
    NO_KEYWORD = "N"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None

    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord.
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]

        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]

        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!

            self.state = State.AWAITING_REASON
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "What is your reason for reporting this post? If it is violence/terrorism please confirm by typing 'Y'. Type 'N' if not."]

        if self.state == State.AWAITING_REASON and message.content == self.YES_KEYWORD:
            self.state = State.AWAITING_VT_TYPE
            return["What kind of violence/terrorism is this post promoting? If it is terrorism please confirm by typing 'Y'. Type 'N' if not."]

        elif self.state == State.AWAITING_REASON:
            return ["We are currently focused on reducing violent and terrorist media but thank you for taking the time to report other types of harmful content."]

        if self.state == State.AWAITING_VT_TYPE and message.content == self.YES_KEYWORD:
            self.state = State.AWAITING_LIVESTREAM
            return["Is this post being live streamed? If so, please confirm by typing 'Y'. Type 'N' if not."]

        elif self.state == State.AWAITING_VT_TYPE:
            return["We are currently working on reducing specifically terrorist content but understand the harms of other forms of violence and appreciate your support in our mission to make this forum a safe space for everyone."]

        if self.state == State.AWAITING_LIVESTREAM and message.content == self.YES_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Thank you. Our content moderation team will review this post with high priority."]

        elif self.state == State.AWAITING_LIVESTREAM:
            self.state = State.REPORT_COMPLETE
            return ["Thank you. Our content moderation team will review this post."]

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE

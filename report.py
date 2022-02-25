from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    AWAITING_REASON = auto()
    AWAITING_VT_TYPE = auto()
    AWAITING_LIVESTREAM = auto()
    AWAITING_MODERATION = auto()

    REPORT_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    YES_KEYWORD = "Y"
    NO_KEYWORD = "N"

    ALL_OPTIONS = [START_KEYWORD, CANCEL_KEYWORD, HELP_KEYWORD, YES_KEYWORD, NO_KEYWORD]

    def __init__(self, client, message):
        self.state = State.REPORT_START
        self.client = client
        self.message = message
        self.reason = None
        self.vt_type = None
        self.livestream = None
        self.auto = True
        self.priority = 1

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
            self.auto = False
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
                return ["I cannot accept reports of posts from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or type `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this post was deleted or never existed. Please try again or type `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.message = message
            self.state = State.AWAITING_REASON
            return ["I found this post:", "```" + message.author.name + ": " + message.content + "```", \
                    "What is your reason for reporting this post? If it is violence/terrorism please confirm by typing 'Y'. Type 'N' if not."]

        if self.state == State.AWAITING_REASON and message.content == self.YES_KEYWORD:
            self.reason = True
            self.state = State.AWAITING_VT_TYPE
            return["What kind of violence/terrorism is this post promoting? If it is terrorism please confirm by typing 'Y'. Type 'N' if not."]

        elif self.state == State.AWAITING_REASON and message.content == self.NO_KEYWORD:
            self.reason = False
            self.state = State.REPORT_COMPLETE
            return ["We are currently focused on reducing violent and terrorist media but thank you for taking the time to report other types of harmful content."]

        if self.state == State.AWAITING_VT_TYPE and message.content == self.YES_KEYWORD:
            self.state = State.AWAITING_LIVESTREAM
            self.vt_type = True
            return["Is this post being live streamed? If so, please confirm by typing 'Y'. Type 'N' if not."]

        elif self.state == State.AWAITING_VT_TYPE and message.content == self.NO_KEYWORD:
            self.vt_type = False
            self.state = State.REPORT_COMPLETE
            return["We are currently working on reducing specifically terrorist content but understand the harms of other forms of violence and appreciate your support in our mission to make this forum a safe space for everyone."]

        if self.state == State.AWAITING_LIVESTREAM and message.content == self.YES_KEYWORD:
            self.livestream = True
            self.state = State.AWAITING_MODERATION
            return ["Thank you. Our content moderation team will review this post with high priority. The post may be removed or flagged and/or the user may be banned."]

        elif self.state == State.AWAITING_LIVESTREAM and message.content == self.NO_KEYWORD:
            self.livestream = False
            self.state = State.AWAITING_MODERATION
            return ["Thank you. Our content moderation team will review this post. The post may be removed or flagged and/or the user may be banned."]

        return ["Not a valid option, please choose again from the prompt or type 'cancel' to cancel moderation."]

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE

    def awaiting_moderation(self):
        return self.state == State.AWAITING_MODERATION
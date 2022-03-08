from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    AWAITING_REASON = auto()
    #AWAITING_VT_TYPE = auto()
    AWAITING_LIVESTREAM = auto()
    AWAITING_MODERATION = auto()
    AWAITING_DETAILS = auto()
    REPORT_COMPLETE = auto()
    AWAITING_IMMEDIACY = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    YES_KEYWORD = "Y"
    NO_KEYWORD = "N"
    FALSE_INFO_KEYWORD = "A"
    SPAM_KEYWORD = "B"
    HARASSMENT_KEYWORD = "C"
    VIOLENCE_KEYWORD = "D"
    TERRORISM_KEYWORD = "E"
    HATE_SPEECH_KEYWORD = "F"
    reasons = {"A": "false information", "B": "spam", "C": "harassment", "D": "violence", "E": "terrorism", "F": "hate speech"}

    ALL_OPTIONS = [START_KEYWORD, CANCEL_KEYWORD, HELP_KEYWORD, YES_KEYWORD, NO_KEYWORD]
    priorities = {"false information": 1, "spam": 1, "harassment": 1, "violence": 2, "terrorism": 3, "hate speech": 1}

    def __init__(self, client, message):
        self.reportReason = None
        self.state = State.REPORT_START
        self.client = client
        self.message = message
        self.reason = None #terrrorism or not
        self.vt_type = None
        self.livestream = None
        self.auto = True
        self.priority = 0
        self.extra = ""
        self.immediate = False

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
            reply += "Please copy paste the link to the post you want to report.\n"
            reply += "You can obtain this link by right-clicking the post and clicking `Copy Message Link`."
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
                    "What is your reason for reporting this post? \nA: False Information\nB: Spam \nC: Harassment \nD: Violence \nE: Terrorism \nF: Hate Speech \nIf your reason for reporting this post does not fall into any of the specified categories above, please share in a few words your reason for reporting this post."]

        if self.state == State.AWAITING_REASON:
            if message.content == self.TERRORISM_KEYWORD:
                self.reason = True
            if message.content in self.reasons:
                self.reportReason = self.reasons[message.content]
                self.priority += self.priorities[self.reportReason]
            else:
                self.reportReason = message.content
                self.priority += 1

            self.state = State.AWAITING_IMMEDIACY
            return["Do the contents of this post pose an ongoing or immediate threat? Type 'Y' for yes and 'N' for no."]

        if self.state == State.AWAITING_IMMEDIACY:
            if message.content == self.YES_KEYWORD:
                self.immediate = True
                self.priority += 2
                self.state = State.AWAITING_LIVESTREAM
                return["You stated that the contents of this post pose an ongoing or immediate threat. Is this post being livestreamed? Type 'Y' for yes and 'N' for no."]
            else:
                self.state = State.AWAITING_DETAILS
                self.priority += 1
                return["If you would like to provide any additional details, please do so now. Otherwise type 'N'."]

        if self.state == State.AWAITING_DETAILS:
            self.state = State.AWAITING_MODERATION
            if message.content != self.NO_KEYWORD:
                self.extra = message.content
            print(self.priority)
            if self.livestream:
                return ["Thank you. Our content moderation team will review this post with high priority. The post may be removed or flagged and/or the user may be banned."]
            else:
                return["Thank you. Our content moderation team will review this post. The post may be removed or flagged and/or the user may be banned."]

        if self.state == State.AWAITING_LIVESTREAM:
            if message.content == self.YES_KEYWORD:
                self.livestream = True
                self.priority += 2
            else:
                self.livestream = False
                self.priority += 1
            self.state = State.AWAITING_DETAILS
            return ["If you would like to provide any additional details, please do so now. Otherwise type 'N'."]

        return ["Not a valid option, please choose again from the prompt or type 'cancel' to cancel moderation."]

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE

    def awaiting_moderation(self):
        return self.state == State.AWAITING_MODERATION

from enum import Enum, auto
import discord
import re

class State(Enum):
    MODERATION_START = auto()
    AWAITING_SOURCE = auto()
    AWAITING_TERRORISM = auto()
    AWAITING_LIVESTREAM = auto()
    AWAITING_AID = auto()

    MODERATION_COMPLETE = auto()

class Moderator:
    START_KEYWORD = "start"
    NEXT_KEYWORD = "next"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    T_KEYWORD = "T"
    V_KEYWORD = "V"
    YES_KEYWORD = "Y"
    NO_KEYWORD = "N"

    def __init__(self, report):
        self.state = State.MODERATION_START
        self.report = report
        self.outcome = ""
        self.banned = False
        self.removed = False
        self.flagged = False

    async def handle_message(self, message):
        '''
        This function makes up the meat of the moderator-side handling flow. It defines how we transition between states and what
        prompts to offer at each of those states.
        '''

        if self.state == State.MODERATION_START:
            self.state = State.AWAITING_LIVESTREAM
            reason = "violence/terrorism" if self.report.reason else "reasons other than violence/terrorism"
            vt_type = "terrorism" if self.report.vt_type else "violence"
            live = "is" if self.report.livestream else "is not"
            return(["There is a report for the following message:", "```" + self.report.message.author.name + ": " + self.report.message.content + "```", \
            "The post was reported for "  + reason + ", specifically " + vt_type + " and " + live + " reported to be a livestream.", \
            "Is this post actually being live streamed? If so, please confirm by typing \'Y\'. Type \'N\' or any other key if not."])


        if self.state == State.AWAITING_LIVESTREAM and message.content == self.YES_KEYWORD:
            self.state = State.AWAITING_TERRORISM
            return ["Thank you for confirming that this is a livestream. Is the content of the livestream in fact terrorism? Please confirm by typing 'Y'. Type 'N' or any other key if not."]

        elif self.state == State.AWAITING_LIVESTREAM:
            self.state = State.MODERATION_COMPLETE
            self.outcome = "The post was not found to contain a livestream and therefore, no action was taken at this time."
            return["Thank you for confirming that this is not a livestream. The moderation process for this report is now complete."]

        if self.state == State.AWAITING_TERRORISM and message.content == self.YES_KEYWORD:
            self.state = State.AWAITING_SOURCE
            return["Who is livestreaming this event? If it is the terrorist please type 'T'. If it is a victim, type 'V' or any other key."]

        elif self.state == State.AWAITING_TERRORISM:
            self.state = State.MODERATION_COMPLETE
            self.outcome = "While the post did contain a livestream, the livestream was not found to be of terrorism. Therefore, no action was taken at this time."
            return["Thank you for confirming that this is not a livestream of terrorism. The moderation process for this report is now complete."]

        if self.state == State.AWAITING_SOURCE and message.content == self.T_KEYWORD:
            self.state = State.MODERATION_COMPLETE
            self.banned = True
            self.removed = True
            self.outcome = "The post did contain a livestream of terrorism and was removed. The user has also been banned. The post will be stored to assist in future legal proceedings and authorities have been notified."
            return["This post will be removed and the user will be banned. The post will be stored to assist in future legal proceedings and authorities will be notified. The moderation process for this report is now complete."]

        elif self.state == State.AWAITING_SOURCE:
            self.state = State.AWAITING_AID
            return["Can this livestream enable the victim to acquire help? Please confirm by typing 'Y'. Type 'N' or any other key if not."]

        if self.state == State.AWAITING_AID and message.content == self.YES_KEYWORD:
            self.state = State.MODERATION_COMPLETE
            self.flagged = True
            self.outcome = "The post did contain a livestream of terrorism however, it was shared by a victim and was found to be useful for the victim to signal for help. Therefore, the post remains visible on our platform. We have flagged the post to minimize distress to other users. Authorities have also been notified."
            return ["This post will be flagged with a warning but kept visible in order to signal for help. Authorities will be forwarded the livestream."]

        elif self.state == State.AWAITING_AID:
            self.state = State.MODERATION_COMPLETE
            self.removed = True
            self.outcome = "The post did contain a livestream of terrorism and has been removed. Since the livestream was shared by a victim, we have not banned the user. The post will be stored to assist in future legal proceedings and authorities have been notified."
            return ["This post will be removed but stored to assist in future legal proceedings and authorities will be notified. The moderation process for this report is now complete."]

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE

    def moderation_complete(self):
        return self.state == State.MODERATION_COMPLETE

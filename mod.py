from enum import Enum, auto
import discord
import re

class State(Enum):
    MODERATION_START = auto()
    AWAITING_SOURCE = auto()
    AWAITING_TERRORISM = auto()
    AWAITING_LIVESTREAM = auto()
    AWAITING_AID = auto()
    AWAITING_CATEGORY = auto()
    AWAITING_IMMEDIACY = auto()
    AWAITING_DECISION = auto()
    MODERATION_COMPLETE = auto()

class Moderator:
    START_KEYWORD = "start"
    NEXT_KEYWORD = "next"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    P_KEYWORD = "P"
    V_KEYWORD = "V"
    YES_KEYWORD = "Y"
    NO_KEYWORD = "N"
    ALL_OPTIONS = [START_KEYWORD, NEXT_KEYWORD, CANCEL_KEYWORD, HELP_KEYWORD, P_KEYWORD, V_KEYWORD, YES_KEYWORD, NO_KEYWORD]

    reasons = {"A": "false information", "B": "spam", "C": "harassment", "D": "violence", "E": "terrorism", "F": "hate speech"}

    def __init__(self, report):
        self.state = State.MODERATION_START
        self.report = report
        self.outcome = ""
        self.banned = False
        self.removed = False
        self.flagged = False
        self.category = None
        self.immediate = False
        self.livestream = False
        self.victim = False
        self.helpful = False

    async def handle_message(self, message):
        '''
        This function makes up the meat of the moderator-side handling flow. It defines how we transition between states and what
        prompts to offer at each of those states.
        '''
        if self.state == State.MODERATION_START:
            q = "Has this post been correctly categorized? Type 'Y' if yes. Otherwise type one of the following keys to select why this post is harmful. \nA: False Information\nB: Spam \nC: Harassment \nD: Violence \nE: Terrorism \nF: Hate Speech \nG: Not Harmful" \
            if self.report.reportReason not in self.reasons else "Type one of the following keys to identify why is this post is harmful? \nA: False Information\nB: Spam \nC: Harassment \nD: Violence \nE: Terrorism \nF: Hate Speech"

            self.state = State.AWAITING_CATEGORY
            if (self.report.auto):
                return(["There is a report for the following message: " + "```" + self.report.message.author.name + ": " + self.report.message.content + "```" + \
                    "This post was automatically flagged by our bot. \nPlease answer some questions to help our friendly flagging bot. \nIs this post actually being live streamed? " + \
                    "If so, please confirm by typing \'Y\'. Type \'N\' if not."])
            #reason = self.report.reportReason
            details = "" if not self.report.extra else "The user provided the following additional information: " + self.report.extra
            live = "It is reported to contain a livestream." if self.report.livestream else ""
            imm = self.report.immediate*"ongoing or immediate "
            return(["There is a report for the following message: " + "```" + self.report.message.author.name + ": " + self.report.message.content + "```" + \
            "The post was reported for "  + imm + self.report.reportReason + ". " + details + live + "\n" + q])

        if self.state == State.AWAITING_CATEGORY:
            if message.content == 'G':
                self.state = State.MODERATION_COMPLETE
                self.outcome = "The post was not found to be harmful and no action has been taken at this time."
                return["The moderation process for this report is now complete."]
            elif message.content == self.YES_KEYWORD:
                self.category = self.report.reportReason
            else:
                self.category = self.reasons[message.content]
            self.state = State.AWAITING_IMMEDIACY
            return["Do the contents of this post pose an ongoing or immediate threat? Type 'Y' for yes and 'N' for no."]

        if self.state == State.AWAITING_IMMEDIACY:
            if message.content == self.YES_KEYWORD:
                self.immediate = True
                self.state = State.AWAITING_LIVESTREAM
                return["You stated that the contents of this post pose an ongoing or immediate threat. Is this post being livestreamed? Type 'Y' for yes and 'N' for no."]
            else:
                self.immediate = False
                self.state = State.AWAITING_DECISION
                return[self.get_recommendations()]

        if self.state == State.AWAITING_LIVESTREAM:
            if message.content == self.YES_KEYWORD:
                self.state = State.AWAITING_SOURCE
                self.livestream = True
                return["Who is livestreaming this event? If it is the perpetrator please type 'P'. If it is a victim, type 'V'."]
            else:
                self.state = State.AWAITING_DECISION
                self.livestream = False
                return[self.get_recommendations()]

        if self.state == State.AWAITING_SOURCE:
            if message.content == self.P_KEYWORD:
                self.victim = False
                self.state = State.AWAITING_DECISION
                return[self.get_recommendations()]
                #return["This post will be removed and the user will be banned. The post will be stored to assist in future legal proceedings and authorities will be notified. The moderation process for this report is now complete."]
            elif message.content == self.V_KEYWORD:
                self.victim = True
                self.state = State.AWAITING_AID
                return["Can this livestream enable the victim to acquire help? Please confirm by typing 'Y'. Type 'N' if not."]

        if self.state == State.AWAITING_AID:
            self.state = State.AWAITING_DECISION
            if message.content == self.YES_KEYWORD:
                self.helpful = True
            else:
                self.helpful = False
            return[self.get_recommendations()]

        if self.state == State.AWAITING_DECISION:
            self.state = State.MODERATION_COMPLETE
            actions = [int(i) for i in message.content.split(",")]
            return[self.get_outcome(actions)]

        if (message.content == self.CANCEL_KEYWORD):
            return []
        return ["Not a valid option, please choose again from the prompt or type 'cancel' to cancel moderation."]

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE

    def moderation_complete(self):
        return self.state == State.MODERATION_COMPLETE

    def get_recommendations(self):
        options = "Here are all your options for taking action.\n 1. Store report against user \n2. Flag message \n3. Delete message \n4. Ban user \n5. Store post for legal proceedings\n"
        background = "You have determined that this post is harmful because of " + self.category + " and that there is " + (1-self.immediate)*"no " + (self.immediate)*"an " + "ongoing or immediate threat. "
        h = "that can" + (1-self.helpful)*"not " +" enable them to acquire help."
        s = " from " + self.victim*("a victim ") + (1-self.victim)*("a perpetrator.") + self.victim*h
        ls = "" if not self.immediate else "You have also determined that the post does " + (1-self.livestream)*"not " + "contain a livestream" + (1-self.livestream)*"." + self.livestream*s + " "
        d = "" if not self.report.extra else "Additionally, the user has provided the following context: '" + self.report.extra + "'. "

        recs = set()
        if self.category:
            recs.add(1)
        if self.livestream:
            if (self.victim and self.helpful):
                recs.add(2)

            else:
                if not self.victim:
                    recs.add(4)
                recs.add(3)
        if self.category and not self.livestream:
            recs.add(2)
        print("recs beforehand: ", recs)
        if recs:
            recs = ", ".join(sorted(list(str(i) for i in recs))) + "."
        else:
            recs = "none of the above."

        r = "Given the provided information about this post, we recommend " + recs + " Please type the numbers of the steps you'd like to take separated by commas."

        return background+ls+d+options+r

    def get_outcome(self, actions):
        mp = {1:"This report has been stored against the user.", 2: "The message has been flagged.", 3:"The message has been deleted.", 4:"The user has been banned.", 5:"The post has been stored for legal proceedings."}
        res = ""
        for i in sorted(actions):
            if ((i != 2) or (i ==2 and 3 not in actions)) and i in mp.keys():
                res += mp[i] + " "
                if i == 2:
                    self.flagged = True
                if i == 3:
                    self.removed = True
                if i == 4:
                    self.banned = True
        self.outcome = res
        res += "The moderation process for this report is now complete."
        return res

# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
from mod import Moderator
from google_trans_new import google_translator  

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'token.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']
    perspective_key = tokens['perspective']


class ModBot(discord.Client):
    def __init__(self, key):
        intents = discord.Intents.default()
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to their report
        self.userInfo = {}
        self.mod = None
        self.perspective_key = key
        self.addReport = None
        self.modReport = 0
        self.currReporter = None
        self.priority_reports_arr = None

        self.threshold = 0.7
        self.alpha = 0.1 # Hyperparameter to change weighting of threshold learning

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs).
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel.
        '''
        # Ignore messages from us
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)


    def add_report(self, message):
        author_id = message.author.id
        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = [Report(self)]
            self.userInfo[author_id] = [message.author.name, message.channel]
            self.addReport = self.reports[author_id][-1]

        elif author_id in self.reports and not self.addReport:
            self.reports[author_id] += [Report(self)]
            self.addReport = self.reports[author_id][-1]

    def delete_report(self, message, report):
        author_id = message.author.id
        self.reports[author_id].remove(report)
    
    async def share_report(self, author_id, report, message):
        mod_channel = self.mod_channels[report.message.guild.id]
        await mod_channel.send(f"User {message.author} has filed a report. To start handling requests, type 'start'.")
        

    async def get_messages(self, message):
        responses = await self.mod.handle_message(message)
        for r in responses:
            await self.mod_channels[message.guild.id].send(r)

    def calculate_score(self, score):
        threat = score["THREAT"]
        toxicity = score["TOXICITY"]
        threat_exp = score["THREAT_EXPERIMENTAL"]
        return 0.8 * threat + 0.1 * toxicity + 0.1 * threat_exp

    def set_priority_and_translate_all_reports(self):
        translator = google_translator()
        for k, v in self.reports.items():
            for report in v:
                # report.message.content = translator.translate(report.message.content, lang_tgt='en')
                perspective = self.eval_text(report.message)
                score = self.calculate_score(perspective)
                report.priority = 100 * score

    def build_sort_reports(self):
        if (self.reports):
            self.set_priority_and_translate_all_reports()
            reports = [[author_id, report] for author_id in self.reports.keys() for report in self.reports[author_id]]
            self.priority_reports_arr = sorted(reports, key = lambda x: x[1].priority, reverse=True) # only sort once on init

    async def init_mod(self, message):
        if (self.reports):
            self.currReporter = self.priority_reports_arr[0][0]
            self.modReport = self.priority_reports_arr[0][1]
            self.mod = Moderator(self.modReport)
            await self.get_messages(message)
            
    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        # Only respond to messages if they're part of a reporting flow
        if message.content == Report.START_KEYWORD:
            self.add_report(message)
            responses = await self.addReport.handle_message(message)
            for r in responses:
                await message.channel.send(r)
            return
        
        if (self.addReport):
            responses = await self.addReport.handle_message(message)
            for r in responses:
                await message.channel.send(r)
            if message.content == Report.CANCEL_KEYWORD or self.addReport.report_complete():
                self.addReport = None
                self.delete_report(message, self.addReport)
                return
            # If the report is ready for moderation, send content to mod channel
            elif self.addReport.awaiting_moderation():
                await self.share_report(author_id, self.addReport, message)
                self.addReport = None        

    async def handle_mod_message(self, message):

        if (message.content == Moderator.START_KEYWORD or message.content == Moderator.NEXT_KEYWORD) and not self.reports:
            next = "There are no remaining reports on this channel at this time."
            await self.mod_channels[message.guild.id].send(next)
            return
        
        if (message.content == Moderator.START_KEYWORD):
            self.build_sort_reports()
            await self.init_mod(message)
            return

        if (message.content == Moderator.NEXT_KEYWORD) and not self.mod:
            await self.init_mod(message)
            return

        if (self.mod):
            await self.get_messages(message)
            if (message.content == Moderator.CANCEL_KEYWORD):
                self.currReporter = None
                self.modReport = None
                self.mod = None
                self.priority_reports_arr = None
                next = "Cancelled moderating, to resume please start again by typing 'start'."
                await self.mod_channels[message.guild.id].send(next)
                return

            if self.mod.moderation_complete():
                await self.send_updates(self.mod.outcome)

                if (self.mod.banned or self.mod.removed or self.mod.flagged):
                    self.threshold = max(0.5, self.threshold + self.alpha * self.modReport.priority/100) # realigning threshold

                self.reports[self.currReporter].remove(self.modReport)
                self.priority_reports_arr.pop(0)
                if len(self.reports[self.currReporter]) == 0:
                    self.reports.pop(self.currReporter)
                self.currReporter = None
                self.modReport = None
                self.mod = None
                next = "To continue moderating remaining reports type 'next'." if self.reports else "There are no remaining reports at this time."
                await self.mod_channels[message.guild.id].send(next)


            
    
    async def send_updates(self,outcome):
        reporter_name = self.userInfo[self.currReporter][0]
        reporter_channel = self.userInfo[self.currReporter][1]

        reported_name = self.modReport.message.author.name
        reported_id = self.modReport.message.author.id
        reported_user = await self.fetch_user(reported_id)


        post_channel = self.modReport.message.channel
        flagged = self.mod.flagged
        removed = self.mod.removed
        banned = self.mod.banned

        if removed and banned:
            await post_channel.send(f"The following post: ```{reported_name}:{self.modReport.message.content}```\nwas found to contain a livestream of terrorism and has now been removed. The user has also been banned from our platform and authorities have been notified.")
            await reported_user.send(f"Hi {reported_name}. Your post ```{self.modReport.message.content}```\nwas found to contain a livestream of terrorism and has now been removed. You have also been banned from our platform.")
        elif removed and not banned:
            await post_channel.send(f"The following post: ```{reported_name}:{self.modReport.message.content}```\nwas found to contain a livestream of terrorism. It has been removed and authorities have been notified.")
            await reported_user.send(f"Hi {reported_name}. Your post ```{self.modReport.message.content}```\nwas found to contain a livestream of terrorism. It has been removed and authorities have been notified.")
        elif flagged:
            await post_channel.send(f"The following post: ```{reported_name}:{self.modReport.message.content}```\nwas found to contain a livestream of terrorism. It remains visible in order to signal for help. Authorities have been notified.")
            await reported_user.send(f"Hi {reported_name}. Your post ```{self.modReport.message.content}```\nwas found to contain a livestream of terrorism. It has been flagged but remains visible in order to signal for help. Authorities have been notified.")

        await reporter_channel.send(f"Hi {reporter_name}! Thank you for your recent report on the following post: ```{reported_name}:{self.modReport.message.content}```\nIt has been reviewed. {outcome}")

    async def handle_channel_message(self, message):

        if message.channel.name == f'group-{self.group_num}-mod':
            await self.handle_mod_message(message)

        elif message.channel.name == f'group-{self.group_num}':
            await self.auto_handle_message(message)

        else:
            return

    async def auto_handle_message(self, message):
        perspective = self.eval_text(message)
        score = self.calculate_score(perspective)
        if (score > self.threshold): #add to reporting flow for moderators
            self.reports[message.author.id] = message
        return
        

    def eval_text(self, message):
        '''
        Given a message, forwards the message to Perspective and returns a dictionary of scores.
        '''
        PERSPECTIVE_URL = 'https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze'

        url = PERSPECTIVE_URL + '?key=' + self.perspective_key
        data_dict = {
            'comment': {'text': message.content},
            'languages': ['en'],
            'requestedAttributes': {
                                    'THREAT_EXPERIMENTAL' : {},
                                    'SEVERE_TOXICITY': {}, 'PROFANITY': {},
                                    'IDENTITY_ATTACK': {}, 'THREAT': {},
                                    'TOXICITY': {}, 'FLIRTATION': {}
                                },
            'doNotStore': True
        }
        response = requests.post(url, data=json.dumps(data_dict))
        response_dict = response.json()

        scores = {}
        for attr in response_dict["attributeScores"]:
            scores[attr] = response_dict["attributeScores"][attr]["summaryScore"]["value"]

        return scores

    def code_format(self, text):
        return "```" + text + "```"


client = ModBot(perspective_key)
client.run(discord_token)

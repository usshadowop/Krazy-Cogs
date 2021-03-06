import discord
import asyncio
import time
import re
import os # This is required because you will be creating folders/files
from .utils.dataIO import dataIO  # This is pulled from Twentysix26's utils
from cogs.utils import checks
from discord.ext import commands

jsonPath = "data/mudclient/settings.json"
maxWaitTime = 2
maxBufferLength = 20

class mudclient:
    """ This cog allows users to connect to MUD servers and play MUD's in discord """
    #init cog saving all important json data
    def __init__(self, bot):
        self.bot = bot
        self.clients = []
        self.file_path = jsonPath
        self.settings = dataIO.load_json(self.file_path)
        self.prefix = self.settings["prefix"]


    @commands.command(pass_context = True, aliases = ["connect"])
    async def startConnection(self, ctx):
        """Creates a client session for the user in the current channel"""
        user = ctx.message.author
        channel = ctx.message.channel
        if not self.clients:
            hasSession = False
        else:
            for c in self.clients:
                if(c.author == user and c.channel.id == channel.id):
                    hasSession = True
                else:
                    hasSession = False

        if(hasSession != True):
            try:
                clientThread = client(self.bot, user, channel,self.settings["Server"])
                self.bot.loop.create_task(clientThread.start())
                self.clients.append(clientThread)
                await self.bot.say("```Client Started.\nPlease precede all commands with {}\nClose Session with {}EXIT```".format(self.prefix, self.prefix))
            except RuntimeError as e:
                print(e)
                await self.bot.say("```Could not start Client Please talk to your bot owner```")
        else:
            await self.bot.say("```you already have a client running in this channel, please remeber to close it with {}EXIT```".format(self.prefix))


    @commands.group(pass_context=True)
    @checks.is_owner()
    async def clientsettings(self, ctx):
        """Settings for MUDClient"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @commands.command(pass_context = True, aliases = ["numclients"])
    async def numconnections(self, ctx):
        numClient = 0
        for c in self.clients:
            if c.channel.id == ctx.message.channel.id:
                numClient = numClient + 1

        if numClient == 0:
            await self.bot.say("There are no active clients in this channel")
        elif numClient == 1:
            await self.bot.say("There is 1 active client in this channel")
        else:
            await self.bot.say("There are {} active clients in this channel".format(numClient))

    @commands.command(pass_context = True)
    async def haveclient(self, ctx):
        hasSession = False
        for c in self.clients:
            if c.channel.id == ctx.message.channel.id and c.author == ctx.message.author:
                hasSession = True

        if hasSession:
            await self.bot.say("{} you have a client running in this channel".format(ctx.message.author.mention))
        else:
            await self.bot.say("{} you do not have a client running in this channel".format(ctx.message.author.mention))

    @clientsettings.command(name="prefix", pass_context=True)
    async def _prefix(self, ctx, prefix:str):
        """Set the prefix for the MUDClient"""

        self.prefix = prefix
        self.settings['prefix'] = self.prefix
        dataIO.save_json(jsonPath, self.settings)
        await self.bot.say('`Changed client prefix to {} `'.format(self.prefix))

    @clientsettings.command(name="server", pass_context=True)
    async def _server(self, ctx, name:str, server: str, port = 23):
        """Sets the Server the client connects to.\nUse [p]clientsettings server [name] [address] [port]\nWarning do not use while clients connected"""

        self.settings['Server']['Name'] = name
        self.settings['Server']['IP'] = server
        self.settings['Server']['Port'] = port
        dataIO.save_json(jsonPath, self.settings)
        await self.bot.say('```Changed server to {} ```'.format(self.settings['Server']['Name']))


    #get client messages
    async def on_message(self, message):
        #check if user has a client otherwise ignore message
        if not self.clients:
            hasSession = False
        else:
            for client in self.clients:
                if(client.author == message.author and client.channel.id == message.channel.id):
                    hasSession = True
                    session = client
                else:
                    hasSession = False

        if hasSession:

            if not self.prefix:
                check_folder()
                check_file()

            if message.content.startswith(self.prefix):
                command = message.content.split(self.prefix)[1]
                print(command)
                if not command:
                    return
                if command == "EXIT":
                    await session.sendmessage(command.lower())
                    session.running = False
                    self.clients.remove(session)
                    await self.bot.send_message(destination = message.channel, content = "{} successfully closed client.".format(message.author.mention))
                else:
                    await session.sendmessage(command)
        else:
            return



def setup(bot):
    check_folders() # runs the folder check on setup that way it exists before running the cog
    check_files() # runs the check files function to make sure the files you have exists
    bot.add_cog(mudclient(bot))

def check_folders(): # This is how you make your folder that will hold your data for your cog
    if not os.path.exists("data/mudclient"): # Checks if it exists first, if it does, then nothing executes
        print("Creating data/mudclient folder...")  # You can put what you want here. Prints in console for the owner
        os.makedirs("data/mudclient") # This makes the directory


def check_files(): # This is how you check if your file exists and let's you create it
    system = {"Server" : {"Name" : "telehack", "IP" : "telehack.com", "Port" : 23},
                "prefix" : "#"}
    f = jsonPath # f is the path to the file
    if not dataIO.is_valid_json(f): # Checks if file in the specified path exists
        print("Creating default settings.json...") # Prints in console to let the user know we are making this file
        dataIO.save_json(f, system)


class client():

    def __init__(self, bot, user: discord.User, channel, server):
        self.author = user
        self.channel = channel
        self.bot = bot
        self.session = server["Name"]
        self.server = server

    async def connect(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(self.server["IP"], self.server["Port"])
            self.running = True
        except:
            print("Bad Connection")
            raise RuntimeError("Could not connect to server")

    async def start(self):
        try:
            await self.connect()
        except RuntimeError as e:
            raise e
        timeSinceLast = 0
        lines = 0
        LastTime = time.time()
        readBuffer = None
        while self.running:
            try:
                read = await self.reader.readline()
            except ConnectionError as con:
                print("Connection Closed: {}".format(con))
                self.reader, self.writer = await asyncio.open_connection(self.server["IP"], self.server["Port"])
                continue
            except EOFError as e:
                print("something happened trying to recover by flushing buffer")
                read = ""
            if read == "":
                self.reader.feed_eof()
                timeSinceLast = time.time() - LastTime
                print("{}seconds since last line ".format(timeSinceLast))
            else:
                read = read.decode('unicode_escape')
                ansi_escape = re.compile(r'[\x02\x0F\x16\x1D\x1F\xFF]|\x03(\d{,2}(,\d{,2})?)?')
                read = ansi_escape.sub('', read)
                if readBuffer is None:
                    readBuffer = read
                else:
                    readBuffer = readBuffer + read
                lines = lines + 1
                LastTime = time.time()
            if not readBuffer:
                continue
            if timeSinceLast > maxWaitTime or lines == maxBufferLength or self.reader.at_eof():
                lines = 0
                try:
                    await self.bot.send_message(destination = self.channel, content="{}\n```--------------------------------------------------------------------\n{}\n--------------------------------------------------------------------```".format(self.author.mention,str(readBuffer)))
                except:
                    print(readBuffer)
                    await self.bot.send_message(destination = self.channel, content = "Could not Display messages")
                readBuffer = None
            self.writer.close()



    async def sendmessage(self, message:str):
        command = "{}\r\n".format(message)
        command = command.encode('utf-8')
        print(command)
        try:
            self.writer.write(command)
            await self.writer.drain()
            print("write successfull")
        except ConnectionError as e:
            print("Connection Lost, reconnecting and retrying")
            self.reader, self.writer = await asyncio.open_connection(self.server["IP"], self.server["Port"])
            self.writer.write(command)
            await self.writer.drain()

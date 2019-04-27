#!/usr/bin/env python
# encoding: utf-8
import sys, os, platform, time, json, subprocess
import base64, numpy, datetime, threading

# Discrod 
import discord, asyncio

# Twitch
import requests, getopt 

# Color
from colorama import init
init()
from colorama import Fore, Back, Style
S_b, S_r, F_r, F_w, F_c, F_g, F_y, F_b = (Style.BRIGHT, Style.RESET_ALL, Fore.RED, Fore.WHITE, Fore.CYAN, Fore.GREEN, Fore.YELLOW, Fore.BLUE)

# DISCORD PARAM
discord_key             = ""
vocal_channel_id        = ""
game_responce           = "Twitch onlive"
bot_id                  = ""
logprint                = True
start_responce          = "Starting on "
stop_responce           = "Broadcasting stopping..."
nostart_responce        = "A broadcast is already in progress"
nostop_responce         = "No broadcast is in progress"

connect_responce        = "Connecting..."
noconnect_responce      = "Already connected"

disconnect_responce     = "Disconnecting..."
nodisconnect_responce   = "Already disconnected"


status_responce         = ""

# TWITCH PARAM
Tclient_id              = ""
Toauth_token            = ""
stream_url              = ""
looping                 = False
disconnect_vocal        = False

class TwitchRecorder(threading.Thread):
    def __init__(self, client_id, oauth_token, username, quality, client, message):

        self.refresh        = 30.0
        self.root_path      = "/"

        self.client_id      = client_id
        self.oauth_token    = oauth_token
        self.username       = username
        self.quality        = quality
        self.client         = client
        self.message        = message

        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True  # Daemonize thread
        thread.start()        # Start the execution        

    def run(self):
        # path to recorded stream
        self.recorded_path = os.path.join(self.root_path, "recorded", self.username)

        # create directory for recordedPath and processedPath if not exist
        if(os.path.isdir(self.recorded_path) is False):
            os.makedirs(self.recorded_path)

        # make sure the interval to check user availability is not less than 15 seconds
        if(self.refresh < 15):
            print("Check interval should not be lower than 15 seconds.")
            self.refresh = 15
            print("System set check interval to 15 seconds.")
        
        print("Checking for", self.username, "every", self.refresh, "seconds. Record with", self.quality, "quality.")

        self.loopcheck()

    def check_user(self):
        url = 'https://api.twitch.tv/kraken/streams/' + self.username
        info = None
        status = 3
        try:
            r = requests.get(url, headers = {"Client-ID" : self.client_id}, timeout = 15)
            r.raise_for_status()
            info = r.json()
            if info['stream'] == None:  status = 1
            else:                       status = 0
        except requests.exceptions.RequestException as e:
            if e.response:
                if e.response.reason == 'Not Found' or e.response.reason == 'Unprocessable Entity': status = 2
        return status, info

    def loopcheck(self):
        global status_responce, looping, stream_url
        while looping:
            status, info = self.check_user()
            if status == 2:
                status_responce = "Username not found. Invalid username or typo"
                time.sleep(self.refresh)
            elif status == 3:
                status_responce = str(datetime.datetime.now().strftime("%Hh%Mm%Ss")) + " unexpected error. will try again in 5 minutes."
                time.sleep(300)
            elif status == 1:
                status_responce = self.username + " currently offline, checking again in " + str(self.refresh) +  " seconds."
                time.sleep(self.refresh)
            elif status == 0:
                try:
                    status_responce = self.username + " online. Broadcasting is launched."
                    
                    # start streamlink process
                    out = subprocess.Popen(["streamlink", "--twitch-oauth-token", self.oauth_token, "twitch.tv/" + self.username, self.quality, "--player-external-http", "--ringbuffer-size", "50M", "--player-no-close", "--player-passthrough", "rtmp"], stdout=subprocess.PIPE)

                    for line in out.stdout:
                        print(">", line.decode("utf-8"))
                        if len(line.decode("utf-8").split("://")) > 1:
                            stream_url = "http://" + line.decode("utf-8").split("://")[1].strip()

                    if not self.stop: time.sleep(self.refresh)

                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    print(exc_type, fname, exc_tb.tb_lineno)

        if not looping: print ("STOP")

# Ditch
try:
    client          = discord.Client()
    
    @client.event
    async def on_ready():
        global vocal_channel_id

        #os.system('cls' if os.name=='nt' else 'clear')

        print(S_b, F_g,'\n  Informations', S_r)
        print(S_b, F_r, discord_key, S_r)
        print(S_b, F_r, vocal_channel_id, S_r)
        print(S_b, F_g,'------------------', S_r)

        print(S_b, F_g,'\n  Channel', S_r)
        print(S_b, F_w, vocal_channel_id, S_r)
        print(S_b, F_g,'------------------', S_r)

        await client.change_presence(game=discord.Game(name=game_responce))

    @client.event
    async def on_message(message):
        global looping, stream_url, vocal_channel_id, disconnect_vocal
        try:
            if message.author.id != bot_id:
                if message.content.startswith('!ditch start'):
                    Tchannel = message.content.split('start')[1].strip()
                    if Tchannel:
                        if not looping:
                            await client.send_message(message.channel, start_responce + Tchannel + "...")
                            looping = True
                            TwitchRecorder(client_id=Tclient_id, oauth_token=Toauth_token, username=Tchannel, quality="audio_only", client=client, message=message)
                        else:
                            await client.send_message(message.channel, nostart_responce)

                elif message.content.startswith('!ditch status'):
                    await client.send_message(message.channel, status_responce)

                elif message.content.startswith('!ditch connect'):

                    if stream_url:
                        await client.send_message(message.channel, connect_responce)
                        disconnect_vocal = False

                        # Voice Channel
                        voice = await client.join_voice_channel(client.get_channel(str(vocal_channel_id)))

                        player = voice.create_ffmpeg_player(stream_url)
                        player.start()

                        loop = True
                        while loop:
                            if disconnect_vocal: loop = False
                            if player.is_done(): loop = False
                            time.sleep(1)  

                        voice.disconnect()
                    else: await client.send_message(message.channel, noconnect_responce)

                elif message.content.startswith('!ditch disconnect'): 
                    if voice:
                        disconnect_vocal = True
                        await client.send_message(message.channel, disconnect_responce)
                    else: await client.send_message(message.channel, nodisconnect_responce)

                elif message.content.startswith('!ditch stop'):
                    if looping:                    
                        looping = False
                        await client.send_message(message.channel, stop_responce)
                    else:
                        await client.send_message(message.channel, nostop_responce)                        

        except Exception as e:
            if logprint: await client.send_message(message.channel, "```" + str(e) + "```")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

    try:                client.run(discord_key)
    except Exception:   pass
    client.close()

except KeyboardInterrupt as e:
    client.send_message(message.channel, stop_responce)
    sys.exit(0)

time.sleep(5)
subprocess.Popen([sys.executable] + Sargs, creationflags=subprocess.CREATE_NEW_CONSOLE)
time.sleep(5)
sys.exit(0)
import os
import random
from os import system
import discord
import youtube_dl
from discord.ext import commands
from discord.utils import get
import asyncio

bot = commands.Bot(command_prefix="=")
youtube_dl.utils.bug_reports_message = lambda: ''


@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.online, activity=discord.Game('Xee Me !'))
    print('Xebot is READYYY!')


@bot.event
async def on_member_join(member):
    await member.create_dm()
    await member.dm_channel.send(
        f'Hi {member.name}, welcome to my Discord server!'
    )


@bot.event
async def on_member_leave(member):
    await member.dm_channel.send(
        f'Bye {member.name}, Thanks for coming!!'
    )


@bot.command()
async def function(ctx):
    if ctx.author == bot.user:
        return
    await ctx.send(f'greet - Greet user\n'
                    f'ping - Check ping\n'
                    f'clear - Clear last 6 msg\n'
                   f'roll - Roll 1-10\n'
                   f'flip - Flip a coin\n'
                   f'game - Choose a game to ply\n'
                   f'join [channel name] - Join a channel\n'
                   f'stop - stop the music and disconnect\n'
                   f'play [youtube link] - plays a youtube audio\n'
                   f'local [play local file] - plays audio from local directory\n'
                   f'pause - pause audio\n'
                   f'resume - Resume audio\n'
    )


@bot.command()
async def greet(ctx):
    if ctx.author == bot.user:
        return
    await ctx.send(f'{ctx.author.name}씨 안녕하세요 ! ')


@bot.command()
async def ping(ctx):
    if ctx.author == bot.user:
        return
    await ctx.send(f'Ping : {round(bot.latency * 1000)}ms')


@bot.command()
async def clear(ctx, amount=6):
    if ctx.author == bot.user:
        return
    await ctx.channel.purge(limit=amount)


@bot.command()
async def roll(ctx):
    if ctx.author == bot.user:
        return
    numbers = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']

    await ctx.send(f'Roll 1-10 : {random.choice(numbers)}')


@bot.command()
async def flip(ctx):
    if ctx.author == bot.user:
        return
    coin = ['HEAD', 'TAILS']
    await ctx.send(f'Flip a coin : {random.choice(coin)}')


@bot.command()
async def game(ctx):
    if ctx.author == bot.user:
        return
    games = ['Dota 2', 'Brawlhalla', 'Fortnite', 'CSGO', 'Mobile Legends', 'Minecraft']
    await ctx.send(f' Play {random.choice(games)}')


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()
        await ctx.send(f'Joined channel {channel}')

    @commands.command()
    async def local(self, ctx, *, query):
        """Plays a file from the local filesystem"""

        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
        ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(query))

    @commands.command()
    async def play(self, ctx, *, url):
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(player.title))

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Changed volume to {}%".format(volume))

    @commands.command()
    async def download(self, ctx, *, url):
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(player.title))

    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")
        else:
            ctx.voice_client.pause()
            await ctx.send("Paused")

    @commands.command()
    async def resume(self, ctx):
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")
        else:
            ctx.voice_client.resume()
            await ctx.send("Resumed")

    @commands.command()
    async def disconnect(self, ctx):
        """Stops and disconnects the bot from voice"""
        await ctx.voice_client.disconnect()
        await ctx.send(f'Disconnected')

    @play.before_invoke
    @local.before_invoke
    @download.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


bot.add_cog(Music(bot))

bot.run('Njk3MDc4NjkwMTM5MzQwOTAw.Xo1H2w.RdzZzklUNCBxJcA9Rca07sIam8k')


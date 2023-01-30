import aiohttp
import asyncio
import discord
import datetime
import itertools
import pytube
import time
import typing

from async_timeout import timeout
from discord.ext import commands
from functools import partial
from random import shuffle
from youtube_dl import YoutubeDL

YTDL_FORMATS = {
    'format' : 'bestaudio/best',
    'outtmpl' : 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames' : True,
    'noplaylist' : True,
    'nocheckcertificate' : True,
    'ignoreerrors' : False,
    'logtostderr' : False,
    'quiet' : True,
    'no_warnings': True,
    'default_search' : 'auto',
    'source_address' : '0.0.0.0'
}

FFMPEG_OPTIONS = {
    'before_options': '-nostdin',
    'options': '-vn'
}

LYRICS_URL = "https://some-random-api.ml/lyrics?title="

ytdl = YoutubeDL(YTDL_FORMATS)

class VoiceConnectionError(commands.CommandError):
    """Custom Exception class for connection errors."""


class InvalidVoiceChannel(VoiceConnectionError):
    """Exception for cases of invalid Voice Channels."""

class ProgressBar():
    """Represents a progress bar, used for the now playing command.
    
    Attributes:
        vid_length (int): Length of the video.
        size (20): Length of the progress bar.
        line (str): Line on the progress bar.
        slider (str): Dot representing the current progress on the bar.
    """
    def __init__(self, vid_length: int):
        self.vid_length = vid_length
        self.size = 20
        self.line = "▬"
        self.slider = "🔘"

    def get_progress(self, elapsed):
        """Returns an updated progress bar representing the elapsed time.
        
        @param:
            elapsed (int): The elapsed time in the video.
            
        @returns:
            bar (str): A string displaying a progress bar, to be used within
            a discord.Embed
        """
        if elapsed > self.vid_length:
            bar = self.line * (self.size - 1) + self.slider
            return bar
        else:
            percent = elapsed / self.vid_length
            progress = round(self.size * percent)
            remaining = self.size - progress
            progress_txt= (self.line * progress) + self.slider
            remaining_txt = self.line * remaining
            bar = progress_txt + remaining_txt
            return bar


class YTDLSource(discord.PCMVolumeTransformer):
    """Represents a source object for a youtube video.
    
    Attributes:
        requester (discord.Member): The user who requested the video.
        duration (int): The video duration.
        title (str): The video title.
        web_url (str): The video url.
    """
    def __init__(self, source, *, data, requester, duration: int):
        super().__init__(source)
        self.requester = requester
        self.duration = duration
        self.title = data.get('title')
        self.web_url = data.get('webpage_url')

    def __getitem__(self, item: str):
        """Allows access to attributes similar to a dict."""
        return self.__getattribute__(item)
    
    @classmethod
    async def get_source_playlist(cls, ctx, song_link: str, *, loop, download=False):
        pass
    
        loop = loop or asyncio.get_event_loop()
        
        to_run = partial(ytdl.extract_info, url=song_link, download=download)
        data = await loop.run_in_executor(None, to_run)
        
        if 'entries' in data:
            data = data['entries'][0]
            
        if download:
            source = ytdl.prepare_filename(data)
        else:
            return {
                'webpage_url': data['webpage_url'],
                'requester': ctx.author,
                'title': data['title'],
                'duration' : data['duration']}

        return cls(discord.FFmpegPCMAudio(source), data=data, requester=ctx.author)

    @classmethod
    async def get_source_song(cls, ctx, search: str, *, loop, download=False, repeat=False):
        """Gets the source for the requested video's link.
        
        @param:
            search (str): The song to search for
            loop (AbstractEventLoop or None): The current event loop.
            download (Bool): Downloads the video if True, stream if False.
            repeat (Bool): Repeats the video if True, doesn't if False.
        """
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        if 'entries' in data:
            data = data['entries'][0]

        ## If the current song is not looping.
        if not repeat:
            await ctx.send(F"\nAdded **{data['title']}** to the Queue.", delete_after=15)

        if download:
            source = ytdl.prepare_filename(data)
        else:
            return {
                'webpage_url': data['webpage_url'],
                'requester': ctx.author,
                'title': data['title'],
                'duration' : data['duration']}

        return cls(discord.FFmpegPCMAudio(source), data=data, requester=ctx.author)

    @classmethod
    async def prepare_stream(cls, data, *, loop):
        """Prepares a stream, instead of downloading."""
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']
        duration = data['duration']
        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url']), data=data, requester=requester, duration=duration)


class MusicPlayer:
    """Assigned to each guild currently using the bot.
    
    Is created when the bot joins a voice channel, and is destroyed upon
    leaving the channel.
    
    Attributes:
        _channel (discord.ctx.channel): The current discord channel.
        _cog (discord.ctx.cog): The current cog.
        current (YTDLSource): The currently playing song.
        bot (discord.Member.bot): This discord bot.
        _guild (discord.guild): The current discord guild.
        next (asyncio.Event): The next event (song) to be played from the queue.
        np (YTDLSource): The current source.
        queue (asyncio.Queue): A container of all queued songs.
        start_time (float): The start time of the currently playing song.
        delta_time (float): The elapsed time in the song.
        volume (float): The current volume of the video player, represented as
        as a value from 0 to 1.
    """
    
    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next',
                'current', 'np', 'volume', 'start_time', 'loop', 'delta_time', 'song_embed')
    
    def __init__(self, ctx):
        self._channel = ctx.channel
        self._cog = ctx.cog
        self.current = None
        self.bot = ctx.bot
        self._guild = ctx.guild
        self.loop = False
        self.next = asyncio.Event()
        self.np = None
        self.queue = asyncio.Queue()
        self.song_embed = None
        self.start_time = time.perf_counter()
        self.delta_time = 0.0
        self.volume = .5
        
        ctx.bot.loop.create_task(self.player_loop())
        
    async def timer(self):
        """Keeps track of the song's runtime, and resets the runtime
        when a new song starts.
        """
        self.start_time = time.perf_counter()
        while True:
            await asyncio.sleep(1)
            if self._guild.voice_client.is_playing():
                ## Subtract runtime while paused.
                self.delta_time = time.perf_counter() - self.start_time
                
            ## Reset time once song is finished.
            else:
                break

    async def player_loop(self):
        """The main loop for the media player.
        Runs as long as the bot is in a voice channel."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                ## Wait for the next song.
                ## If it times out (10 min) then disconnect.
                async with timeout(600):
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.destroy(self._guild)

            if not isinstance(source, YTDLSource):
                try:
                    source = await YTDLSource.prepare_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(F"There was an error processing your song.")
                    print(F"Error processing song {e}")
                    continue
            
            ## Set volume and play the song.
            source.volume = self.volume
            self.current = source
            self._guild.voice_client.play(source, after=lambda song: self.bot.loop.call_soon_threadsafe(self.next.set))
        
            ## Get the url for the video thumbnail.
            video_id = source.web_url.split("=", 1)[1]
            thumbnail = F"https://i1.ytimg.com/vi/{video_id}/hqdefault.jpg"
            ## Split the duration into hours/minutes/seconds.
            time_delta = str(datetime.timedelta(seconds=source.duration))
            timestamp = datetime.datetime.today().strftime('%H:%M %p')
            
            ## Now playing embed. Sent whenever a new song starts playing.
            field = (F"\n**Requested by {(str(source.requester.mention))}** | **Duration**: `{time_delta}`")
            new_song_embed = discord.Embed(
                title="**Now Playing**",
                url=source.web_url,
                description=(F"{source.title}\n{field}"),
                color=0xa84300
                )
            
            new_song_embed.set_footer(text=(F"Today at {timestamp}\t\t\t\t\t\t\t\t\t\tVolume: {source.volume * 100}%"))
            new_song_embed.set_thumbnail(url=thumbnail)
            self.song_embed = await self._channel.send(embed=new_song_embed)
    
            ## Count the runtime of the song, in case now_playing() is called.
            await self.timer()
            await self.next.wait()
            ## Clean up FFMPEG.
            source.cleanup()
            self.current = None
            
            try:
                await self.song_embed.delete()
                if (self.np is not None) and (self.queue.empty()):
                    await self.np.delete()
            except discord.HTTPException:
                pass

    def destroy(self, guild):
        """Disconnects and cleans the player.
        Useful if there is a timeout, or if the bot is no longer playing.
        """
        return self.bot.loop.create_task(self._cog.cleanup(guild))


class Music(commands.Cog):
    """Music related commands."""

    __slots__ = ('bot', 'players')

    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    async def cleanup(self, guild, ctx):
        """Cleans up the bot's player and the FFMPEG client."""
        player = self.get_player(ctx)
        player.loop = False
        player.queue._queue = []
        
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass
        
        try:
            del self.players[guild.id]
        except KeyError:
            pass
        
    def in_channel(self, ctx):
        """Checks if the message author is in the bot's voice channel."""
        if ctx.voice_client:
            return True
        return False

    def get_channel(self, ctx):
        """Checks if the bot is connected to a voice channel.
        
        @return:
            True if connected to a channel, False if not.
        """
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return False
        return True

    def get_player(self, ctx):
        """Retrieves the player for a guild, or generate a new one."""
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player
    
    def reset_np(self, ctx):
        pass
    
    @commands.command(name='join', aliases=['connect'])
    async def connect_(self, ctx, *, channel: discord.VoiceChannel=None):
        """Connects the bot to a voice channel, or switches voice channels.
        
        @param:
            channel (discord.VoiceChannel): The channel to connect to. 
            If not provided then attempts to connect to the author's channel.
        """
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                raise InvalidVoiceChannel("No channel to join. Please either specify a valid channel or join one.")

        vc = ctx.voice_client
        if vc:
            if vc.channel.id == channel.id:
                return
            try:
                await vc.move_to(channel)
            except asyncio.TimeoutError:
                raise VoiceConnectionError(F"Moving to channel: <{channel}> timed out.")
            
        ## If channel is not provided, connect to the author's current channel.
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                raise VoiceConnectionError(F"Connecting to channel: <{channel}> timed out.")
    
    @commands.command(name='loop')
    async def loop_(self, ctx):
        """Loops after the current song is complete.
        If the player was looping and is called again, stops looping."""
        vc = ctx.voice_client
        source = vc.source
        player = self.get_player(ctx)
        player.loop = not player.loop
        
        await ctx.send(F"{'Now looping' if player.loop else 'Stopped looping'}")
        
        while player.loop:
            try:
                if source not in player.queue._queue:
                    await self.play_(ctx=ctx, song_search=source.title)
                    await asyncio.sleep(source.duration)
            except:
                await asyncio.sleep(1)
            
    @commands.command(name='lyrics', aliases=['lyric'])
    async def lyrics_(self, ctx, *, name: typing.Optional[str]):
        """Gets the lyrics for a song.
        
        @param:
            name (str): The name of a song to get lyrics for.
            If not provided then tries to get lyrics for the currently playing song.
        """
        vc = ctx.voice_client
        name = name or vc.source.title
        
        async with ctx.typing():
            async with aiohttp.request("GET", LYRICS_URL + name, headers={}) as response:
                if not 200 <= response.status <= 299:
                    print("No lyrics found.")
                    
                data = await response.json()
                try:
                    if len(data['lyrics']) > 2000:
                        await ctx.send(F"<{data['links']['genius']}>")
                except KeyError:
                    return await ctx.send("Couldn't find the lyrics for this song.")
                    
                lyrics_embed = discord.Embed(
                    title=data["title"],
                    description=data["lyrics"],
                    color=0xa84300
                    )
                
                lyrics_embed.set_thumbnail(url=data['thumbnail']['genius'])
                lyrics_embed.set_author(name=F"{data['author']}")
                await ctx.send(embed=lyrics_embed)
                
                
    @commands.command(name='delete')
    async def delete_song_(self, ctx, *, name):
        pass
        await ctx.send(F"Deleted {name} from the queue.", delete_after=15)
            
    @commands.command(name='play')
    async def play_(self, ctx, *, song_search: str):
        """Requests a song and adds it to the queue.
        
        If the bot is not already in a voice channel, it will attempt to join the channel of the user who 
        requested the song.

        @param:
            song_search [str]: The song to search for, can be a URL or a title.
            If the given query is a playlist, then all songs in the playlist
            will be added to the queue.
        """ 
        await ctx.trigger_typing()
        vc = ctx.voice_client
        if not vc:
            await ctx.invoke(self.connect_)
            
        player = self.get_player(ctx)
        if "playlist?list=" in song_search:
            playlist = pytube.Playlist(song_search)
            
            for link in playlist.video_urls:
                source = await YTDLSource.get_source_playlist(
                    ctx, link, loop=self.bot.loop, download=False)
                
                await player.queue.put(source)
            
            await ctx.send(F"Added {len(playlist)} videos from **{playlist.title}** to the queue.", delete_after=15)
        else:
            source = await YTDLSource.get_source_song(
                ctx, song_search, repeat=player.loop, loop=self.bot.loop, download=False
                )
            
            await player.queue.put(source)
        
    @commands.command(name='np')
    async def now_playing(self, ctx):
        """Gets the currently playing song and its timestamp."""
        vc: discord.voice_client.VoiceClient = ctx.voice_client
        if not vc and not vc.source:
            return await ctx.send("I am not currently playing anything!", delete_after=10)

        source = vc.source        
        ## Get the video length and elapsed time.
        vid_length = datetime.timedelta(seconds=source.duration)
        vid_time = vid_length.total_seconds()
        player = self.get_player(ctx)
        ## Get the video thumbnail. Uses high-quality.
        video_id = source.web_url.split("=", 1)[1]
        thumbnail = F"https://i1.ytimg.com/vi/{video_id}/hqdefault.jpg"
        
        progress_bar = ProgressBar(vid_time)
        elapsed = round(player.delta_time)
        current_progress = progress_bar.get_progress(elapsed)
        
        ## Create the now-playing embed.
        field = (F"\n**Requested by {(str(source.requester.mention))}** | **Duration**: `{elapsed}`|`{vid_length}` ")
        np_embed = discord.Embed(
            title="**Now Playing**", url=source.web_url,
            description=(F"{source.title}\n\n{current_progress}\n{field}"),
            color=0xa84300
            )
        
        np_embed.set_footer(text=F"Volume: {source.volume * 100}%")
        np_embed.set_thumbnail(url=thumbnail)
        player.np = await ctx.send(embed=np_embed)

        paused_time = 0

        while vc.source is not None:
            if not vc.is_playing():
                paused_time += 1
                await asyncio.sleep(1)
                continue
            
            ## Update the elapsed time and progress bar.
            elapsed = round(player.delta_time - paused_time)
            elapsed_field = time.strftime('%H:%M:%S', time.gmtime(elapsed))
            current_progress = progress_bar.get_progress(elapsed)
            print(elapsed)
            ## Update the now-playing embed.
            field = (F"\n**Requested by {(str(source.requester.mention))}** | **Duration**: `{elapsed_field}`|`{vid_length}` ")
            np_embed = discord.Embed(
                title="**Now Playing**",
                url=source.web_url,
                description=(F"{source.title}\n\n{current_progress}\n{field}"),
                color=0xa84300
                )
            
            np_embed.set_footer(text=(F"Volume: {source.volume * 100}%"))
            np_embed.set_thumbnail(url=thumbnail)
            
            try:
                await player.np.edit(embed=np_embed)
            except:
                pass
            
            vc = ctx.voice_client
            
            await asyncio.sleep(1)
    
    @commands.command(name='pause')
    async def pause_(self, ctx):
        """Pauses the currently playing song.
        If the song is already paused then resumes.
        """
        vc = ctx.voice_client
        if not vc:
            return await ctx.send("I am not currently playing anything!", delete_after=10)
        elif vc.is_paused():
            vc.resume()
            return await ctx.send(F"**`{ctx.author}`** resumed the song!", delete_after=10)

        vc.pause()
        return await ctx.send(F"**`{ctx.author}`** Paused the song!", delete_after=10)

    @commands.command(name='queue', aliases=['q', 'playlist'])
    async def get_queue(self, ctx):
        """Gets up to seven upcoming songs."""
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("I am not currently connected to voice!", delete_after=10)

        player = self.get_player(ctx)
        if player.queue.empty():
            return await ctx.send("There are no more queued songs.")

        upcoming = list(itertools.islice(player.queue._queue, 0, 10))
        song_names = '\n'.join(F"**{song['title']}** | `{datetime.timedelta(seconds=song['duration'])}`" for song in upcoming)
        queue_embed = discord.Embed(
            title=F"Upcoming - Next {len(upcoming)}",
            description=song_names,
            color=0x206694
            )
        
        await ctx.send(embed=queue_embed, delete_after=15)
        
    @commands.command(name='removesong', aliases=['r'])
    async def remove_song(self, ctx, *, spot: int):
        """Removes a song at the given spot in the queue.
        
        @param:
            spot (int): The index to remove a video from.
        """
        player = self.get_player(ctx)
        songs_queue = player.queue._queue
        try:
            song_title = songs_queue[spot - 1]['title']
            del songs_queue[spot - 1]
        except IndexError:
            return await ctx.send("There is no song at the spot in the queue.")
        
        await ctx.send(F"Removed `{song_title}` from the queue.")
        
    @commands.command(name='shuffle')
    async def shuffle_(self, ctx):
        """Shuffles the queue."""
        player = self.get_player(ctx)
        songs = player.queue._queue
        shuffle(songs)
        await ctx.send("Shuffled the queue.", delete_after=10)
        
    @commands.command(name='skip')
    async def skip_(self, ctx):
        """Skips the currently playing song."""
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("I am not currently playing anything!", delete_after=10)
        
        elif not vc.is_playing():
            return

        vc.stop()
        await ctx.send(F"**`{ctx.author}`**: Skipped the song!", delete_after=10)
        
    @commands.command(name='stop')
    async def stop_(self, ctx):
        """Stops the currently playing song and destroy the player."""
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("I am not currently playing anything!", delete_after=10)

        ## Call cleanup and get rid of the player
        await self.cleanup(ctx.guild, ctx)
        
    @commands.command(name='volume', aliases=['vol'])
    async def change_volume(self, ctx, *, vol: int):
        """Changes the player volume.
        @param:
            vol [int]: Set volume as a percentage.
            Only accepts ints between 0 and 101.
        """
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("I am not currently connected to voice!", delete_after=10)
        ## Given volume is outside the range.
        elif not 1 <= vol <= 100:
            return await ctx.send("Please enter a value between 0 and 101.", delete_after=10)
        elif vc.source:
            vc.source.volume = vol / 100
        
        ## Set the volume.
        player = self.get_player(ctx)
        player.volume = vol / 100
        await ctx.send(F"**`{ctx.author}`** set the volume to **{vol}%**", delete_after=10)


## Adds cog to the bot
def setup(bot):
    bot.add_cog(Music(bot))
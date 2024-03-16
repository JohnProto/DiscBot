#test
import discord
from discord import FFmpegPCMAudio
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
client = discord.Client(intents=intents)

try:
    with open('counter.txt', 'r') as file:
        nerd_counter = int(file.read())
except FileNotFoundError:
    nerd_counter = 0

try:
    with open('token.txt', 'r') as file:
        token = file.read().strip()
except FileNotFoundError:
    print("Token file not found!")
    exit()

voice_client = None

@client.event 
async def on_ready():
    print("Ready!")
    print(f'Logged in as {client.user}')
    await client.change_presence(activity=discord.Game(name="CSD Simulator"))

@client.event
async def on_message(message):
    global nerd_counter
    global voice_client

    if message.author == client.user:
        return
    
    if '💀' in message.content:
        gif_url = 'https://media1.tenor.com/m/tNfzy9M48V8AAAAd/skull-issues.gif'
        await message.channel.send(gif_url)
    
    if '🗿' in message.content:
        await message.channel.send('🗿')

    if 'nerd' in message.content.lower() or 'actually' in message.content.lower() or '🤓' in message.content:
        gif_url = 'https://tenor.com/view/nerd-emoji-nerd-emoji-avalon-play-avalon-gif-24241051'
        nerd_counter += 1
        await message.channel.send(f'{gif_url}\nNerd counter: {nerd_counter}')

        with open('counter.txt', 'w') as file:
            file.write(str(nerd_counter))

    if 'gtfi' in message.content.lower() and client.user in message.mentions:
        audio_source = FFmpegPCMAudio('Erika.mp3')
        if message.guild and message.author.voice and message.author.voice.channel:
            voice_channel = message.author.voice.channel
            if voice_channel:
                if not voice_client:
                    voice_client = await voice_channel.connect()
                    await play_audio_with_delay(audio_source, 1)
                    await message.channel.send(f"Joined {voice_channel.name}")
                else:
                    if voice_client.is_connected():
                        await message.channel.send("Already in a voice channel")
                    else:
                        voice_client = await voice_channel.connect()
                        await play_audio_with_delay(audio_source, 1)
                        await message.channel.send(f"Rejoined {voice_channel.name}")
        else:
            await message.channel.send("You need to be in a voice channel to use this command")

    if 'gtfo' in message.content.lower() and client.user in message.mentions:
        audio_source = FFmpegPCMAudio('abuenoAdiosMaster.mp3')
        if voice_client and voice_client.is_connected():
            await play_audio_with_delay(audio_source, 0)
            await asyncio.sleep(4)
            await voice_client.disconnect()
            voice_client = None
            await message.channel.send("Disconnected from voice channel")


async def play_audio_with_delay(audio_source, delay):
    await asyncio.sleep(delay)
    voice_client.play(audio_source)

@client.event
async def on_voice_state_update(member, before, after):
    global voice_client

    guild = member.guild
    target_channel_id = 1182016043628105811
    voice_channel = guild.get_channel(target_channel_id)    
    audio_source = FFmpegPCMAudio('Erika.mp3')

    bot_voice = client.voice_clients
    if (before.channel and before.channel.id == target_channel_id and after.channel == None) or (after.channel and after.channel.id == target_channel_id):
        if voice_channel and member.id != client.user.id and not after.self_stream and not before.self_stream:
            if len(voice_channel.members) > 0 and not bot_voice:   
                voice_client = await voice_channel.connect()
                await play_audio_with_delay(audio_source, 1)
                print(f"Bot joined {voice_channel.name}")
            elif len(voice_channel.members) > 1 and bot_voice:
                if not before.channel and after.channel and bot_voice:
                    if member.id == 361434482735054850:
                        audio_source = FFmpegPCMAudio('forgor.mp3')
                    await play_audio_with_delay(audio_source, 1.3)
            elif len(voice_channel.members) == 1 and bot_voice:
                await bot_voice[0].disconnect()
                print(f"bot left {voice_channel.name}")

client.run(token)

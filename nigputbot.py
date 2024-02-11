import discord
#Mia Malakia Kserw Egw Na Doume Ti Tha Ginei Gia Ta Memes
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

@client.event
async def on_message(message):
    global nerd_counter

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

    target_user_id = 361434482735054850
    for user in message.mentions:
        if user.id == target_user_id:
            target_user = user
            await message.channel.send(f'{target_user.mention} :foot:')
            break

    target_user_id = 949241373922570240
    if message.author.id == target_user_id:
        await message.channel.send(f'stfu im better')

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
        if voice_channel and member.id != client.user.id:
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

client.run('token')

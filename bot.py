import os
import time 
import asyncio
import json
import requests
from dotenv import load_dotenv
import discord
from discord.ext import commands
import re
from discord import app_commands

load_dotenv()

channels = []
huggingface_token = os.getenv('HUGGINGFACE_TOKEN')
API_URL = 'https://api-inference.huggingface.co/models/Ninja5000/DialoGPT-medium-TWEWYJoshua'
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="joshua!", intents=intents)
cooldown = {}

def EmbedBuilder(type: str, title: str, description: str, fields={}, footer=""):
    embed = discord.Embed()
    embed.title = title
    embed.description = description
    if type == "error":
        embed.color = discord.Color.red()
    elif type == "info":
        embed.color = discord.Color.blurple()
    else:
        raise ValueError("type must be either \"info\" or \"error\"")
    if footer != "":
        embed.set_footer(text=footer)
    if fields != None:
        for field in fields:
            embed.add_field(value = fields[index(field)]["value"], name = fields[index(field)]["name"], inline = fields[index(field)]["inline"])
    return embed

def LoadChannels():
    global channels
    try:
        with open("channels.json", "r") as f:
            channels = json.load(f)
    except:
        pass

def UpdateChannels():
    global channels
    try:
        with open("channels.json", "w") as f:
            json.dump(channels, f)
    except:
        pass

def query(prompt, waitformodel=False):
    """
    Get the response from the Hugging Face API
    """

    payload = {'inputs': f'You say: {prompt}\nI reply:'}
    backoff = 3
    if not waitformodel:
        for i in range(3):
            response = requests.post(
                API_URL, 
                headers = {
                    'Authorization': f'Bearer {huggingface_token}',
                    "x-use-cache": "false"
                },
                json = payload
            )
            if response.status_code == 429:
                print("Error 429 received. Backing off...")
                time.sleep(backoff)
                backoff *= 2
            else:
                return response
    else:
        for i in range(3):
            response = requests.post(
                API_URL, 
                headers = {
                    'Authorization': f'Bearer {huggingface_token}',
                    "x-use-cache": "false",
                    "x-wait-for-model": "true"
                },
                json = payload
            )
            if response.status_code == 429:
                print("Error 429 received. Backing off...")
                time.sleep(backoff)
                backoff *= 2
            else:
                return response
    return f"ERROR"

@bot.event
async def on_ready():
    LoadChannels()
    await bot.tree.sync()
    print("Logged in and synced commands.")


@bot.hybrid_command(name = "setup", description = "Set the channel for Joshua")
@commands.has_permissions(administrator=True)
async def setup(ctx):
    message = await ctx.reply(
        embed=EmbedBuilder(
            type="info", 
            title="⏳ Setting channel...", 
            description="Please wait while the channel is being set", 
            fields=None
        )
    )
    try:
        channels.append(str(ctx.channel.id))
        UpdateChannels()
        await message.edit(
            embed=EmbedBuilder(
                type="info", 
                title="✅ Channel successfully set!", 
                description="", fields=None
            )
        )
    except:
        await message.edit(
            embed=EmbedBuilder(
                type="error", 
                title="❌ Channel couldn't be set.", 
                description="Please contact **user0_07161**", 
                fields=None
            )
        )

@bot.hybrid_command(name = "unset", description = "Unset the channel for Joshua")
@commands.has_permissions(administrator=True)
async def unset(ctx):
    message = await ctx.reply(
        embed=EmbedBuilder(
            type="info", 
            title="⏳ Unsetting channel...", 
            description="Please wait while the channel is being set", 
            fields=None
        )
    )
    try:
        channels.remove(str(ctx.channel.id))
        UpdateChannels()
        await message.edit(
            embed=EmbedBuilder(
                type="info", 
                title="✅ Channel successfully unset!", 
                description="", 
                fields=None
            )
        )
    except:
        await message.edit(
            embed=EmbedBuilder(
                type="error", 
                title="❌ Channel couldn't be unset.", 
                description="Make sure the channel was set before or contact **user0_07161**", 
                fields=None
            )
        )

@bot.event
async def on_message(message):
    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return
    if (not bot.user.mentioned_in(message) and 
        not str(message.channel.id) in channels and 
        not ("@everyone" in message.mentions or 
            "@here" in message.mentions) and not 
        isinstance(message.channel, discord.channel.DMChannel) or
        message.author.bot
    ):
        return
    try:
        if time.time() - cooldown[message.author.id] < 2:
            await message.reply(
                embed=EmbedBuilder(
                    type="info", 
                    title="❄️ Cooldown", 
                    description=f"-# Please wait `{int(2-(time.time()-cooldown[message.author.id]))}` seconds for the cooldown to finish.",
                    fields=None
                )
            )
            return
        else:
            cooldown[message.author.id] = time.time()
    except:
        cooldown[message.author.id] = time.time()
    for match in re.findall(r'<@?!?(\d{11,})>', message.content):
        user = await bot.fetch_user(int(match))
        if user:
            message.content = message.content.replace(f'<@{match}>', f'@{user.name}')
    async with message.channel.typing():
        response = query(message.content)
        if "str" in str(type(response)):
            error = response.split("-")[-1]
            await message.reply(
                embed=EmbedBuilder(
                    type="error",
                    title="❗ Error",
                    description=f"An error occured.\nPlease contact **user0_07161**, if this error persists.",
                    fields=None
                )
            )
            return
        elif response.status_code == 503:
            msg = await message.reply(
                embed=EmbedBuilder(
                    type="info",
                    title="⌛ Model loading",
                    description=f"The model is currently loading...\nPlease wait...",
                    fields=None,
                    footer="The message will be updated once the model finished loading."
                )
            )
            async with message.channel.typing():
                response = query(message.content, waitformodel=True)
            if response.status_code != 200:
                await msg.edit(
                    embed=EmbedBuilder(
                        type="error",
                        title="❗ Error",
                        description=f"An error occured.\nStatus code: {response.status_code}.\nPlease contact **user0_07161**, if this error persists.",
                        fields=None
                    ),
                    suppress=True
                )
                return
            else:
                if len(list(response.json()[0]['generated_text'].split("I reply:")[-1])) == 1:
                    await msg.edit(
                        content=f":{response.json()[0]['generated_text'].split('I reply:')[-1]}",
                        suppress=True
                    )
                else:
                    await msg.edit(
                        content=response.json()[0]['generated_text'].split("I reply:")[-1],
                        suppress=True
                    )
                return
        elif response.status_code != 200:
            await message.reply(
                embed=EmbedBuilder(
                    type="error",
                    title="❗ Error",
                    description=f"An error occured.\nStatus code: {response.status_code}.\nPlease contact **user0_07161**, if this error persists.",
                    fields=None
                )
            )
            return
        else:
            try:
                if len(list(response.json()[0]['generated_text'].split("I reply:")[-1])) == 1:
                    await message.reply(
                        content=f":{response.json()[0]['generated_text'].split('I reply:')[-1]}"
                    )
                else:
                    await message.reply(
                        content=response.json()[0]['generated_text'].split("I reply:")[-1]
                    )
                return
            except discord.errors.HTTPException:
                await message.reply(
                    embed=EmbedBuilder(
                        type="error",
                        title="❗ Error",
                        description=f"An error occured.\nThe model returned empty output.",
                        fields=None
                    )
                )
            return
        await message.reply(
            embed=EmbedBuilder(
                type="error",
                title="❗ Error",
                description=f"An unknown error occured.\nPlease contact **user0_07161**, if this error persists.",
                fields=None
            )
        )

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="generate", description="Generate a response...")  
async def generate(interaction, prompt: str):
    await interaction.response.defer()
    response = query(prompt)
    if "str" in str(type(response)):
        error = response.split("-")[-1]
        await interaction.edit_original_response(
            embed=EmbedBuilder(
                type="error",
                title="❗ Error",
                description=f"An error occured.\nPlease contact **user0_07161**, if this error persists.",
                fields=None
            )
        )
        return
    elif response.status_code == 503:
        msg = await interaction.edit_original_response(
            embed=EmbedBuilder(
                type="info",
                title="⌛ Model loading",
                description=f"The model is currently loading...\nPlease wait...",
                fields=None,
                footer="The message will be updated once the model finished loading."
            )
        )
        response = query(prompt=prompt, waitformodel=True)
        if response.status_code != 200:
            await msg.edit(
                embed=EmbedBuilder(
                    type="error",
                    title="❗ Error",
                    description=f"An error occured.\nStatus code: {response.status_code}.\nPlease contact **user0_07161**, if this error persists.",
                    fields=None
                ),
            )
            return
        else:
            if len(list(response.json()[0]['generated_text'].split("I reply:")[-1])) == 1:
                await msg.edit(
                    content=f":{response.json()[0]['generated_text'].split('I reply:')[-1]}",
                    embed = None
                )
            else:
                await msg.edit(
                    content=response.json()[0]['generated_text'].split("I reply:")[-1],
                    embed = None
                )
            return
    elif response.status_code != 200:
        await interaction.edit_original_response(
            embed=EmbedBuilder(
                type="error",
                title="❗ Error",
                description=f"An error occured.\nStatus code: {response.status_code}.\nPlease contact **user0_07161**, if this error persists.",
                fields=None
            )
        )
        return
    else:
        try:
            if len(list(response.json()[0]['generated_text'].split("I reply:")[-1])) == 1:
                await interaction.edit_original_response(
                    content=f":{response.json()[0]['generated_text'].split('I reply:')[-1]}"
                )
            else:
                await interaction.edit_original_response(
                    content=response.json()[0]['generated_text'].split("I reply:")[-1]
                )
        except discord.errors.HTTPException:
            await interaction.edit_original_response(
                embed=EmbedBuilder(
                    type="error",
                    title="❗ Error",
                    description=f"An error occured.\nThe model returned empty output.",
                    fields=None
                )
            )
        return
    await interaction.edit_original_response(
        embed=EmbedBuilder(
            type="error",
            title="❗ Error",
            description=f"An unknown error occured.\nPlease contact **user0_07161**, if this error persists.",
            fields=None
        )
    )

bot.run(os.getenv('DISCORD_TOKEN'))

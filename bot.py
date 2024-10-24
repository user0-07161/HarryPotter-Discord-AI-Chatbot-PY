import os
import time 
import asyncio
import json
import requests
from dotenv import load_dotenv
import discord
from discord.ext import commands
import logging
import random
import re
logger = logging.getLogger('discord') # set up the logger

load_dotenv()

# Hugging Face API endpoint
API_URL = 'https://api-inference.huggingface.co/models/Ninja5000/DialoGPT-medium-TWEWYJoshua'
# API_URL = 'https://api-inference.huggingface.co/models/KaydenSou/Joshua' # many diff responses
# API_URL = 'https://api-inference.huggingface.co/models/nabarun/DialoGPT-small-joshua' # kinda like og josh, but more out of context
# API_URL = 'https://api-inference.huggingface.co/models/'

# discord intents
intents = discord.Intents.default()
intents.message_content = True

# set up the bot
class MyBot(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_endpoint = API_URL
        self.last_message_time = {}
        huggingface_token = os.getenv('HUGGINGFACE_TOKEN') # Make sure to set this in your .env file
        self.request_headers = {
            'Authorization': 'Bearer {}'.format(huggingface_token),
            "x-use-cache": "false"
        }
    
bot = MyBot(command_prefix="joshua!", intents=intents, owner_id=707170199861854209) # replace with your discord id

def query(payload):
    """
    make request to the Hugging Face model API with exponential backoff retry strategy
    """
    # logger.debug(payload)
    
    retries = 3
    backoff_time = 2  # initial backoff time
    for _ in range(retries):
        response = requests.post(bot.api_endpoint,
                                    headers=bot.request_headers,
                                    json=payload)
        if response.status_code == 429:
            logger.warning("Received 429 error, backing off for {} seconds".format(backoff_time))
            time.sleep(backoff_time)
            backoff_time *= 2  # exponential backoff
        else:
            logger.debug(response)
            return response
    return None  # if all retries fail

@bot.event
async def on_ready():
    # logging info when the bot wakes up 
    logger.info('Logged in as')
    logger.info(bot.user.name)
    logger.info(bot.user.id)
    logger.info(f'Connected to {len(bot.guilds)} guilds')
    logger.info('------')
    # send a request to the model without caring about the response
    # just so that the model wakes up and starts loading
    # query({'inputs': 'Hello!'})
    await keep_alive()

# Make a request to the model every 10 minutes to keep it alive
async def keep_alive():
    while True:
        # various inputs so model loads and doesn't cache response
        inputs = ["Hello!", "cheesecake macaroni", "potatoes", "lalala", "jajaja", "brr", "mbmb", "abcd", "xyz"]
        # send a request to the model without caring about the response
        query({'inputs': random.choice(inputs)})
        logger.info('Sent keep-alive request to the model')
        await asyncio.sleep(60 * 10)

@bot.event
async def on_message(message):
    """
    this function is called whenever the bot sees a message in a channel
    """

    # ignore the message if it comes from the bot itself or a direct message
    if message.author.id == bot.user.id or isinstance(
            message.channel, discord.DMChannel):
        return
    if message.author.bot:
        return
    if (message.channel.id not in [946035894601797643, 1296840483229798460, 1297140878917242921, 1296154358832041995, 1297963659691298917]) \
        and not (bot.user.mentioned_in(message) and not (["@everyone", "@here"] in message.mentions)):
        return

    for match in re.findall(r'<@?!?(\d{11,})>', message.content):
        user = await bot.fetch_user(int(match))
        if user:
            message.content = message.content.replace(f'<@{match}>', f'@{user.name}')

    logger.info(f"Received message from {message.author.name} [{message.author.id}] in {message.guild.name}: {message.content}")

    if message.author.id in bot.last_message_time:
        if time.time() - bot.last_message_time[message.author.id] < 3:
            remaining_time = round(3 - (time.time() - bot.last_message_time[message.author.id]))
            await message.reply(f"Please wait for {remaining_time} seconds for the cooldown to finish.", mention_author=False)
            return
    bot.last_message_time[message.author.id] = time.time()

    # form query payload with the content of the message
    payload = {'inputs': f'You say: {message.content}\nI reply:'}

    # while the bot is waiting on a response from the model
    # set the its status as typing for user-friendliness
    async with message.channel.typing():
        max_retries = 3
        for i in range(max_retries):
            logger.info(f"Try {str(i + 1)} of {str(max_retries)}")
            response = query(payload)
            if response.status_code != 200:
                if "[503]" in str(response):
                    logger.error(f"Error [503]: {response.text}")
                    bot_response = f'`Model Ninja5000/DialoGPT-medium-TWEWYJoshua is currently loading`'
                else:
                    logger.error(f"Error occurred: {response.text}")
                    bot_response = '`Hmm... something is not right.`'
                continue
            else:
                response_data = response.json()
                bot_response = response_data[0]['generated_text']
                # remove the prompt from the bot's response
                bot_response = bot_response[len(payload['inputs']):]
                if len(bot_response.strip()) > 1:
                    break


    # we may get ill-formed response if the model hasn't fully loaded
    # or has timed out
    if not bot_response:
        if 'error' in response or 'error' in response.text:
            logger.error(f'`Unkown error: [{response.status_code}] {response.text}`')
            bot_response = 'An unkown error occured.'
        else:
            logger.error(f"Error occurred: [{response.status_code}] {response.text}")
            bot_response = '`No response from the model due to unknown reasons.`'

    await message.reply(bot_response.strip(), mention_author=False)
    logger.info(f"Sent message in {message.guild.name} [{message.guild.id}]: {bot_response.strip()}\n")

bot.run(os.getenv('DISCORD_TOKEN'))

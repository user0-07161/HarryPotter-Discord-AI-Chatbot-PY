# the os module helps us access environment variables
# i.e., our API keys
import os
import time  # cooldown

# to keep the repl online
from keep_alive import keep_alive

# these modules are for querying the Hugging Face model
import json
import requests

# the Discord Python API
import discord
# discord text sanitiser
#import discordtextsanitizer as dts

# this is my Hugging Face profile link
API_URL = 'https://api-inference.huggingface.co/models/Ninja5000/'

class MyClient(discord.Client):
    def __init__(self, model_name):
        super().__init__()
        self.api_endpoint = API_URL + model_name
        # retrieve the secret API token from the system environment
        huggingface_token = os.environ['HUGGINGFACE_TOKEN']
        # format the header in our request to Hugging Face
        self.request_headers = {
            'Authorization': 'Bearer {}'.format(huggingface_token)
        }

    def query(self, payload):
      """
      make request to the Hugging Face model API with exponential backoff retry strategy
      """
      data = json.dumps(payload)
      retries = 3
      backoff_time = 2  # initial backoff time
      for _ in range(retries):
        response = requests.post(self.api_endpoint, headers=self.request_headers, data=data)
        if response.status_code == 429:
            print("Received 429 error, backing off for {} seconds".format(backoff_time))
            time.sleep(backoff_time)
            backoff_time *= 2  # exponential backoff
        else:
            return json.loads(response.content.decode('utf-8'))
      return None  # if all retries fail


    async def on_ready(self):
        # print out information when the bot wakes up
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')
        # send a request to the model without caring about the response
        # just so that the model wakes up and starts loading
        self.query({'inputs': {'text': 'Hello!'}})

    async def on_message(self, message):
        """
        this function is called whenever the bot sees a message in a channel
        """
        # ignore the message if it comes from the bot itself
        if message.author.id == self.user.id:
            return

        # form query payload with the content of the message
        payload = {'inputs': {'text': message.content}}

        # while the bot is waiting on a response from the model
        # set the its status as typing for user-friendliness
        async with message.channel.typing():
          response = self.query(payload)
        bot_response = response.get('generated_text', None)
        
        # we may get ill-formed response if the model hasn't fully loaded
        # or has timed out
        if not bot_response:
            if 'error' in response:
                bot_response = '`Error: {}`'.format(response['error'])
            else:
                bot_response = 'Hmm... something is not right.'

        # send the model's response to the Discord channel
        await message.channel.send(bot_response)

def main():
    
    client = MyClient('DialoGPT-medium-TWEWYJoshua')
    client.run(os.environ['DISCORD_TOKEN'])

if __name__ == '__main__':
  keep_alive()
  main()


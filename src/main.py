import discord
from time import time
import asyncio
import traceback
import sys

import commands
import configuration
import util
import database_handle
import logger


class DOCBotClient(discord.Client):
    
    DEBUG_SPY_MODE = False
    
    async def on_ready(self) -> None:
        """Runs when the bot is operational"""
        print('DaysOfCodingBot is ready')


    async def on_error(self, event_method, *args, **kwargs) -> None:
        try:
            print(f'Ignoring exception in {event_method}', file=sys.stderr)
            error = traceback.format_exc()
            print(error)
            await logger.log_error(error, self)
        except Exception as e:
            print("Caught error in on_error:", e)

       
    async def on_message(self, message) -> None:
        """Runs every time the bot notices a message being sent anywhere."""
        
        if self.DEBUG_SPY_MODE:
            print(message.content)

        # Ignore bot accounts
        if message.author.bot:
            return

        # Ignore messages in DMs
        if type(message.channel) != discord.channel.TextChannel:
            return

        # COMMANDS: Check if it has our command prefix, or starts with a mention of our bot
        command_text = ''
        # Find the command_text from stripping a command prefix
        for prefix in (configuration.PREFIX, self.user.mention, f"<@!{self.user.id}>"):
            if message.content.startswith(prefix):
                command_text = message.content[len(prefix):].lstrip()
                break

        # If there was a command prefix and command text found...
        if command_text != '':

            # Split the command into 2 parts, command name and parameters
            split_command_text = command_text.split(maxsplit=1)

            command_name = split_command_text[0].lower()

            if len(split_command_text) == 2:
                # Theres 2 elements, so there must be a name and parameters
                parameters = split_command_text[1]
                # Remove trailing whitespaces
                parameters = parameters.strip()
            else:
                # No paramaters specified
                parameters = ""

            try:
                # Get the command's function
                command_function = commands.command_aliases_dict[command_name]
            except KeyError:
                # There must not be a command by that name.
                return

            # We got the command's function!

            requirements = command_function.command_data.get(
                "role_requirements")

            # Do role checks
            if requirements:
                # its not an @everyone command..
                if not requirements.intersection([role.id for role in message.author.roles]):
                    # User does not have permissions to execute that command.
                    roles_string = " or ".join([f"`{message.guild.get_role(role_id).name}`" for role_id in
                                                command_function.command_data['role_requirements'] if
                                                message.guild.get_role(role_id) != None])
                    error_message = await message.channel.send(f"You don't have permission to do that! You need {roles_string}.")
                    await asyncio.sleep(configuration.DELETE_ERROR_MESSAGE_TIME)
                    await error_message.delete()
                    return

            # Run the found function
            try:
                await command_function(message, parameters, self)

            except commands.CommandSyntaxError as err:
                # If the command raised CommandSyntaxError, send some information to the user:
                error_details = f": {str(err)}\n" if str(
                    err) != "" else ". "  # Get details from the exception, and format it
                # Get command syntax from the function
                error_syntax = command_function.command_data['syntax']
                # Put it all together
                error_text = f"Invalid syntax{error_details}Usage: `{error_syntax}`"
                error_message = await message.channel.send(error_text)
                await asyncio.sleep(configuration.DELETE_ERROR_MESSAGE_TIME)
                await error_message.delete()


if __name__ == '__main__':
    with open('env/token') as file:
        token = file.read()

    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True
    intents.members = True
    intents.typing = False
    intents.presences = False

    allowed_mentions = discord.AllowedMentions(
        everyone=False,
        roles=False,
        users=True
    )

    client = DOCBotClient(
        intents=intents, allowed_mentions=allowed_mentions)

    client.run(token)

    print('DOCBot Killed')
    database_handle.client.close()

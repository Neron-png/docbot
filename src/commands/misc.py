import discord
import configuration
import util
import asyncio
import time
from commands import Category, CommandSyntaxError, command

# Registers all the commands; takes as a parameter the decorator factory to use.
@command({
    "syntax": "test",
    "aliases": ["twoplustwo"],
    "role_requirements": {configuration.MODERATOR_ROLE},
    "category": Category.OTHER
})
async def test(message: discord.Message, parameters: str, client: discord.Client) -> None:
    """A command named 'test'"""
    result = 2 + 2
    await message.channel.send(f"Two plus two is {result}")

@command({
    "syntax": "submit <code>",
    "category": Category.OTHER,
    "description": "Submits your code for grading"
})
async def submit(message: discord.Message, parameters: str, client: discord.Client) -> None:
    """Relays a submission to the grading channel"""

    attachmens = message.attachments

    # If no attachment is present, return the appropriate error
    if not attachmens:
        raise CommandSyntaxError("You seem to have forgotten to attach a file \nIf you think this is an error, please contact a Moderator")
    
    gradingMessage = f"{message.channel.name} | **{message.channel.topic}** | `{message.channel.id}`\n{attachmens[0].url}"
    await client.get_channel(configuration.SUBMIT_CHANNEL).send(gradingMessage)
    
    
@command({
    "syntax": "hug <target>",
    "allowed_channels": [329226224759209985, 827880703844286475],
    "category": Category.OTHER,
    "description": "Hug someone"
})
async def hug(message: discord.Message, parameters: str, client: discord.Client) -> None:
# Make sure someone was specified
    if parameters == "":
        raise CommandSyntaxError("You must specify someone to hug.")
    # Get users
    hugger = message.author.mention
    target = parameters
    
    if str(message.author.id) in target:
        #reply message should be a pun
        reply = util.choose_random(configuration.STRINGS_PUN).format(hugger=hugger)
    else:
        
        if target.lower() == "me":
            await message.channel.send("Aw, do you need a hug?")
            # Make Modertron hug the user instead
            target = hugger
            hugger = client.user.mention
        
        # Get a random message and fill it in
        choice = util.choose_random(configuration.STRINGS_HUG)
        reply = choice.format(hugger=hugger, target=target)
    # Make a fancy embed so people don't complain about getting pinged twice
    R, G, B = 256 * 256, 256, 1
    embed = discord.Embed(
        description=reply,
    colour=(46*R + 204*G + 113*B)
    )
    # Done
    await message.channel.send(embed=embed)

    if str(client.user.id) in target:
        await message.channel.send('Thanks for hugging me; I love that!')


@command({
    "syntax": "faderolecolour <role> <colour> <duration>",
    "aliases": ["fadecolour"],
    "role_requirements": {configuration.MODERATOR_ROLE},
    "category": Category.OTHER,
    "description": "Fades the colour of a role to an other colour (hex) in a certain time period (h, d or m)"
})
async def faderolecolour(message: discord.Message, parameters: str, client: discord.Client) -> None:
    if len(parameters.split(' ')) != 3:
        await message.channel.send(content="Try `!faderolecolour <role> <colour> <duration>`.")             
        return
    
    guild = client.get_guild(configuration.GUILD_ID)
    
    # Specify which role is requested to be colour-updated
    role_id = (parameters.split(' ')[0]).lstrip("<@&").rstrip(">")
    role = guild.get_role(int(role_id))
    if role is None:
        await message.channel.send(content="I couldn't find the role @" + role_id + "! :tired_face:")
        return
    
    # Specify clearly that colour is in hex form
    new_colour = parameters.split(' ')[1]
    if not util.is_hex(new_colour.lstrip('#')):
        await message.channel.send(content="Hm...:thinking: " + new_colour + " does not look like a colour in hex form!")
        return

    initial_colour = str(role.colour)
    final_colour = str(new_colour)
    
    # Set samples scale and specify samples
    samples = parameters.split(' ')[2]                        
    if isinstance(samples[-1],str):
        if samples[-1] == 'd':  # for days
            samples_scale = 60
            samples = util.is_valid_duration(samples[:-1],24)
        elif samples[-1] == 'h':  # for hours
            samples_scale = 60
            samples = util.is_valid_duration(samples[:-1],1)
        elif samples[-1] == 'm':  # for minutes
            samples_scale = 1
            samples = util.is_valid_duration(samples[:-1],1)
        else:
                samples = None
    else:
        samples = None

    if samples is None:
        await message.channel.send(content="This does not look like a valid period... Try something like 3**d** for days, "\
            + "3**h** for hours or 3**m** for minutes.")
        return 
    
    # Set the gradient and sampling routine
    gradient = util.linear_gradient(initial_colour,final_colour,samples)
    for i in range(0,samples):
        sample_colour = int(str(gradient['hex'][i]).lstrip('#'),16)
        await role.edit(colour=discord.Colour(sample_colour))
        await asyncio.sleep(60*samples_scale)
    else:   # If duration is non-positive, imediatly update colour to the requested one
        sample_colour = int(str(gradient['hex'][-1]).lstrip('#'),16)
        await role.edit(colour=discord.Colour(sample_colour))



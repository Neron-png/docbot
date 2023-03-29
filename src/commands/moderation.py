from ast import literal_eval
import asyncio
import sqlite3
from time import time
import os.path
import discord
import configuration
import util
from commands import Category, CommandSyntaxError, command
import database_handle
import logger

# Registers all the commands; takes as a parameter the decorator factory to use.

@command({
    "syntax": "createTeam <code> <Team name> [<user tag> <user id>]",
    "aliases": ["create"],
    "role_requirements": {configuration.MODERATOR_ROLE},
    "category": Category.MODERATION,
    "description": "Create a team for Days of Coding"
})
async def createTeam(message: discord.Message, parameters: str, client: discord.Client) -> None:
    """Creates a team for days of Coding"""

    print(parameters)
    if len(parameters) not in (4, 6, 8, 10):
        raise CommandSyntaxError("Invalid parameters given. Ex: `create abcde testTeam neron#3610 209403862736437248`")
    
    message.reply("TODO, fallback")
    
    
@command({
    "syntax": "import_teams",
    "aliases": ["import"],
    "role_requirements": {configuration.MODERATOR_ROLE},
    "category": Category.MODERATION,
    "description": "Import teams for Days of coding"
})
async def import_teams(message: discord.Message, parameters: str, client: discord.Client) -> None:
    """Import teams from the sheets"""

    teams = util.getTeams()
    registered_team_codes = []
    category_channel_count = {x: 0 for x in configuration.TEAMS_CATEGORIES} # Counting because discord's limit is 25 channels per category
    
    for channel in message.guild.channels:
        if channel.category and channel.category.id in configuration.TEAMS_CATEGORIES:
                category_channel_count[channel.category.id] += 1
                if str(channel.type) == 'text':
                    registered_team_codes += [channel.topic]
    
    # Adding the team channel
    print(teams)
    for team in teams:
        if team['CODE'] not in registered_team_codes:
            
            # Find empty category
            for category in message.guild.categories:
                if category.id not in configuration.TEAMS_CATEGORIES or category_channel_count[category.id] == 25:
                    continue
                
                team_members = []
                for i in range(1, 5):
                    if team[f'PLAYER #{i} ID']:
                        try:
                            team_members += [ message.guild.get_member(team[f'PLAYER #{i} ID'])]
                        except Exception as e:
                            await message.channel.send(f"Issue with {team[f'PLAYER #{i} ID']}, {team['CODE']}")
                
                overwrites  = {
                     x: discord.PermissionOverwrite(read_messages=True, attach_files=True, read_message_history=True) for x in team_members 
                }
                await category.create_text_channel(name= team['NAME'], topic=team['CODE'], overwrites=overwrites )
                
                break
            
            
    print(category_channel_count)
    print(registered_team_codes)
    


@command({
    "syntax": "set_day <day number>",
    "aliases": ["set"],
    "role_requirements": {configuration.MODERATOR_ROLE},
    "category": Category.MODERATION,
    "description": "Set the day of Days of coding and unlock the relevant stuff"
})
async def set_day(message: discord.Message, parameters: str, client: discord.Client) -> None:
    
    day = parameters[0]
    # get the file to update in the path
    path = os.path.split(os.path.dirname(__file__))
    print(path)
    


@command({
    "syntax": "warns <member>",
    "role_requirements": {configuration.MODERATOR_ROLE},
    "category": Category.MODERATION,
    "description": "List the warns of a user"
})
async def warns(message: discord.Message, parameters: str, client: discord.Client) -> None:
    member = util.get_member_by_id_or_name(message, parameters)

    if member is None:
        user_id = util.try_get_valid_user_id(parameters)
        if not user_id:
            raise CommandSyntaxError("You must specify a valid user!")
    else:
        user_id = member.id

    def warn_embed_generator(page: int, total_pages: int):
        warn_list = database_handle.cursor.execute('''SELECT REASON, TIMESTAMP FROM WARNS WHERE ID = :member_id LIMIT 10 OFFSET :offset''',
                                                   {'member_id': user_id, "offset": page * 10}).fetchall()

        warn_text = timestamp_text = ''

        for warn in warn_list:
            warn_text += f"{warn[0]}\n"
            timestamp_text += f"<t:{warn[1]}:d> <t:{warn[1]}:T>\n"

        return discord.Embed(title=f"Warns. Total of {total_warns}", description=f"<@{user_id}>") \
            .add_field(name="Reason", value=warn_text) \
            .add_field(name="Timestamp", value=timestamp_text) \
            .set_footer(text=f"Page: {page+1}/{total_pages+1}")

    total_warns = database_handle.cursor.execute(
        '''SELECT COUNT(*) FROM WARNS WHERE ID=:member_id''', {"member_id": user_id}).fetchone()[0]

    if total_warns == 0:
        await message.channel.send("User has no warns.")
    elif total_warns <= 10:
        await message.channel.send(embed=warn_embed_generator(0,0))
    else:
        response = await message.channel.send(embed=discord.Embed(title="Loading"))
        reaction_handler = util.ReactionPageHandle(client, response, message.author, warn_embed_generator, 0, (total_warns - 1) // 10)
        await reaction_handler.start()


@command({
    "syntax": "mywarns",
    "description": "See your own warns",
    "category": Category.MODERATION
})
async def mywarns(message: discord.Message, parameters: str, client: discord.Client) -> None:
    await warns(message, str(message.author.id), client)


@command({
    "syntax": "delwarn <member> <timestamp of warn>",
    "role_requirements": {configuration.MODERATOR_ROLE},
    "category": Category.MODERATION,
    "description": "Delete a warn from a user"
})
async def delwarn(message: discord.Message, parameters: str, client: discord.Client) -> None:
    member_reason = await util.split_into_member_and_reason(message, parameters)
    if member_reason == (None, None):
        raise CommandSyntaxError('You must specify a valid user')

    warn = database_handle.cursor.execute('''SELECT REASON FROM WARNS WHERE TIMESTAMP=:timestamp AND ID=:id''',
                                          {"timestamp": member_reason[1], "id": member_reason[0].id}).fetchone()

    if warn is not None:
        await message.channel.send(f"Deleting warn from {member_reason[0].name}#{member_reason[0].discriminator} ({member_reason[0].id}) about {warn[0]}")
    else:
        await message.channel.send("No warn found")
        return

    database_handle.cursor.execute('''DELETE FROM WARNS WHERE TIMESTAMP=:timestamp AND ID=:id''',
                                   {"timestamp": member_reason[1], "id": member_reason[0].id})
    database_handle.client.commit()


@command({
    "syntax": "mute <member> | <duration><s|m|h|d|w|y> [reason]",
    "role_requirements": {configuration.MODERATOR_ROLE},
    "category": Category.MODERATION,
    "description": "Mute a user for a specified duration"
})
async def mute(message: discord.Message, parameters: str, client: discord.Client) -> None:
    member_reason = await util.split_into_member_and_reason(message, parameters)
    if member_reason == (None, None):
        raise CommandSyntaxError('You must specify a valid user/duration.')

    try:
        time_reason = member_reason[1].split(maxsplit=1)
        multiplier = configuration.TIME_MULTIPLIER[time_reason[0][-1]]
        mute_time = int(time_reason[0][:-1]) * multiplier
    except:
        raise CommandSyntaxError('You must specify a valid duration.')

    # Give mute
    try:
        await member_reason[0].add_roles(message.guild.get_role(configuration.MUTED_ROLE))
    except discord.errors.Forbidden:
        await message.channel.send("I don't have perms to give mute role")
        return

    roles = member_reason[0].roles
    # Remove @everyone role
    roles = roles[1:]

    try:
        database_handle.cursor.execute('''INSERT INTO MUTES (ID, TIMESTAMP, ROLES) \
        VALUES(:member_id, :timestamp, :roles) ''',
                                       {'member_id': member_reason[0].id, 'timestamp': round(time()) + mute_time,
                                        'roles': str([role.id for role in roles])})
    except sqlite3.IntegrityError:
        await message.channel.send('User is already muted')
        return

    database_handle.client.commit()

    # Remove all roles
    forbidden_role_list = []
    for role in roles:
        if role.id != configuration.MUTED_ROLE:
            try:
                await member_reason[0].remove_roles(role)
            except discord.errors.Forbidden:
                forbidden_role_list.append(role)

    if forbidden_role_list:
        await message.channel.send(f"Unable to remove roles: {forbidden_role_list}")

    await warn(message, f'{member_reason[0].id} MUTE - {member_reason[1]}', client, action_name="muted")

    await asyncio.sleep(mute_time)
    await unmute(message, str(member_reason[0].id), client, silenced=True)


@command({
    "syntax": "unmute <member>",
    "role_requirements": {configuration.MODERATOR_ROLE},
    "category": Category.MODERATION,
    "description": "Unmutes a user"
})
async def unmute(message: discord.Message, parameters: str, client: discord.Client, guild=False, silenced=False) -> None:
    """
    Unmutes member
    Params:
    message: discord.message/guild object
    parameters: Parameters
    guild: if the message parameter is a guild object"""

    if guild:
        member = message.get_member(int(parameters))
    else:
        member = util.get_member_by_id_or_name(message, parameters)

    if member is None:
        user_id = util.try_get_valid_user_id(parameters)
        if not user_id:
            raise CommandSyntaxError("You must specify a valid user!")

    else:
        user_id = member.id

    roles = database_handle.cursor.execute('''SELECT ROLES FROM MUTES WHERE ID=:member_id''',
                                           {'member_id': user_id}).fetchone()

    database_handle.cursor.execute('''DELETE FROM MUTES WHERE ID=:member_id''',
                                   {'member_id': user_id})
    database_handle.client.commit()

    if roles is None:
        # If it's an empty array, they're in the database, elif None, they're not
        await message.channel.send("User is not muted")
        return

    if not member:
        # No need to re give roles or anything, they left
        if not silenced:
            await message.channel.send(f"Unmuted {user_id}")
        return

    # Re give roles
    roles = literal_eval(roles[0])
    forbidden_roles_list = []

    for role in roles:
        if guild:
            role = message.get_role(role)
        else:
            role = message.guild.get_role(role)

        try:
            await member.add_roles(role)
        except:
            forbidden_roles_list.append(role)

    if not silenced and forbidden_roles_list:
        await message.channel.send(f"Unable to re-give roles: {forbidden_roles_list}")

    # Remove muted role
    if guild:
        await member.remove_roles(message.get_role(configuration.MUTED_ROLE))
    else:
        await member.remove_roles(message.guild.get_role(configuration.MUTED_ROLE))

    # Inform user we're done
    if not silenced:
        await message.channel.send(f'Unmuted {member.name}#{member.discriminator} ({member.id})')


@command({
    "syntax": "kick <member> | [reason]",
    "aliases": ["kcik"],
    "role_requirements": {configuration.MODERATOR_ROLE},
    "category": Category.MODERATION,
    "description": "Kicks a user"
})
async def kick(message: discord.Message, parameters: str, client: discord.Client) -> None:
    member_reason = await util.split_into_member_and_reason(message, parameters)

    if member_reason[0] is None:
        raise CommandSyntaxError('You must specify a valid user.')

    if not message.guild.me.guild_permissions.kick_members:
        await message.channel.send("I don't have permissions to kick.")
        return

    if message.guild.me.top_role <= member_reason[0].top_role:
        await message.channel.send("I am not high enough in the role hierarchy")
        return

    # if message.author.top_role <= member_reason[0].top_role:
    #     await message.channel.send("You are not high enough in the role hierarchy.")
    #     return

    await warn(message, f"{member_reason[0].id} KICK - {member_reason[1]}", client, action_name="kicked")
    await message.guild.kick(member_reason[0], reason=member_reason[1])


@command({
    "syntax": "ban <member> | (optional) [delete message days, 0-7] | [reason]",
    "aliases": ["snipe"],
    "role_requirements": {configuration.MODERATOR_ROLE},
    "category": Category.MODERATION,
    "description": "Bans a user"
})
async def ban(message: discord.Message, parameters: str, client: discord.Client) -> None:
    member_reason = await util.split_into_member_and_reason(message, parameters)

    if member_reason[0] is None:
        raise CommandSyntaxError('You must specify a valid user.')

    if not message.guild.me.guild_permissions.ban_members:
        await message.channel.send("I don't have permissions to ban.")
        return

    if message.guild.me.top_role <= member_reason[0].top_role:
        await message.channel.send("I am not high enough in the role hierarchy.")
        return

    # if message.author.top_role <= member_reason[0].top_role:
    #     await message.channel.send("You are not high enough in the role hierarchy.")
    #     return

    if message.guild.me.guild_permissions.manage_guild:
        invites = await message.guild.invites()
        for invite in invites:
            if invite.inviter == member_reason[0]:
                await invite.delete()
    else:
        await message.channel.send("I need the `manage_guild` permission to view and delete their invites.")
    
    # See if the optional parameter for message deletion has been set.
    try:
        delete_days = int(member_reason[1][0])
        if delete_days > 7:
            delete_days = 0
    except (ValueError, TypeError) as e :
        delete_days = 0
        

    await warn(message, f"{member_reason[0].id} BAN - {member_reason[1]}", client, action_name="banned")
    await message.guild.ban(member_reason[0], reason=member_reason[1], delete_message_days=delete_days)

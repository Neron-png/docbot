from ast import literal_eval
import asyncio
import json
import sqlite3
from time import time
import os.path
import discord
import configuration
import util
from commands import Category, CommandSyntaxError, command
import database_handle
import logger
from datetime import datetime

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
    registered_team_channels = {}
    category_channel_count = {x: 0 for x in configuration.TEAMS_CATEGORIES} # Counting because discord's limit is 50 channels per category
    
    for channel in message.guild.channels:
        if channel.category and (channel.category.id in configuration.TEAMS_CATEGORIES):
                category_channel_count[channel.category.id] += 1
                if str(channel.type) == 'text':
                    registered_team_codes += [channel.topic]
                    if channel.topic:
                        registered_team_channels[channel.topic] = channel
    
    
    
    # Adding the team channel
    for team in teams:
        if team['TYPE'] == "looking":
            continue
        
        if team['CODE'] not in registered_team_codes:
            
            # Find empty category
            for category in message.guild.categories:
                if category.id not in configuration.TEAMS_CATEGORIES or category_channel_count[category.id] > 40:
                    continue
                
                team_members = []
                for i in range(1, 5):
                    if team[f'PLAYER #{i} ID']:
                        try:
                            team_members += [ message.guild.get_member(team[f'PLAYER #{i} ID'])]
                        except Exception as e:
                            await message.channel.send(f"Issue with {team[f'PLAYER #{i} ID']}, {team['CODE']}")
                
                # Giving members their role
                for member in team_members:
                    await member.add_roles(message.guild.get_role(configuration.DOC_PARTICIPANT_ROLE))
                
                # Generating permission overrides, so that only the members can see them
                
                # Member overrides
                overwrites  = {
                     x: discord.PermissionOverwrite(read_messages=True, attach_files=True, read_message_history=True) for x in team_members 
                }
                # Everyone overrides
                overwrites[message.guild.default_role] = discord.PermissionOverwrite(read_messages=False)
                overwrites[message.guild.get_role(configuration.MODERATOR_ROLE)] = discord.PermissionOverwrite(read_messages=True, attach_files=True, read_message_history=True)
                
                await category.create_text_channel(name= team['NAME'], topic=team['CODE'], overwrites=overwrites )
                break
        else:
            # Team has been registered, so check if new members are due
            try:
                channel = registered_team_channels[team["CODE"]]
                team_members = []
                for i in range(1, 5):
                    member = message.guild.get_member(team[f'PLAYER #{i} ID'])
                    if member:
                        team_members += [member]
                
                # Giving members their role
                for member in team_members:
                    await member.add_roles(message.guild.get_role(configuration.DOC_PARTICIPANT_ROLE))
                
                # Member overrides
                overwrites  = {
                     x: discord.PermissionOverwrite(read_messages=True, attach_files=True, read_message_history=True) for x in team_members 
                }
                overwrites[message.guild.default_role] = discord.PermissionOverwrite(read_messages=False)
                overwrites[message.guild.get_role(configuration.MODERATOR_ROLE)] = discord.PermissionOverwrite(read_messages=True, attach_files=True, read_message_history=True)
                
                for key, value in overwrites.items():
                    await channel.set_permissions(key, overwrite=value)
                
                
            except Exception as e:
                await message.channel.send(f"Issue {e}")
            
        await asyncio.sleep(1)    
           
    await message.reply("Import successful!")        
    


@command({
    "syntax": "set_day <int: day number>",
    "aliases": ["set"],
    "role_requirements": {configuration.MODERATOR_ROLE},
    "category": Category.MODERATION,
    "description": "Set the day of Days of coding and unlock the relevant stuff"
})
async def set_day(message: discord.Message, parameters: str, client: discord.Client) -> None:
    
    day = int(parameters[0])

    if day not in [x for x in range(8)]:
        await message.reply("What is that? It's not a valid day!")
        return
    
    # get the file to update in the path
    # It should be up two levels from the current dir
    path = os.path.split(os.path.dirname(__file__))
    path = os.path.split(path[0])
    path = os.path.split(path[0])
    path = path[0]
    file = path + "/DaysOfCoding2023SignUp/" + "activeDay"
    
    # setting the day
    with open(file, "w") as f:
        f.write(str(day))
    
    await message.reply(f"Updated the day to {day}")
    

@command({
    "syntax": "commit",
    "aliases": ["upload", "publish"],
    "role_requirements": {configuration.MODERATOR_ROLE},
    "category": Category.MODERATION,
    "description": "Commit the leaderboard grades"
})
async def commit(message: discord.Message, parameters: str, client: discord.Client) -> None:
    
    grades = util.getGrading()
    
    # Discord embed
    # embed=discord.Embed(title="(Click) Full Leaderboard", url="https://auth.acm.org/days-of-coding-event", color=0xb81fff)
    # embed.set_author(name="Leaderboard (top 5)", url="https://auth.acm.org/days-of-coding-event")
    # lb_len = 5 if len(grades) > 5 else len(grades)
    # for i in range(lb_len):
    #     team_name = grades[i]["name"]
    #     score = grades[i]["score"]
        
    #     embed.add_field(name=f"{team_name}: {score}pts", value="", inline=False)
    # embed.set_footer(text="Το πλήρες leaderboard στο https://auth.acm.org/days-of-coding-event/leaderboard")
    # await message.channel.send(embed=embed)
    
    # Generating the JSON File
    
    leaderboard = {"leaderboard" : [],
                   "updated": datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
    for grade in grades:
        team_name = grade["name"]
        team_code = grade["ID"]
        score = grade["score"]
        team = util.getTeam(team_code)
        members = []
        for member in (team["PLAYER #1 NAME"], team["PLAYER #2 NAME"], team["PLAYER #3 NAME"], team["PLAYER #4 NAME"]):
            if member:
                members += [member]
        leaderboard["leaderboard"] += [{"team": team_name,
                        "id": team_code,
                        "score": score,
                        "members": members}]
                        
    print(leaderboard)
    
    path = os.path.split(os.path.dirname(__file__))
    path = os.path.split(path[0])
    path = os.path.split(path[0])
    path = path[0]
    file = path + "/DaysOfCoding2023SignUp/" + "leaderboard.json"
    
    # setting the day
    with open(file, "w") as f:
        f.write(json.dumps(leaderboard))
    
    

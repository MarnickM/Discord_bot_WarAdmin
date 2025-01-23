import os, json, time, threading
import discord
from discord import channel
from discord.ui import Button
from discord.ext import commands
from datetime import datetime, timedelta
from itertools import islice
import requests
import aiohttp
from pymongo import MongoClient
from datetime import datetime, timedelta
import time
import aiohttp
# from discord_slash.utils.manage_components import create_button, create_actionrow
# from discord_slash.model import ButtonStyle
# pm2 list => to view processes
# pm2 start main.py 
# pm2 logs id
# pm2 stop id
# pm2 restart id
# pm2 logs 0 --lines 50

intents = discord.Intents.all()
intents.messages = True
bot = commands.Bot(command_prefix="-", intents=intents)

garyID = 781062676557594625
evoID = 196032505940279296
mosID = 548554534411042848
juiceID = 351204529229922305

async def loadJson(fileName):
  with open(fileName, 'r') as file:
    data = json.load(file)
    return data


async def saveJson(fileName, data):
  with open(fileName, 'w') as file:
    json.dump(data, file, indent=4)


@bot.event
async def on_ready():
  print("bot ready")

def replace_spaces(string):
    return string.replace(" ", "%20")

# first_entry = True
# Dictionary to store initial WarPoints for alliances
initial_warpoints = {}
# Dictionary to store the latest WarPoints for alliances
latest_warpoints = {}

def check_war_state():
    
    global initial_warpoints, latest_warpoints
    while True:
        # print("function started")
        try:
            response = requests.get("https://api.galaxylifegame.net/Alliances/warpointLb")
            alliance_data = response.json()

            for alliance in alliance_data:
                alliance_name = alliance["Name"]
                allaince_search = replace_spaces(alliance_name)

                # Retrieve current alliance data
                alliance_info = requests.get(f"https://api.galaxylifegame.net/Alliances/get?name={allaince_search}")
                current_alliance = alliance_info.json()

                if alliance_name not in initial_warpoints:
                        initial_warpoints[alliance_name] = current_alliance["WarPoints"]
                        
                if current_alliance["InWar"]:
                    # Store the latest score even during the war
                    latest_warpoints[alliance_name] = current_alliance["WarPoints"]
                else:
                    # If the war has ended, update the total score to the latest score
                    if alliance_name in initial_warpoints:
                        initial_warpoints[alliance_name] = latest_warpoints.get(alliance_name, current_alliance["WarPoints"])
            time.sleep(60)

        except Exception as e:
            print(f"Error occurred: {e}")
            time.sleep(60)  # Wait for a minute before retrying


# Start the thread to continuously check the war state
thread = threading.Thread(target=check_war_state)
thread.start()

# @bot.command()
# async def war(ctx, alliance=None):
#     if alliance is None:
#         await ctx.send("Please provide an alliance name")
#         return
    
#     alliance_search = replace_spaces(alliance)
#     response = requests.get(f"https://api.galaxylifegame.net/Alliances/get?name={alliance_search}")
#     alliance_data = response.json()

#     if alliance_data["InWar"]:
#         alliance_search = replace_spaces(alliance_data["OpponentAllianceId"])
#         opponents = requests.get(f"https://api.galaxylifegame.net/Alliances/get?name={alliance_search}")
#         enemy_alliance_data = opponents.json()
        
#         # Retrieve initial and latest warpoints for the alliance and its opponent
#         initial_score_alliance = initial_warpoints.get(alliance_data["Name"], 0)  
#         initial_score_opponent = initial_warpoints.get(enemy_alliance_data["Name"], 0) 

#         default = "Alliance not in Leaderbord"
#         latest_score_alliance = latest_warpoints.get(alliance_data["Name"], default)
#         latest_score_opponent = latest_warpoints.get(enemy_alliance_data["Name"], default)
        
#         # Calculate score difference
#         if latest_score_alliance != default and latest_score_opponent != default:
#           score_difference_alliance = latest_score_alliance - initial_score_alliance
#           score_difference_opponent = latest_score_opponent - initial_score_opponent
#         elif latest_score_alliance == default and latest_score_opponent != default:
#           score_difference_alliance = default
#           score_difference_opponent = latest_score_opponent - initial_score_opponent
#         elif latest_score_alliance != default and latest_score_opponent == default:
#           score_difference_alliance = latest_score_alliance - initial_score_alliance
#           score_difference_opponent = default
#         else:
#           score_difference_alliance = default
#           score_difference_opponent = default
          

#         embed = discord.Embed(title="Current war",
#                               color=discord.Colour.from_rgb(255, 191, 0))
        
#         embed.add_field(name=f"{alliance_data['Name']} VS {enemy_alliance_data['Name']}", 
#                         value=f"{str(score_difference_alliance)} <:Warpoints:1206215489349619722>   :  {str(score_difference_opponent)} <:Warpoints:1206215489349619722> ")
        
#         await ctx.send(embed=embed)  # Send the embed message
#     else: 
#         await ctx.send("They are currently not in a war")


class DatabaseConnection:
    def __init__(self):
        self.client = MongoClient(self.connection_string)
        self.db = self.client['Galaxy_Life']
      
    async def get_score(self, name: str):
        collection = self.db['alliances']
        alliance = collection.find_one({"Name": name})
        if alliance:
            score = alliance.get("pointsGained", 0)
            return score
        else:
            # await DatabaseConnection.add_alliance(self=DatabaseConnection(), alliance_name=name)
            return 0
    
    def get_war_start_time(self, alliance_name: str):
        collection = self.db['alliances']
        alliance = collection.find_one({"Name": alliance_name})
        if alliance is not None:
            return alliance.get("warStartTime", 0)
        else:
            return "*not tracked*"
    
    
    async def add_alliance(self, alliance_name):
      collection = self.db['alliances']
      try:
          alliance_search = alliance_name.replace(" ", "%20")
          async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.galaxylifegame.net/Alliances/get?name={alliance_search}") as response:
                if response.status == 200:
                    alliance_data = await response.json(content_type="text/plain")
        
                    # Calculate the average player level
                    total_levels = sum(member['Level'] for member in alliance_data.get('Members', []))
                    players_count = len(alliance_data.get('Members', []))
                    avg_player_level = total_levels / players_count if players_count > 0 else 0
        
                    # Calculate the average HQ level
                    total_hq_levels = 0
                    for member in alliance_data.get('Members', []):
                        player_name = member['Name']
                        async with aiohttp.ClientSession() as session:
                            player_name = player_name.replace(" ", "%20")
                            async with session.get(f"https://api.galaxylifegame.net/Users/name?name={player_name}") as player_response:
                                 if player_response.status == 200:
                                     player_data = await player_response.json(content_type="text/plain")
                                     if player_data.get('Planets'):
                                         total_hq_levels += player_data['Planets'][0]['HQLevel']
        
                    avg_hq_level = total_hq_levels / players_count if players_count > 0 else 0
        
                    # Prepare the document with fetched data
                    alliance_document = {
                        "Name": alliance_data.get("Name", alliance_name),
                        "avgPlayerLevel": avg_player_level,
                        "warpoints": alliance_data.get("WarPoints", 0),
                        "avgHQLevel": avg_hq_level,
                        "varHQLevel": 0,  # Placeholder, needs specific logic to determine this value
                        "PlayersCount": players_count,
                        "warPointsAvailable": 0,  # Placeholder, needs specific logic to determine this value
                        "InWar": alliance_data.get("InWar", False),
                        "LastUpdate": datetime.now(),
                        "WarsWon": alliance_data.get("WarsWon", 0),
                        "WarsLost": alliance_data.get("WarsLost", 0),
                        "OpponentAllianceId": alliance_data.get("OpponentAllianceId", ""),
                        "pointsGained": 0,
                        "remainingTime":0,
                        "initialWarPoints":alliance_data.get("WarPoints", 0),
                        "warStartTime":datetime.now()
                    }
        
                    # Insert the document into the collection
                    collection.insert_one(alliance_document)
                    print(f"Inserted data for alliance: {alliance_name}")
                else:
                    print(f"Failed to fetch data for alliance: {alliance_name} - Status Code: {response.status}")
      except Exception as e:
          print(f"Error processing alliance: {alliance_name} - Error: {e}")
        

def format_score(self, num):
    return f"{num:,}"

@bot.command()
async def war(ctx, alliance_name: str):
    try:
        # Fetch data for the user's alliance
        alliance_search = replace_spaces(alliance_name)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.galaxylifegame.net/Alliances/get?name={alliance_search}") as response:

                 if response.status == 200:
                     alliance_data = await response.json(content_type="text/plain")
                     in_war = alliance_data.get("InWar", False)
         
                     if in_war:
                         enemy_alliance_id = alliance_data.get("OpponentAllianceId", "Unknown")
                         enemy_alliance_id = replace_spaces(enemy_alliance_id)
         
                         # Fetch data for the enemy alliance
                         async with aiohttp.ClientSession() as session:
                                async with session.get(f"https://api.galaxylifegame.net/Alliances/get?name={enemy_alliance_id}") as enemy_alliance_response:
                                   if enemy_alliance_response.status == 200:
                                        enemy_alliance_data = await enemy_alliance_response.json(content_type="text/plain")
                                        enemy_alliance_name = enemy_alliance_data.get("Name", "Unknown")
                   
                                        our_score = await DatabaseConnection.get_score(self=DatabaseConnection(), name=alliance_name)
                                        our_score_formatted = format_score(self=DatabaseConnection(), num=our_score)
                                        their_score = await DatabaseConnection.get_score(self=DatabaseConnection(), name=enemy_alliance_name)
                                        their_score_formatted = format_score(self=DatabaseConnection(), num=their_score)

                                        war_start_time = DatabaseConnection.get_war_start_time(self=DatabaseConnection(), alliance_name=alliance_name)

                                        if war_start_time != "*not tracked*":
                                             # get time until 3 day end mark
                                             current_time = datetime.now()
                                             three_day_mark = war_start_time + timedelta(days=3)
                                             max_duration_left = three_day_mark - current_time
                                                     
                                             # Format max duration left as HH:MM:SS
                                             max_duration_hours = max_duration_left.total_seconds() // 3600
                                             max_duration_minutes = (max_duration_left.total_seconds() % 3600) // 60
                                             max_duration_seconds = max_duration_left.total_seconds() % 60
                                             max_duration_str = f"{int(max_duration_hours)}:{int(max_duration_minutes):02}:{int(max_duration_seconds):02}"
                                        else:
                                           max_duration_str = "not tracked"
     
                   
                                        # # Calculate remaining time if available
                                        # fifteen_hour_mark = war_start_time + timedelta(hours=14) + timedelta(minutes=10)
                                                    
                                        #             # Calculate remaining time based on the score
                                        # remainingTime = db_operations.calculate_remaining_time(our_score, their_score)
                                        # if remainingTime == "no points yet":
                                        #         # Set remainingTime to the 15-hour mark if no points yet
                                        #         remainingTime = fifteen_hour_mark.timestamp()
                                        # else:
                                        #     # Convert remainingTime to a timedelta
                                        #     remaining_time_delta = timedelta(seconds=remainingTime)
                                        #     calculated_end_time = current_time + remaining_time_delta
                                                    
                                        #     # Determine the appropriate end time
                                        # if current_time < fifteen_hour_mark:
                                        #         remainingTime = fifteen_hour_mark.timestamp()
                                        # else:
                                        #     remainingTime = calculated_end_time.timestamp()
                                                    
                                        # # Ensure remainingTime is an integer Unix timestamp
                                        # remaining_time = int(remainingTime)
                   
                                       # Construct embed with scores, progress bar, and remaining time
                                        embed = discord.Embed(
                                           title=f"{alliance_name} vs {enemy_alliance_name}",
                                           color=discord.Color.red(),
                                        )
                   
                                        embed.add_field(name="", value=f"{our_score_formatted} <:Warpoints:1262351554682294293>    :    {their_score_formatted} <:Warpoints:1262351554682294293>", inline=False)
                                        # embed.add_field(name="Earliest KO", value=f"<t:{remaining_time}:R>", inline=False)
                                        embed.add_field(name="Time left", value=max_duration_str, inline=False)
                   
                                        await ctx.send(embed=embed)
                                   else:
                                        await ctx.send(f"Failed to fetch data for enemy alliance - Status Code: {enemy_alliance_response.status}")
                     else:
                         await ctx.send(f"Alliance {alliance_name} is not currently in a war.")
                 else:
                     await ctx.send(f"Failed to fetch data for alliance {alliance_name} - Status Code: {response.status}")
         
    except json.JSONDecodeError as e:
        if "Expecting value: line 1 column 1 (char 0)" in str(e):
            await ctx.send("You mistyped the name or this alliance doesn't exist.")
            # Handle the error, for example, by setting a default value
        else:
            # Print the exception message if it's a different JSONDecodeError
            await ctx.send(f"Unexpected JSONDecodeError: {e}")
            # Re-raise the exception
            raise

    except AttributeError as e:
        if "'NoneType' object has no attribute 'get'" in str(e):
            await ctx.send("You mistyped the name or this alliance doesn't exist.")
            # Handle the error, for example, by setting a default value
        else:
            # Print the exception message if it's a different AttributeError
            await ctx.send(f"Unexpected AttributeError: {e}")
            # Re-raise the exception
            raise
           






@bot.command()
async def status(ctx):
    await ctx.send("Please be patient... gathering info")
    response = requests.get("https://api.galaxylifegame.net/Alliances/warpointLb")
    alliance_data = response.json()[:50]  # Fetch only the first 50 alliances

    total_alliances = len(alliance_data)
    num_batches = (total_alliances + 24) // 25  # Calculate the number of batches

    for batch in range(num_batches):
        start_index = batch * 25
        end_index = min(start_index + 25, total_alliances)

        embed = discord.Embed(title=f"Status of top 50 alliances - Part {batch + 1}",
                              color=discord.Colour.from_rgb(255, 191, 0))

        for i in range(start_index, end_index):
            text = ""
            alliance = alliance_data[i]
            alliance_search = replace_spaces(alliance["Name"])
            response = requests.get(f"https://api.galaxylifegame.net/Alliances/get?name={alliance_search}")
            alliance_info = response.json()

            if alliance_info["InWar"]:
                alliance_search = replace_spaces(alliance_info["OpponentAllianceId"])
                opponents = requests.get(f"https://api.galaxylifegame.net/Alliances/get?name={alliance_search}")
                enemy_alliance_data = opponents.json()
                text += f"in war with {enemy_alliance_data['Name']}"
            else:
                text += "not in war"

            embed.add_field(name=f"#{i + 1} {alliance_info['Name']}", value=text)

        await ctx.send(embed=embed)

@bot.command()
async def statusExtended(ctx):
    await ctx.send("Please be patient... gathering info")
    response = requests.get("https://api.galaxylifegame.net/Alliances/warpointLb")
    alliance_data = response.json()  

    total_alliances = len(alliance_data)
    num_batches = (total_alliances + 24) // 25  # Calculate the number of batches

    for batch in range(num_batches):
        start_index = batch * 25
        end_index = min(start_index + 25, total_alliances)

        embed = discord.Embed(title=f"Status of top 100 alliances - Part {batch + 1}",
                              color=discord.Colour.from_rgb(255, 191, 0))

        for i in range(start_index, end_index):
            text = ""
            alliance = alliance_data[i]
            alliance_search = replace_spaces(alliance["Name"])
            response = requests.get(f"https://api.galaxylifegame.net/Alliances/get?name={alliance_search}")
            alliance_info = response.json()

            if alliance_info["InWar"]:
                alliance_search = replace_spaces(alliance_info["OpponentAllianceId"])
                opponents = requests.get(f"https://api.galaxylifegame.net/Alliances/get?name={alliance_search}")
                enemy_alliance_data = opponents.json()
                text += f"in war with {enemy_alliance_data['Name']}"
            else:
                text += "not in war"

            embed.add_field(name=f"#{i + 1} {alliance_info['Name']}", value=text)

        await ctx.send(embed=embed)


# @bot.command()
# async def addmember(ctx):
  
#   name = ctx.author.name
#   members = await loadJson("./members.json")
#   if members[name] is not None:
#     ctx.send(f"{name} is already in the members list!")
#     return
  
#   members["members"][name] = {"points": "0", "totalpoints": "0"}
#   await saveJson("./members.json", members)
#   await ctx.send(f"{name} has been added!")


# @bot.command()
# async def delmember(ctx, member=None):
#   if ctx.author.id != garyID and ctx.author.id != evoID and ctx.author.id != mosID:
#       await ctx.send("you can't use this command")
#       return
#   if member is None:
#     await ctx.send("Please write the member name")
#     return
#   members = await loadJson("./members.json")
#   if member not in members["members"]:
#     await ctx.send("This member does not exist!")
#     await ctx.send(":information_source: Don't forget use the real discord name of the user you want to delete.")
#   else:
#     del members["members"][member]
#     await saveJson("./members.json", members)
#     await ctx.send("Member has been removed!")


# @bot.command()
# async def score(ctx):
#   members = await loadJson("./members.json")
#   war = await loadJson("./war_info.json")
#   enemy_name = war["name"]
#   total_war_score = 0
#   for member, values in members["members"].items():
#     total_war_score += int(values["points"])

#   # Iterate through each member and get the 5 highest points
#   for member, values in members["members"].items():
#       points_list = [(key, value["points"]) for key, value in members["members"].items()]
#       points_list.sort(key=lambda x: x[1], reverse=True)
      
#       # Get the top 5 points for the current member
#       top_5_points = points_list[:5]

#   file = discord.File("./1_5_1_1.png", filename="1_5_1_1.png")

#   embed = discord.Embed(
#     title="Scoreboard",
#     description=f"Galactic Empire II VS {enemy_name}",
#     color=discord.Colour.from_rgb(255, 191, 0)
#   )
#   embed.set_thumbnail(url="attachment://1_5_1_1.png")

  
#   embed.add_field(name=f":first_place: {top_5_points[0][0]}",value=f"Total score: {top_5_points[0][1]}",inline=False)
#   embed.add_field(name=f":second_place: {top_5_points[1][0]}",value=f"Total score: {top_5_points[1][1]}",inline=False)
#   embed.add_field(name=f":third_place: {top_5_points[2][0]}",value=f"Total score: {top_5_points[2][1]}",inline=False)
#   embed.add_field(name=f"#4 {top_5_points[3][0]}",value=f"Total score: {top_5_points[3][1]}",inline=False)
#   embed.add_field(name=f"#5 {top_5_points[4][0]}",value=f"Total score: {top_5_points[4][1]}",inline=False)
#   embed.set_footer(text="doesn't regard wp reductions")

#   # row = discord.create_actionrow(*[
#   #   discord.create_button(style=discord.ButtonStyle.secondary, label="War Scoreboard", custom_id="War Scoreboard"),
#   #   discord.create_button(style=discord.ButtonStyle.secondary, label="Alliance Scoreboard", custom_id="Alliance Scoreboard")])
    
#   #   # Send the message with buttons
#   await ctx.send(file=file, embed=embed) # , components=[row]


# @bot.event
# async def on_button_click(interaction):
#     if interaction.custom_id == "War Scoreboard":
#         await show_alliance_scoreboard(interaction, alliance_id=1)
#     elif interaction.custom_id == "Alliance Scoreboard":
#         await show_alliance_scoreboard(interaction, alliance_id=2)

# async def show_alliance_scoreboard(interaction, alliance_id):
#     members = await loadJson("C:\\Users\\Marni\\Desktop\\Games\\Galaxy_life\\Bot\\GalaxyLifeBot\\members.json")

#     for member, values in members["members"].items():
#       points_list = [(key, value["totalpoints"]) for key, value in members["members"].items()]
#       points_list.sort(key=lambda x: x[1], reverse=True)
      
#       # Get the top 5 points for the current member
#       top_5_points = points_list[:5]
    
#     # Implement logic to fetch and display the scoreboard for the selected alliance
#     # Modify the logic based on your requirements
    
#     file = discord.File("C:\\Users\\Marni\\Desktop\\Games\\Galaxy_life\\Bot\\GalaxyLifeBot\\1_5_1_1.png", filename="1_5_1_1.png")

#     embed = discord.Embed(
#         title=f"Top 5 highest warpoints in Galactic Empire II",
#         description=f"Total points",
#         color=discord.Colour.from_rgb(255, 191, 0)
#     )
#     embed.set_thumbnail(url="attachment://1_5_1_1.png")

#     embed.add_field(name=f":first_place: {top_5_points[0][0]}",value=f"Total score: {top_5_points[0][1]}",inline=False)
#     embed.add_field(name=f":second_place: {top_5_points[1][0]}",value=f"Total score: {top_5_points[1][1]}",inline=False)
#     embed.add_field(name=f":third_place: {top_5_points[2][0]}",value=f"Total score: {top_5_points[2][1]}",inline=False)
#     embed.add_field(name=f"#4 {top_5_points[3][0]}",value=f"Total score: {top_5_points[3][1]}",inline=False)
#     embed.add_field(name=f"#5 {top_5_points[4][0]}",value=f"Total score: {top_5_points[4][1]}",inline=False)
#     embed.set_footer(text="Might be inaccurate due to wp reductions for attacking low lvl players.")
#     await interaction.message.edit(embed=embed, file=file)


@bot.command()
async def save(ctx):

  war = await loadJson("./war_info.json")
  alliance_name = war["name"]
  archive = await loadJson("./war_archive.json")

  if alliance_name in archive and archive[alliance_name] is not None:
    temporary_save = archive[alliance_name]
    await saveJson("./backup.json", temporary_save)
    await ctx.send("This alliance already existed in archive, overwriting...")
    archive[alliance_name] = {}

  archive[alliance_name] = war
  await saveJson("./war_archive.json", archive)
  await ctx.send("Saved!")


@bot.command()
async def createwar(ctx, enemyAlliance=None):
  if ctx.author.id != garyID and ctx.author.id != evoID and ctx.author.id != juiceID:
    await ctx.send("you can't use this command")
    return
  if enemyAlliance is None:
    await ctx.send("Please write the enemy alliance name!")
    return

  archive = await loadJson("./war_archive.json")
  war = await loadJson("./war_info.json")

  global regentime
  regentime = 0
  if enemyAlliance in archive and archive[enemyAlliance] is not None:
    war = archive[enemyAlliance]
  else:
    war["name"] = enemyAlliance
    war["members"] = {}

  await saveJson("./war_info.json", war)
  await ctx.send("War has been created")


regentime = 0

@bot.command()
async def setTime(ctx, regenTime=None):
    if regenTime is None:
        await ctx.send("You must provide a rebuild time.")
        return

    try:
        regenTime = int(regenTime)
    except ValueError:
        await ctx.send("Rebuild time must be a number.")
        return

    if regenTime < 3 or regenTime > 7:
        await ctx.send("Rebuild time can be max 7 or min 3.")
        return

    global regentime
    regentime = regenTime
    await ctx.send(f"Rebuild time set to {regentime}")

@bot.command()
async def addenemy(ctx, enemy=None, starbaseLVL=None):
  # added starbaseLVL none check
  if enemy is None or starbaseLVL is None:
    await ctx.send("Please write the enemy name and starbase lvl!")
    return
  # added error check for starbase lvl
  if int(starbaseLVL) < 1 or int(starbaseLVL) > 9:
    await ctx.send("There can only be starbases between 1 and 9")
    return

  # create starbase lvl template
  starbasetemp = "SB" + starbaseLVL

  war = await loadJson("./war_info.json")
  lower_case_members = {
      key.lower(): value
      for key, value in war["members"].items()
  }

  if enemy.lower() in lower_case_members:
    lower_enemy = enemy.lower()
    for key, value in war["members"].items():
      if key.lower() == lower_enemy:
        enemy = key
        break

  if enemy in war["members"]:
    await ctx.send("The enemy is already registered!")
    return
  # added the starbase to the list
  war["members"][enemy] = {"C0": ["0", "0", starbasetemp]}
  await saveJson("./war_info.json", war)
  await ctx.send("Added enemy **" + enemy + "** !")


@bot.command()
async def addcolony(ctx,
                    enemy=None,
                    colony=None,
                    coordinates=None,
                    starbaseLVL=None):
  # added coordinates and starbase lvl
  if enemy is None or colony is None or coordinates is None or starbaseLVL is None:
    await ctx.send(
        "Please write the enemy name, colony number, coordinates and starbase lvl!!"
    )
    return
  if int(colony) < 1 or int(colony) > 11:
    await ctx.send("There can only be colonies between 1 and 11")
    return
  # added error check for starbase lvl
  if int(starbaseLVL) < 1 or int(starbaseLVL) > 9:
    await ctx.send("There can only be starbases between 1 and 9")
    return
  
  # create starbase lvl template
  starbasetemp = "SB" + starbaseLVL
  ctemp = "C" + colony
  war = await loadJson("./war_info.json")
  lower_case_members = {
      key.lower(): value
      for key, value in war["members"].items()
  }

  if enemy.lower() in lower_case_members:
    lower_enemy = enemy.lower()
    for key, value in war["members"].items():
      if key.lower() == lower_enemy:
        enemy = key
        break
  if enemy in war["members"]:
    if ctemp in war["members"][enemy]:
      await ctx.send("The colony is already registered!")
      return
  else:
    await ctx.send("The enemy does not exist!!")
    return
  # place after name Cx,coords,starbase in list
  war["members"][enemy][ctemp] = ["0", coordinates, starbasetemp]

  for member, colonies in war['members'].items():
    sorted_colonies = dict(
        sorted(colonies.items(), key=lambda x: int(x[0][1:])))
    war['members'][member] = sorted_colonies

  await saveJson("./war_info.json", war)
  await ctx.send("Added colony **" + colony + "** for **" + enemy + "** !")


@bot.command()
async def delenemy(ctx, enemy=None):
  if enemy is None:
    await ctx.send("Please write the enemy name!")
    return
  
  war = await loadJson("./war_info.json")

  lower_case_members = {
      key.lower(): value
      for key, value in war["members"].items()
  }

  if enemy.lower() in lower_case_members:
    lower_enemy = enemy.lower()
    for key, value in war["members"].items():
      if key.lower() == lower_enemy:
        enemy = key
        break

  
  if enemy in war["members"]:
    del war["members"][enemy]
    await saveJson("./war_info.json", war)
    await ctx.send("Enemy removed!")
  else:
    await ctx.send("The enemy does not exist!")


@bot.command()
async def delcolony(ctx, enemy=None, colony=None):
  if enemy is None or colony is None:
    await ctx.send("Please write the enemy name and colony number!")
    return
  if int(colony) < 1 or int(colony) > 11:
    await ctx.send("There can only be colonies between 1 and 11")
    return
  
  war = await loadJson("./war_info.json")
  lower_case_members = {
    key.lower(): value
    for key, value in war["members"].items()
  }

  if enemy.lower() in lower_case_members:
    lower_enemy = enemy.lower()
    for key, value in war["members"].items():
      if key.lower() == lower_enemy:
        enemy = key
        break
  ctemp = "C" + colony
  
  if enemy in war["members"]:
    if ctemp in war["members"][enemy]:
      del war["members"][enemy][ctemp]
      await saveJson("./war_info.json", war)
      await ctx.send("Enemy colony removed!")
    else:
      await ctx.send("This enemy colony does not exist!")
  else:
    await ctx.send("The enemy does not exist!!")

claim = {
        "bonvsko": ["no lock", "0", "enemy", "0"],
        "pawelcio": ["no lock", "0", "enemy", "0"],
        "kuxaku": ["no lock", "0", "enemy", "0"],
        "daynas": ["no lock", "0", "enemy", "0"],
        "EOVComix": ["no lock", "0", "enemy", "0"],
        "0770": ["no lock", "0", "enemy", "0"],
        "Cerdukay": ["no lock", "0", "enemy", "0"],
        "Juice_Lime": ["no lock", "0", "enemy", "0"],
        "Mossoma": ["no lock", "0", "enemy", "0"],
        "Nigkiip": ["no lock", "0", "enemy", "0"],
        "Ahmedwaheed": ["no lock", "0", "enemy", "0"],
        "Garybaldy16": ["no lock", "2024-02-01 18:53:00", "test1", "C0"],
        "Miw": ["no lock", "0", "enemy", "0"]
}

def check_reset_timer():
    global claim

    while True:
        current_time = datetime.now()

        for name, player_list in claim.items():
            if player_list[0] == "claimed":
                claim_time = datetime.strptime(player_list[1], "%Y-%m-%d %H:%M:%S")
                time_difference = current_time - claim_time

                if time_difference >= timedelta(minutes=15):
                    # Reset the player_list fields
                    player_list[0] = "no lock"
                    player_list[1] = "0"
                    player_list[2] = "enemy"
                    player_list[3] = "0"

        # Sleep for 1 minute before checking again
        time.sleep(60)

# # Start the thread
# timer_thread = threading.Thread(target=check_reset_timer)
# timer_thread.start()

@bot.command()
async def claim(ctx, enemy=None, colony="0"):
  if enemy is None or colony is None:
    await ctx.send("Please write the enemy name and colony number!")
    return
  
  if colony != "0":
    if int(colony) < 1 or int(colony) > 11:
      await ctx.send("There can only be colonies between 1 and 11")
      return
    
  ctemp = "C" + colony
  war = await loadJson("./war_info.json")
  global claim
  

  author = ctx.author.id
  print(author)
  print(type(author))
  ids = {
    "bonvsko":508684349294641155,
    "pawelcio":347291231396691978,
    "kuxaku":1078626493023920178,
    "daynas":241532814292418570,
    "EOVComix":196032505940279296,
    "0770":1184165487861563433,
    "Cerdukay":786853381833752586,
    "Juice_Lime":351204529229922305,
    "Mossoma":548554534411042848,
    "Nigkiip":324196976839229441,
    "Ahmedwaheed":679724404757889066,
    "Garybaldy16":781062676557594625,
    "Miw":485145604989779998
  }
  existance = False
  name = None
  player_list = []

  for key, value in ids.items():
    if author == value:
        name = key
        existance = True
        break
    else:
        existance = False

  if existance == False:
     await ctx.send(f"You are not registered yet {ctx.author.name}, please contact Gary.")
     return

  lower_case_members = {
      key.lower(): value
      for key, value in war["members"].items()
  }
  if enemy.lower() in lower_case_members:
    lower_enemy = enemy.lower()
    for key, value in war["members"].items():
      if key.lower() == lower_enemy:
        enemy = key

    if ctemp in war["members"][enemy]:
       
       player_list = claim["members"][name]
       print(claim["members"][name])

       if player_list[0] == "claimed":
         await ctx.send("You already claimed a target, please wait before claiming another one.")
         return
       
       player_list[0] = "claimed"
       player_list[1] = datetime.now().strftime(
          "%Y-%m-%d %H:%M:%S")
       player_list[2] = enemy
       player_list[3] = ctemp

       claim["members"][name] = player_list
       if colony == "0":
         await ctx.send("You have claimed **" + enemy + "** **main** planet")
       else:
          if colony == "1":
            await ctx.send("You have claimed **" + enemy + "** **" + colony + "st colony**")
          elif colony == "2":
            await ctx.send("You have claimed **" + enemy + "** **" + colony + "nd colony**")
          elif colony == "3":
            await ctx.send("You have claimed **" + enemy + "** **" + colony + "rd colony**")
          else:
            await ctx.send("You have claimed **" + enemy + "** **" + colony + "th colony**")

       await saveJson("./claim.json",claim)
    else:
       await ctx.send("The enemy colony does not exist!")
  else:
    await ctx.send("The enemy does not exist!")

  



@bot.command()
async def down(ctx, enemy=None, colony="0"):

  if enemy is None:
    await ctx.send("Please write the enemy name!")
    return

  if colony != "0":
    if int(colony) < 1 or int(colony) > 11:
      await ctx.send("There can only be colonies between 1 and 11")
      return
    
  warpoints = {
      "1": 100,
      "2": 200,
      "3": 300,
      "4": 400,
      "5": 600,
      "6": 1000,
      "7": 1500,
      "8": 2000,
      "9": 2500
  }

  ctemp = "C" + colony
  war = await loadJson("./war_info.json")
  claim = await loadJson("./claim.json")
  #members_list = await loadJson("./members.json")
 
  special_names = {
    "ming_miw":"miw",
    "kuxuku_":"kuxaku",
    "pawel5142":"pawelcio123",
    "_temucin_":"cerdukay",
    "TahiaDjazair213algerCentre#8475":"cornflekssz",
    "szalonylukaszek69":"bonvsko",
    "kexsik777_29868":"0770",
    "eovcom1x": "eovcomix",
    "MP furry#0675":"nigkiip",
    "ahmed_real.":"ahmedwaheed2002"
  }
  
  lower_case_members = {
      key.lower(): value
      for key, value in war["members"].items()
  }
  existance = True

  if enemy.lower() in lower_case_members:
    lower_enemy = enemy.lower()
    for key, value in war["members"].items():
      if key.lower() == lower_enemy:
        enemy = key
    
    if ctemp in war["members"][enemy]:
       war["members"][enemy][ctemp][0] = datetime.now().strftime(
          "%Y-%m-%d %H:%M:%S")
       for key,value in claim["members"].items():
          if value[2] == enemy:
             value[0] = "no lock"
             value[1] = 0
             value[2] = "enemy"
             value[3] = 0
             
       await saveJson("./war_info.json", war)
       if colony == "0":
         await ctx.send("**" + enemy + "** **main** Down")
       else:
         await ctx.send("**" + enemy + "** **" + ctemp + "** Down")
    else:
       existance = False
       await ctx.send("The enemy colony does not exist!")

    #if existance == True: 
          # start of scores
          #planet = war["members"][enemy][ctemp][2]
          #SB_level = planet[2]
          #points = warpoints[SB_level]
          #name = ctx.author.name
  
          #for key,value in special_names.items():
            #if key == name:
              #name = value
  
          #for key, value in members_list["members"].items():
            #if key.lower() == name:
              #value["points"] += points
              #value["totalpoints"] += points
          #await saveJson("./members.json", members_list)
          # end of scores
            #break

  else:
    await ctx.send("The enemy does not exist!")

@bot.command()
async def unknown(ctx, enemy=None, colony="0"):
  '''
  if ctx.author.id != garyID and ctx.author.id != evoID and ctx.author.id != catID:
    await ctx.send("The command is under maintenance, notify the dev's")
    return
  '''
  if enemy is None:
    await ctx.send("Please write the enemy name!")
    return

  if colony != "0":
    if int(colony) < 1 or int(colony) > 11:
      await ctx.send("There can only be colonies between 1 and 11")
      return

  ctemp = "C" + colony
  war = await loadJson("./war_info.json")
  lower_case_members = {
      key.lower(): value
      for key, value in war["members"].items()
  }

  if enemy.lower() in lower_case_members:
    lower_enemy = enemy.lower()
    for key, value in war["members"].items():
      if key.lower() == lower_enemy:
        enemy = key
        break

    if ctemp in war["members"][enemy]:
      war["members"][enemy][ctemp][0] = "unknown"
      
      
      await saveJson("./war_info.json", war)
      if colony == "0":
        await ctx.send("**" + enemy + "** **main** down time unkown")
      else:
        await ctx.send("**" + enemy + "** **" + ctemp + "** down time unknown")
    else:
      await ctx.send("The enemy colony does not exist!")
  else:
    await ctx.send("The enemy does not exist!")


@bot.command()
async def up(ctx, enemy=None, colony="0"):
  if enemy is None:
    await ctx.send("Please write the enemy name!")
    return

  if colony != "0":
    if int(colony) < 1 or int(colony) > 11:
      await ctx.send("There can only be colonies between 1 and 11")
      return
    
  war = await loadJson("./war_info.json")
  lower_case_members = {
    key.lower(): value
    for key, value in war["members"].items()
  }

  if enemy.lower() in lower_case_members:
    lower_enemy = enemy.lower()
    for key, value in war["members"].items():
      if key.lower() == lower_enemy:
        enemy = key
        break  
  ctemp = "C" + colony
  
  if enemy in war["members"]:
    if ctemp in war["members"][enemy]:
      war["members"][enemy][ctemp][0] = "0"
      await saveJson("./war_info.json", war)
      if colony == "0":
        await ctx.send("**" + enemy + "** **main** Up")
      else:
        await ctx.send("**" + enemy + "** **" + ctemp + "** Up")
    else:
      await ctx.send("The enemy colony does not exist!")
  else:
    await ctx.send("The enemy does not exist!!")

@bot.command()
async def upAll(ctx, enemy=None):
  if enemy is None:
    await ctx.send("Please write the enemy name!")
    return
    
  war = await loadJson("./war_info.json")
  lower_case_members = {
    key.lower(): value
    for key, value in war["members"].items()
  }

  if enemy.lower() in lower_case_members:
    lower_enemy = enemy.lower()
    for key, value in war["members"].items():
      if key.lower() == lower_enemy:
        enemy = key
        break  
  
  if enemy in war["members"]:
      for colony, values in war["members"][enemy].items():
            values[0] = "0"
      await saveJson("./war_info.json", war)
      await ctx.send(f"All planets of **{enemy}** are up!")
  else:
      await ctx.send("The enemy does not exist!")


# @bot.command()
# async def upgraded(ctx, starbaselvl=None):
#   if starbaselvl is None:
#     await ctx.send("Please write your new starbase level!")
#     return
#   if int(starbaselvl) < 1 or int(starbaselvl) > 9:
#     await ctx.send("There can only be starbases between 1 and 9")
#     return
#   points = await loadJson("./total_wp.json")
#   warpoints_added = {
#       "2": 100,
#       "3": 100,
#       "4": 100,
#       "5": 200,
#       "6": 400,
#       "7": 500,
#       "8": 500,
#       "9": 500
#   }
#   new_points = warpoints_added[starbaselvl]
#   points["total_wp"] += new_points
#   await ctx.send(f"Total warpoints of our alliance increased by {new_points}!")
#   await saveJson("./total_wp.json", points)


# @bot.command()
# async def add(ctx, starbaselvl=None):
#   if starbaselvl is None:
#     await ctx.send("Please write your new starbase level!")
#     return
#   if int(starbaselvl) < 1 or int(starbaselvl) > 9:
#     await ctx.send("There can only be starbases between 1 and 9")
#     return
#   points = await loadJson("./total_wp.json")
#   warpoints_added = {
#       "2": 200,
#       "3": 300,
#       "4": 400,
#       "5": 600,
#       "6": 1000,
#       "7": 1500,
#       "8": 2000,
#       "9": 2500
#   }
#   new_points = warpoints_added[starbaselvl]
#   points["total_wp"] += new_points
#   await ctx.send(f"Total warpoints of our alliance increased by {new_points}!")
#   await saveJson("./total_wp.json", points)

@bot.command()
async def refreshMainWp(ctx):
    galacticEmpire_wp_sum = 0
    try:
      response = requests.get(f"https://api.galaxylifegame.net/Alliances/get?name=galactic%20empire%20II")
      data = response.json()
      if 'Members' in data:
          members = data['Members']
          member_names = [member['Name'] for member in members]
          warpoints = {
                    1: 100,
                    2: 200,
                    3: 300,
                    4: 400,
                    5: 600,
                    6: 1000,
                    7: 1500,
                    8: 2000,
                    9: 2500
                }
          for member in member_names:
              response = requests.get(f"https://api.galaxylifegame.net/Users/name?name={member}")
              user_data = response.json()
              HQlevel = user_data['Planets'][0]["HQLevel"]
              if HQlevel in warpoints:
                  points = warpoints[HQlevel]
                  galacticEmpire_wp_sum += points
          main_wp = await loadJson("./total_wp.json")
          main_wp["total_wp"] = galacticEmpire_wp_sum
          await saveJson("./total_wp.json", main_wp)
        
      else:
          print("No member data found in the API response.")
    except Exception as e:
        print(f"An error occurred: {e}")

@bot.command()
async def info(ctx):
  war = await loadJson("./war_info.json")
  points = await loadJson("./total_wp.json")
  # total sum of all our starbase levels combined
  GalacticEmpire_wp_sum = points["total_wp"]

  # total sum of all starbase levels combined of the enemy alliance
  EnemyAlliance_wp_sum = 0

  warpoints = {
      1: 100,
      2: 200,
      3: 300,
      4: 400,
      5: 600,
      6: 1000,
      7: 1500,
      8: 2000,
      9: 2500
  }
  counter = 0
  for player, player_data in war["members"].items():
    if "C0" in player_data:
      sb_value = int(player_data["C0"][2][2:])
      counter += 1
      EnemyAlliance_wp_sum += warpoints.get(sb_value, 0)

  regenTime = (3*EnemyAlliance_wp_sum)/GalacticEmpire_wp_sum
  # print(regenTime)
  base_value = int(regenTime)
  # print(base_value)
  border_for_rounding = base_value + 0.9
  # print(border_for_rounding)
  if regenTime < border_for_rounding:
    actualRegenTime = base_value
  else:
    actualRegenTime = base_value + 1
  # RegenFactor = EnemyAlliance_wp_sum / GalacticEmpire_wp_sum
  # # default regen time in wars is 3h
  # regenTime = 3
  # memberRatio = counter/18
  # memberTime = 3*memberRatio # respawn time based on members
  # if memberTime < 3:
  #   memberTime = 3
  # elif memberTime > 7:
  #   memberTime = 7
  # # calculate the actual regeneration time for a base
  # actualRegenTimeV1 = regenTime * RegenFactor # with no member consideration
  # actualRegenTime = round((actualRegenTimeV1 + memberTime)/2) # take average of both times
  # # actualRegenTime = round(regenTime * RegenFactor)
  if actualRegenTime < 3:
    actualRegenTime = 3
  elif actualRegenTime > 7:
    actualRegenTime = 7
  # actualRegenTime = 3
  print(actualRegenTime)

  global regentime
  if regentime != 0:
    actualRegenTime = regentime
  
  embed = discord.Embed(
      title=war["name"],
      description=
      f"Total WP main:{EnemyAlliance_wp_sum}, Rebuild time:{actualRegenTime}",
      color=discord.Colour.from_rgb(0,0,0))
  currentTime = datetime.now()

  claim = await loadJson("./claim.json")

  if len(war["members"]) <= 25:
    for member in war["members"]:
      text = ""
      for planet in war["members"][member]:

        # checking if time is unknown
        if war["members"][member][planet][0] == "unknown":
            starbaselvl = war["members"][member][planet][2]
            if planet== "C0":
              text += f":warning: main {starbaselvl}-> ????\n"
              continue
            else:
              coords = war["members"][member][planet][1]
              text += f":warning: {planet} {coords} {starbaselvl}-> ????\n"
              continue

        if war["members"][member][planet][0] == "0":
          # get the starbase lvl from position 2
          starbaselvl = war["members"][member][planet][2]
          if planet == "C0":

            # check for claims
            claimed = False
            for key,value in claim["members"].items():
               if member == value[2] and value[0] == "claimed" and value[3] == "C0":
                  text += f":lock: main  {starbaselvl}-> UP\n"
                  claimed = True
            if claimed == False:
              text += f":white_check_mark: main  {starbaselvl}-> UP\n"

          else:
            coords = war["members"][member][planet][1]
            for key,value in claim["members"].items():
               if war["members"][member] == value[2] and value[0] == "claimed" and value[3] == planet:
                  text += f":lock: {planet} {coords} {starbaselvl}-> UP\n"
                  claimed = True

            if claimed == False:
              text += f":white_check_mark: {planet} {coords} {starbaselvl}-> UP\n"
          continue

        tempTime = war["members"][member][planet][0]
        tempTime = datetime.strptime(tempTime, "%Y-%m-%d %H:%M:%S")

        timeDifference = currentTime - tempTime
        # added the actualRegenTime instead of the hard coded 3h time
        if timeDifference >= timedelta(hours=actualRegenTime):
          war["members"][member][planet][0] = "0"
          # get the starbase lvl from position 2
          starbaselvl = war["members"][member][planet][2]

          if planet == "C0":
            claimed = False
            for key,value in claim["members"].items():
               if war["members"][member] == value[2] and value[0] == "claimed" and value[3] == "C0":
                  text += f":lock: main  {starbaselvl}-> UP\n"
                  claimed = True

            if claimed == False:
              text += f":white_check_mark: main {starbaselvl}-> UP\n"
          else:
            starbaselvl = war["members"][member][planet][2]
            coords = war["members"][member][planet][1]
            claimed = False
            for key,value in claim["members"].items():
               if war["members"][member] == value[2] and value[0] == "claimed" and value[3] == planet:
                  text += f":lock: {planet} {coords} {starbaselvl}-> UP\n"
                  claimed = True

            if claimed == False:
              text += f":white_check_mark: {planet} {coords} {starbaselvl}-> UP\n"
        else:
          # added the actualRegenTime instead of the hard coded 3h time
          timeLeft = timedelta(hours=actualRegenTime) - timeDifference
          hoursLeft = timeLeft.seconds // 3600
          minutesLeft = (timeLeft.seconds % 3600) // 60

          ptemp = ":octagonal_sign: " + planet
          coords = war["members"][member][planet][1]
          # get the starbase lvl from position 2
          starbaselvl = war["members"][member][planet][2]


          if planet == "C0":

            claimed = False
            for key,value in claim["members"].items():
                if war["members"][member] == value[2] and value[0] == "claimed" and value[3] == "C0":
                  ptemp = ":lock: main"
                  coords = ""
                  claimed = True

            if claimed == False:
              ptemp = ":octagonal_sign: main"
              coords = ""

          
          for key,value in claim["members"].items():
              if war["members"][member] == value[2] and value[0] == "claimed" and value[3] == planet:
                ptemp = ":lock:" + planet

          # added starbaselvl in the display
          text += f"{ptemp} {coords} {starbaselvl}-> {hoursLeft}h:{minutesLeft}m\n"

      embed.add_field(name=member, value=text, inline=True)

    embed.set_footer(text="Developed by Garybaldy16")
    await saveJson("./war_info.json", war)
    await ctx.send(embed=embed)

  else:
    max_members_per_embed = 25

    # Calculate the total number of members
    total_members = len(war["members"])

    # Iterate over members in chunks of max_members_per_embed
    for start_index in range(0, total_members, max_members_per_embed):
      end_index = start_index + max_members_per_embed
      current_members = list(war["members"].items())[start_index:end_index]

      embed = discord.Embed(
          title=war["name"],
          description=
          f"Total WP main:{EnemyAlliance_wp_sum}, Rebuild time:{actualRegenTime}",
          color=discord.Colour.from_rgb(0,0,0))

      for member, member_data in current_members:
        text = ""
        for planet in member_data:

            # checking if time is unknown
          if war["members"][member][planet][0] == "unknown":
              starbaselvl = war["members"][member][planet][2]
              if planet== "C0":
                text += f":warning: main {starbaselvl}-> ????\n"
                continue
              else:
                coords = war["members"][member][planet][1]
                text += f":warning: {planet} {coords} {starbaselvl}-> ????\n"
                continue

          if war["members"][member][planet][0] == "0":
            # get the starbase lvl from position 2
            starbaselvl = war["members"][member][planet][2]
            if planet == "C0":
              text += f":white_check_mark: main  {starbaselvl}-> UP\n"
            else:
              coords = war["members"][member][planet][1]
              text += f":white_check_mark: {planet} {coords} {starbaselvl}-> UP\n"
            continue

          tempTime = war["members"][member][planet][0]
          tempTime = datetime.strptime(tempTime, "%Y-%m-%d %H:%M:%S")

          timeDifference = currentTime - tempTime
          # added the actualRegenTime instead of the hard coded 3h time
          if timeDifference >= timedelta(hours=actualRegenTime):
            war["members"][member][planet][0] = "0"
            # get the starbase lvl from position 2
            starbaselvl = war["members"][member][planet][2]
            if planet == "C0":
              text += f":white_check_mark: main {starbaselvl}-> UP\n"
            else:
              coords = war["members"][member][planet][1]
              # get the starbase lvl from position 2
              starbaselvl = war["members"][member][planet][2]
              # added the starbaselvl in the display
              text += f":white_check_mark: {planet} {coords} {starbaselvl}-> UP\n"
          else:
            # added the actualRegenTime instead of the hard coded 3h time
            timeLeft = timedelta(hours=actualRegenTime) - timeDifference
            hoursLeft = timeLeft.seconds // 3600
            minutesLeft = (timeLeft.seconds % 3600) // 60

            ptemp = ":octagonal_sign: " + planet
            coords = war["members"][member][planet][1]
            # get the starbase lvl from position 2
            starbaselvl = war["members"][member][planet][2]
            if planet == "C0":
              ptemp = ":octagonal_sign: main"
              coords = ""

            # added starbaselvl in the display
            text += f"{ptemp} {coords} {starbaselvl}-> {hoursLeft}h:{minutesLeft}m\n"

        embed.add_field(name=member, value=text, inline=True)

      embed.set_footer(text="Developed by Garybaldy16")
      await saveJson("./war_info.json", war)
      await ctx.send(embed=embed)


# keep_alive.keep_alive()

# try:
#   bot.run(token)
# except Exception as e:
#   print(f"An error occurred: {type(e).__name__} - {e}")

#   # Create a dictionary with error information
#   error_data = {"error_type": type(e).__name__, "error_message": str(e)}

#   # Run the asynchronous task outside of an async function
#   bot.loop.run_until_complete(write_error_to_json(error_data))

#   asyncio.run(bot.close())  # Close the bot
#   # Add a delay before attempting to restart
#   asyncio.run(asyncio.sleep(5))
#   # Restart the bot
#   bot.loop.run_until_complete(bot.start(token))


#RaCC0on Bot. Copyright Timothy Marshall Upper, 2023. All Rights Reserved.
#Version 2.2 - April 26, 2022

from __future__ import print_function
import os
import random
import urllib.request
import time
import discord
from discord.ext import commands
from discord import Interaction
from discord.ui import Button, View, Select
from discord.commands import Option
from discord.ext.commands import Context
from dotenv import load_dotenv
import psycopg2
import json
import requests
import datetime
import asyncio
import replicate
from io import BytesIO
from PIL import Image
from PIL import UnidentifiedImageError

from web3 import Web3

load_dotenv()

TOKEN = os.getenv('BOT_TOKEN')
DATABASETOKEN = os.getenv('DATABASE_URL')
trashCollectChannel = 1076613455357952090
raccoonGuildID = 960007772903194624

#To be honest, I don't know enough about what the below does, I just know it's what Google told me to do XD
#I would think I'm initializing a Client object, but I never call it again, so....
client = discord.Client()
#Declare the bot's intents and initialize it
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="+", intents=intents)

#Class definition to handle the shop view
class ShopView(View):
    
    def __init__(self, user_id, balance, has_backpack, has_fanny_pack):
        super().__init__(timeout = None)  # I've also added timeout = None here.
        self.user_id = user_id
        self.balance = balance
        self.has_backpack = has_backpack
        self.has_fanny_pack = has_fanny_pack

        #items
        self.backpack_price = 1500
        self.fanny_pack_price = 500

        fanny_pack_button = Button(label="Buy Fanny Pack", style=discord.ButtonStyle.blurple, custom_id="buy_fanny_pack", disabled=self.has_fanny_pack or self.balance < self.fanny_pack_price)
        fanny_pack_button.callback = self.on_button_click
        self.add_item(fanny_pack_button)

        backpack_button = Button(label="Buy Backpack", style=discord.ButtonStyle.blurple, custom_id="buy_backpack", disabled=self.has_backpack or self.balance < self.backpack_price)
        backpack_button.callback = self.on_button_click
        self.add_item(backpack_button)

    async def on_button_click(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your menu!", ephemeral=True)
            return
        item_id = interaction.data["custom_id"]
        conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
        cur = conn.cursor()
        if item_id == "buy_backpack":
            cur.execute("update raccooncollect set backpack = True where discord_user_id = {0}".format(interaction.user.id))
            self.balance = self.balance - self.backpack_price
            cur.execute("update raccooncollect set balance = {0} where discord_user_id = {1}".format(self.balance, interaction.user.id))
            item = "backpack"
        elif item_id == "buy_fanny_pack":
            cur.execute("update raccooncollect set fannypack = True where discord_user_id = {0}".format(interaction.user.id))
            self.balance = self.balance - self.fanny_pack_price
            cur.execute("update raccooncollect set balance = {0} where discord_user_id = {1}".format(self.balance, interaction.user.id))
            item = "fanny pack"

        cur.close()
        conn.commit()
        conn.close()

        await interaction.response.send_message("You bought a " + item + "!", ephemeral=True)

class ImagesView(View):
    def __init__(self, images):
        super().__init__(timeout = None)
        self.images = images

        for i in range(4):
            # Add callback function for each button
            button = Button(style=discord.ButtonStyle.primary, label=f"Image {i+1}", custom_id=f"image_{i}")
            button.callback = self.on_button_click
            self.add_item(button)

    async def on_button_click(self, interaction: Interaction):
        # Find the image number from the button's custom_id
        image_number = int(interaction.data["custom_id"].split('_')[1])

        # Open and send the corresponding image
        image_data = BytesIO()
        self.images[image_number].save(image_data, format='PNG')
        image_data.seek(0)
        file = discord.File(fp=image_data, filename=f'image_{image_number}.png')

        await interaction.response.send_message(content = "", file=file)    


#Defines the collect slash command
@bot.slash_command(guild_ids=[raccoonGuildID], description = "Collect trash")
async def collect(ctx):
    if ctx.channel.id != trashCollectChannel:
        return

    #set constant variables
    userCollectCooldown = 50
    fannyPackTrash = 150
    backPackTrash = .5

    interaction = True
    if str(type(ctx)) == "<class 'discord.commands.context.ApplicationContext'>":
        member = ctx.author
        interaction = False
    else:
        member = ctx.user

    view = View()
    view.clear_items()

    async def collectButton_callback(interaction):
        await collect(interaction)

    collectButton = Button(label="Collect Again", style = discord.ButtonStyle.blurple)
    collectButton.callback = collectButton_callback

    outcome = random.randint(1,100)
    conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
    cur = conn.cursor()
    command = "select * from raccooncollect where discord_user_id = {0}".format(member.id)
    cur.execute(command)
    status = cur.fetchall()
    if status == []:
        command = "insert into raccooncollect (discord_user_id, balance, cooldown_time, collect_cooldown_time) values ({0}, 0, {1}, {2})".format(member.id, int(time.time()), int(time.time()*10))
        cur.execute(command)
        conn.commit()
        account = member.id
        balance = 0
        eligibleToClaim = int(time.time())
        collectCooldown = int(time.time()*10)
        fannyPack = False
        backpack = False
    else:
        account = status[0]
        eligibleToClaim = account[1]
        balance = account[2]
        collectCooldown = account[4]
        fannyPack = account[5]
        backpack = account[6]
    embed = discord.Embed(color=0x000000)
    if eligibleToClaim <= int(time.time()):
        currentTime = int(time.time()*10)
        if collectCooldown <= currentTime:
            if outcome > 90:
                embed.description = "<@" + str(member.id) + ">, you were spotted by the restaurant owner! You drop all your trash and flee."
                safeBalance = 0
                #If the user has a fanny pack, then move some trash from their total balance to their safe balance
                if fannyPack:
                    if balance <= fannyPackTrash:
                        safeBalance = balance
                        balance = 0
                    else:
                        safeBalance = fannyPackTrash
                        balance = balance - fannyPackTrash
                #If the user has a backpack, then move some trash from their total balance to their safe balance
                if backpack:
                    balanceToSave = int(balance * backpackTrash)
                    safeBalance = safeBalance + balanceToSave
                    balance = balance - balanceToSave
                if interaction:
                    await ctx.response.send_message(embed = embed, view = view)
                else:
                    await ctx.respond(embed = embed, view = view)
                await ctx.channel.send("https://tenor.com/view/raccoon-escape-viralhog-running-away-fail-fall-gif-17821787")
                command = "update raccooncollect set balance = {0} where discord_user_id = {1}".format(safeBalance, member.id)
                cur.execute(command)
                conn.commit()
                command = "update raccooncollect set cooldown_time = {0} where discord_user_id = {1}".format(int(time.time())+10800,member.id)
                cur.execute(command)
                conn.commit()
            else:
                maxSalt = int(balance/10)
                if maxSalt < 15:
                    maxSalt = 15
                saltFound = random.randint(maxSalt-10,maxSalt)
                newBalance = balance + saltFound
                command = "update raccooncollect set balance = {0} where discord_user_id = {1}".format(newBalance,member.id)
                cur.execute(command)
                command = "update raccooncollect set collect_cooldown_time = {0} where discord_user_id = {1}".format(currentTime+50,member.id)
                cur.execute(command)
                conn.commit()
                embed.description = "<@" + str(member.id) + ">, you collected " + str(saltFound) + " pieces of trash. You now have " + str(newBalance) + "."
                view.add_item(collectButton)
                if interaction:
                    await ctx.response.send_message(embed = embed, view = view)
                else:
                    await ctx.respond(embed = embed, view = view)
        else:
            timeRemaining = round(((collectCooldown - currentTime)/10.0),1)
            embed.description = "You must wait **{0}**s before collecting again.\nYour cooldown: **{1}**s".format(str(timeRemaining), str(round(userCollectCooldown/10.0,1)))
            view.clear_items()
            if interaction:
                await ctx.response.send_message(embed = embed, view = view, ephemeral = True)
            else:
                await ctx.respond(embed = embed, view = view, ephemeral = True)
    else:
        embed.description = "<@" + str(member.id) + ">, you are still recovering. Try again <t:" + str(eligibleToClaim) +":R>."
        if interaction:
            await ctx.response.send_message(embed = embed, view = view, ephemeral = True)
        else:
            await ctx.respond(embed = embed, view = view, ephemeral = True)
    cur.close()
    conn.commit()
    conn.close()
    #Get the current list of avatars to see if the leaderboard needs to be updated
    conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
    command = "select * from raccooncollect"
    cur = conn.cursor()
    cur.execute(command)
    searchResult = cur.fetchall()
    cur.close()
    conn.close()
    #Sort the list of avatars by EXP descending
    listOfAvatars = []
    for avatar in searchResult:
        listOfAvatars.append([avatar[2],avatar[0]])
    listOfAvatars.sort(reverse=True)
    #See if either participating avatar is in the top 10 EXP leaderboard. If so, we need to update it.
    i = 0
    iMax = len(listOfAvatars)
    if iMax > 10:
        iMax = 10
    leaderboardUpdate = False
    if outcome > 90:
        leaderboardUpdate = True
    while i < iMax and leaderboardUpdate == False:
        if listOfAvatars[i][1]==member.id:
            leaderboardUpdate=True
        i+=1
    if leaderboardUpdate:
        channel = discord.utils.get(ctx.guild.channels, id=1076615144672591962)
        i = 0
        leaderboardString = ""
        while i < iMax:
            leaderboardString += "<@" + str(listOfAvatars[i][1]) + "> - " + str(listOfAvatars[i][0]) + " pieces of trash\n"
            i+=1
        #Clear the EXP Leaderboard channel and send the new top 10
        await channel.purge()
        embed = discord.Embed(description = leaderboardString, color=0x000000)
        await channel.send(embed = embed)

# Add this function after your 'collect' function
@bot.slash_command(guild_ids=[raccoonGuildID], description="Visit the shop")
async def shop(ctx: Context):
    # Retrieve the user's balance and whether they own a backpack or fanny pack
    conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
    cur = conn.cursor()
    command = "select * from raccooncollect where discord_user_id = {0}".format(ctx.author.id)
    cur.execute(command)
    status = cur.fetchall()
    cur.close()
    conn.close()

    if status:
        balance = status[0][2]
        has_backpack = status[0][6] 
        has_fanny_pack = status[0][5]
    else:
        balance = 0
        has_backpack = False
        has_fanny_pack = False

    # Create the shop embed and custom view
    embed = discord.Embed(title="Shop", description="Buy items to improve your trash collecting abilities! Item buffs stack.", color=0x000000)
    embed.add_field(name="Fanny Pack", value="Price: 500\nThe fanny pack can hold up to 150 pieces of trash, so even if you get caught, you get to bring some trash home!")
    embed.add_field(name="Backpack", value="Price: 1500\nThe backpack has even more room for trash - if you get caught, you still bring home half of your collected trash!")
    
    view = ShopView(ctx.author.id, balance, has_backpack, has_fanny_pack)
    await ctx.respond(embed=embed, view=view)

#This command resets a user's cooldown for testing or troubleshooting purposes
@bot.slash_command(guild_ids=[raccoonGuildID], description = "Reset a user's cooldown.")
async def resetcooldown(ctx, user: Option(discord.Member, "Whose cooldown do you want to reset?")):
    guild = bot.get_guild(raccoonGuildID)
    #if the user isn't tupper, don't let them run the command
    if ctx.author.id != 710139786404298822:
        response = random.randint(1,5)
        if response == 1:
            await ctx.respond("https://tenor.com/view/nice-try-saturday-night-live-good-try-nice-attempt-nice-shot-gif-25237563")
        if response == 2:
            await ctx.respond("https://tenor.com/view/nice-try-kid-frank-gallagher-william-macy-shameless-nice-one-gif-16165992")
        if response == 3:
            await ctx.respond("https://tenor.com/view/parks-and-rec-bobby-newport-nice-try-laughs-laughing-gif-21862350")
        if response == 4:
            await ctx.respond("https://tenor.com/view/nice-try-jack-donaghy-30rock-good-try-try-again-gif-21903632")
        if response == 5:
            await ctx.respond("https://tenor.com/view/nicetry-lawyer-harveyspecter-gif-4755413")
        return
    
    uid = user.id
    #Connect to the database and reset the cooldown
    conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
    cur = conn.cursor()
    command = "update raccooncollect set cooldown_time = {0} where discord_user_id = {1}".format(int(time.time()), uid)
    cur.execute(command)
    cur.close()
    conn.commit()
    conn.close()
    await ctx.respond(user.mention + "'s cooldown has been reset!")

#Replicate API call is defined as a function here so it can be run asynchronously later
def run_replicate(prompt):
    return replicate.run(
        "doriancollier/raccoon1:831081aba81a2194d5a003eb225d8b2f33b435b6948a3038ca507aa71866abe8",
        input={"prompt": prompt, "num_outputs": 4, "height": 512, "width": 512}
    )

#Defines the clone slash command
@bot.slash_command(guild_ids=[raccoonGuildID], description="Generate a RaCC0on clone")
async def clone(ctx, prompt: Option(str, "Describe the RaCC0on clone you'd like to generate")):
    originalPrompt = prompt
    prompt = "racc0ons, full_body, " + prompt
    assignmentView = View(timeout=None)
    #Let the user know the request has been received
    message1 = await ctx.respond("**Loading...**")
    message2 = await ctx.channel.send("https://tenor.com/view/raccoon-gif-5614710")
    message3 = await ctx.channel.send("This could take up to 5 minutes.")

    #These are static pngs I've used for testing, and I keep them here just in case
    '''
    output = [
        'https://www.iconsdb.com/icons/preview/black/square-xxl.png',
        'https://www.cac.cornell.edu/wiki/images/4/44/White_square.png',
        'https://i.ibb.co/0sF1B1W/blue-square.png',
        'https://upload.wikimedia.org/wikipedia/commons/9/9b/Greensquare.png'
    ]
    '''
    output = await asyncio.to_thread(run_replicate, prompt)

    # Load the images and store them in a list
    images = []
    for url in output:
        try:
            images.append(Image.open(BytesIO(requests.get(url).content)))
        except UnidentifiedImageError:
            print(f"Cannot identify image file at URL: {url}")

     # Create a new image to combine the four images
    combined_image = Image.new('RGB', (images[0].width * 2, images[0].height * 2))

    # Paste the images onto the new image
    combined_image.paste(images[0], (0, 0))
    combined_image.paste(images[1], (images[0].width, 0))
    combined_image.paste(images[2], (0, images[0].height))
    combined_image.paste(images[3], (images[0].width, images[0].height))

    # Save the combined image to a BytesIO object
    image_data = BytesIO()
    combined_image.save(image_data, format='PNG')
    image_data.seek(0)

    # Upload the image to Discord as an attachment
    image_file = discord.File(fp=image_data, filename='combined_image.png')
    response = await message1.edit_original_message(content = "**" + originalPrompt + "**\n", file=image_file)
    button_view = ImagesView(images)
    await message2.edit(content="Click a button to see the corresponding image full-size:", view=button_view)

    # Get the necessary IDs
    server_id = ctx.guild.id
    channel_id = ctx.channel.id
    message_id = response.id

    # Create the jump URL
    jump_url = f"https://discord.com/channels/{server_id}/{channel_id}/{message_id}"

    #Ping the user and let them know their images are ready and include the jump url. 
    await ctx.channel.send(f"{ctx.author.mention}, 4 results are ready! Jump to Message --> {jump_url}")

    #Delete the "this could take up to 5 minutes message to keep the channel clean.
    await message3.delete()                

#Runs the bot using the TOKEN defined in the environmental variables.         
bot.run(TOKEN)

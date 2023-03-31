#RaCC0on Bot. Copyright Timothy Marshall Upper, 2023. All Rights Reserved.
#Version 2.0 - March 30, 2022

from __future__ import print_function
import os
import random
import urllib.request
import time
import discord
from discord.ext import commands
from discord.ui import Button, View, Select
from discord.commands import Option
from dotenv import load_dotenv
import psycopg2
import json
import requests
import datetime
import asyncio
import replicate

from web3 import Web3

load_dotenv()

TOKEN = "MTA3NTQ2MTkyODc3Mzc0NjczOA.Gj5IzS.BtZKoVJeABzYfJ753ayEvTsBjTp0EwtwhWOsuo" #os.getenv('NIFTYS_BOT_TOKEN')
DATABASETOKEN = "postgres://udccp1sgn1f3bd:p11806fcba44af233f288b1c19a92b5eb09b3e3270c7bdf8106f3456445d59c52@ec2-34-193-55-145.compute-1.amazonaws.com:5432/d5id2nagt1gcg6" #os.getenv('DATABASE_URL')

#To be honest, I don't know enough about what the below does, I just know it's what Google told me to do XD
#I would think I'm initializing a Client object, but I never call it again, so....
client = discord.Client()
#This one tells the bot to look for commands that start with ! (ie. !fight)
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="+", intents=intents)

#Defines the collect slash command
@bot.slash_command(guild_ids=[960007772903194624], description = "Collect trash")
async def collect(ctx):
    if ctx.channel.id != 1076613455357952090:
        return

    userCollectCooldown = 50

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
    else:
        account = status[0]
        eligibleToClaim = account[1]
        balance = account[2]
        collectCooldown = account[4]
    embed = discord.Embed(color=0x000000)
    if eligibleToClaim <= int(time.time()):
        currentTime = int(time.time()*10)
        if collectCooldown <= currentTime:
            if outcome > 90:
                embed.description = "<@" + str(member.id) + ">, you were spotted by the restaurant owner! You drop all your trash and flee."
                if interaction:
                    await ctx.response.send_message(embed = embed, view = view)
                else:
                    await ctx.respond(embed = embed, view = view)
                await ctx.channel.send("https://tenor.com/view/raccoon-escape-viralhog-running-away-fail-fall-gif-17821787")
                command = "update raccooncollect set balance = 0 where discord_user_id = {0}".format(member.id)
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

@bot.slash_command(guild_ids=[960007772903194624], description = "Reset a user's cooldown.")
async def resetcooldown(ctx, user: Option(discord.Member, "Whose cooldown do you want to reset?")):
    guild = bot.get_guild(960007772903194624)
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
    conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
    cur = conn.cursor()
    command = "update raccooncollect set cooldown_time = {0} where discord_user_id = {1}".format(int(time.time()), uid)
    cur.execute(command)
    cur.close()
    conn.commit()
    conn.close()
    await ctx.respond(user.mention + "'s cooldown has been reset!")

def run_replicate(prompt):
    return replicate.run(
        "doriancollier/raccoon1:831081aba81a2194d5a003eb225d8b2f33b435b6948a3038ca507aa71866abe8",
        input={"prompt": prompt}
    )

#Defines the clone slash command
@bot.slash_command(guild_ids=[960007772903194624], description = "Generate a RaCC0on clone")
async def clone(ctx, prompt: Option(str, "Describe the RaCC0on clone you'd like to generate")):
    originalPrompt = prompt
    prompt = "racc0ons, full_body, " + prompt
    assignmentView = View(timeout = None)
    assignmentEmbed = discord.Embed(color = 0x000000)
    assignmentEmbed.title = "Loading..."
    assignmentEmbed.description = "This could take up to 5 minutes."
    message = await ctx.respond(embed = assignmentEmbed, view = assignmentView)

    #output = await asyncio.to_thread(run_replicate, prompt)
    output = ['https://images-ext-1.discordapp.net/external/Mgf4UJ0ClaO01b5F6nJA16wCUHPxDOsegO_IolMRi-c/https/replicate.delivery/pbxt/qVHemwTShB1ydqUE4KnpNXhzonSah3p3pKSCj3BhDpGtznWIA/out-0.png?width=530&height=530',
              'https://images-ext-1.discordapp.net/external/gt18GJZ7vTvYZ_bPaDCNTmO7XwEUlwkAzWl4fsdA6bY/https/replicate.delivery/pbxt/VilfLcywetr7vk8eCPMGvDtP9456DnwwtgON4Fd5AQ66Lf0CB/out-0.png?width=530&height=530']

    await ctx.send(ctx.author.mention + ", 4 results are given below!")
    for image in output:
        assignmentEmbed.title = originalPrompt
        assignmentEmbed.description = ""
        assignmentEmbed.set_image(url=output[0])
        await ctx.send(embed = assignmentEmbed)
        #await message.edit_original_message(embed = assignmentEmbed)
                    

#Runs the bot using the TOKEN defined in the environmental variables.         
bot.run(TOKEN)

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

@bot.command(name='collect')
async def collect(ctx):
    if ctx.channel.id != 1076613455357952090:
        return
    member = ctx.message.author
    outcome = random.randint(1,100)
    conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
    cur = conn.cursor()
    command = "select * from raccooncollect where discord_user_id = {0}".format(member.id)
    cur.execute(command)
    status = cur.fetchall()
    if status == []:
        command = "insert into raccooncollect (discord_user_id, balance, cooldown_time) values ({0}, 0, {1})".format(member.id, int(time.time()))
        cur.execute(command)
        conn.commit()
        account = member.id
        balance = 0
        eligibleToClaim = int(time.time())
    else:
        account = status[0]
        eligibleToClaim = account[1]
        balance = account[2]
    if eligibleToClaim <= int(time.time()):
        if outcome > 90:
            await ctx.send("<@" + str(member.id) + ">, you were spotted by the restaurant owner! You drop all your trash and flee.")
            await ctx.send("https://tenor.com/view/raccoon-escape-viralhog-running-away-fail-fall-gif-17821787")
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
            conn.commit()
            await ctx.send("<@" + str(member.id) + ">, you collected " + str(saltFound) + " pieces of trash. You now have " + str(newBalance) + ".")
    else:
        await ctx.send("<@" + str(member.id) + ">, you are still recovering. Try again <t:" + str(eligibleToClaim) +":R>.")
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
    

#Runs the bot using the TOKEN defined in the environmental variables.         
bot.run(TOKEN)

from asyncio.events import get_event_loop
import discord

from datetime import datetime
import pandas as pd
from otc_funcs import get_team_spending, get_player_contract, get_top_contracts
import os
from dotenv import load_dotenv

load_dotenv()

secret_key=os.environ.get('DISC_TOKEN')

class MyClient(discord.Client):

    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):
        if message.content.lower().startswith('!cap'):
            team = message.content.split(" ")[1]
            team = team.upper()

            filepath = r"C:\Users\Jordan\Desktop\overthecap_bot\team_info.csv"
            team_info = pd.read_csv(filepath)

            team_cap = get_team_spending(team)
            my_embed = discord.Embed(
                title=team_cap['nickname'],
                url=team_cap['url'],
                description="",
                color=team_cap['primary_color']
            )
            my_embed.set_thumbnail(url=team_cap['image_url'])
            my_embed.add_field(name='Cap Space',
                            value=team_cap['cap_space'], inline=False)
            my_embed.add_field(name="Top Paid Players", value='\n'.join(
                [entry['Player'] + ": " + entry['CapNumber'] for entry in team_cap['players']]))
            my_embed.add_field(name="Positional Breakdown",
                            value=f"> Offense: {team_cap['positional_spending']['Offense']}\n > Defense: {team_cap['positional_spending']['Defense']}\n > Special: {team_cap['positional_spending']['Special']}")
            my_embed.set_footer(text='Cap information accessed from Over The Cap.')

            await message.channel.send(embed=my_embed)

        if message.content.lower().startswith('!contracts'):
            position = message.content.split(" ")[1]
            position_contracts = get_top_contracts(position)
            my_embed = discord.Embed(
                title=position,
                description=""
            )
            my_embed.add_field(name="Top Paid Players", value='\n'.join(
                [entry['Player'] + '—' + entry['Contract'] for entry in position_contracts]))

            await message.channel.send(embed=my_embed)

            print(position)
        
        elif message.content.lower().startswith('!contract'):
            contents = message.content.split(" ")
            player = " ".join(contents[1:-1])
            team = contents[-1]

            player_contract = get_player_contract(player, team)

            my_embed = discord.Embed(
                title=player.title(),
                url=player_contract['URL'],
                description=""
            )
            my_embed.set_thumbnail(url='https://overthecap.com/images/otc-logo.png')

            today = datetime.today()
            current_year = today.year

            my_embed.add_field(
                name=f"**Bio**", value=f"> Team: {player_contract['Team']}\n> Position: {player_contract['Position']}\n> Age: {player_contract['Age']}\n> Experience: {player_contract['Accrued Seasons']}\n> Drafted: {player_contract['Entry']}\n> FA: {player_contract['Free Agency']}", inline=False)
            if player_contract['FA'] == False:
                my_embed.add_field(
                    name=f"**Contract**", value=f"> Contract: {player_contract['Contract Value']}\n> Guaranteed Money: {player_contract['Fully Guaranteed Money']}\n> Contract Rank (POS): {player_contract['Contract Ranking']}\n> {current_year} Current Salary: {player_contract['Current Year Salary']}\n> {current_year} Dead Cap: {player_contract['Dead Cap']}", inline=True)
            elif player_contract['FA'] == True:
                my_embed.add_field(
                    name=f"**Contract**", value=f"> This player is currently a free agent.", inline=True)

            await message.channel.send(embed=my_embed)

client = MyClient()

client.run(secret_key)

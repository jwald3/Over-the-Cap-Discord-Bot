# Library imports

# web Scraping
import requests
import httplib2
from bs4 import BeautifulSoup, SoupStrainer

# data processing
import pandas as pd
import re
import json

# time processing
from datetime import datetime


# utility functions

# convert dollar figures to integer values
def dollars_to_int(dollars):
    dollars = dollars.strip('$')
    dollars = dollars.replace(',', '')
    dollars = int(dollars)
    return dollars


# convert name string into a standardized form
def parse_name(name):
    name = name.lower()
    split_name = name.split(' ')

    for i in range(len(split_name)):
        split_name[i] = split_name[i].replace("-", " ")
        split_name[i] = split_name[i].replace("'", " ")
        split_name[i] = split_name[i].replace(".", " ")
        split_name[i] = split_name[i].strip()

    edited_name = ' '.join(split_name)

    return edited_name


# Take dollars and convert to simplified string

def parse_dollars(dollars):
    dollars = str(dollars)

    dollars = dollars.strip('$')
    dollars = dollars.replace(',', '')
    dollars = int(dollars)

    if dollars >= 1_000_000:
        rounded_dollars = round(dollars / 1_000_000, 2)
        rounded_dollars = "$" + str(rounded_dollars) + "M"
    elif dollars > 100_000:
        rounded_dollars = int(dollars / 1000)
        rounded_dollars = "$" + str(rounded_dollars) + "K"
    else:
        rounded_dollars = '$' + str(dollars)

    return rounded_dollars


# Simplify contract to rounded figures

def parse_contract(contract):
    split_contract = contract.split(' ')

    total = parse_dollars(split_contract[0])
    apy = split_contract[1].replace('(', '')
    apy = parse_dollars(apy)

    contract_value = total + " (" + apy + ' APY)'

    return contract_value


# Simplify draft capital into more compact view

def parse_draft(entry):
    draft_reg = r'([0-9]{4}) Draft, Round (.*), #([0-9]{1,}) overall'

    try:
        entry_value = re.search(draft_reg, entry).group(
            1) + " #" + re.search(draft_reg, entry).group(2) + "." + re.search(draft_reg, entry).group(3)
    except AttributeError:
        entry_value = re.search(
            '([0-9]{4})', entry).group(1) + " UDFA"

    return entry_value


## Import reference csv that features team names in different formats as well as urls

filepath = r"C:/users/jordan\desktop/overthecap_bot/team_info.csv"

team_info = pd.read_csv(filepath)


# Returns pandas table that shows cap situations for all 32 teams

def get_league_cap():
    url = 'https://overthecap.com/salary-cap-space/'
    tables = pd.read_html(url)
    league_cap = tables[0]

    league_cap.columns = ['team', 'cap_space', 'effective_cap_space',
                          '#', 'active_cap_spending', 'dead_money']
    league_cap['team'] = league_cap['team'].str.lower()

    return league_cap


# Returns a table with contract information for a given team

def get_team_cap(team):
    url = team_info.loc[team_info['team_abbrev'] == team]['url'].values.item()
    tables = pd.read_html(url)
    table = tables[0]
    table.columns = table.columns.droplevel(1)

    return table


# Returns a list with the positional spending for a given team

def get_cap_liabilities(team):
    url = team_info.loc[team_info['team_abbrev'] == team]['url'].values.item()
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    positional_spending = soup.find(class_='positional-cap-number')

    spending = []

    for i in positional_spending.find_all('li'):
        spending.append(i.span.text)

    return spending


# Returns a JSON object for a team with their name, cap space, cap spending, dead money, and the top 5 highest paid players

def get_team_spending(team):
    cap_space = get_league_cap()
    team_name = team_info.loc[team_info['team_abbrev']
                              == team]['team_name'].values.item()
    nickname = team_info.loc[team_info['team_abbrev']
                             == team]['nickname'].values.item()

    if nickname == 'football team':
        nickname = 'washington'

    cap_spending = get_team_cap(team)
    positional_spending = get_cap_liabilities(team)

    team_dict = dict()

    team_dict['nickname'] = team_name
    team_dict['cap_space'] = cap_space.loc[cap_space['team']
                                           == nickname]['cap_space'].item()
    team_dict['active_cap_spending'] = cap_space.loc[cap_space['team']
                                                     == nickname]['active_cap_spending'].item()
    team_dict['dead_money'] = cap_space.loc[cap_space['team']
                                            == nickname]['dead_money'].item()
    team_dict['players'] = cap_spending[['Player', 'CapNumber',
                                         'Guaranteed Salary']].head().to_dict(orient='records')
    team_dict['positional_spending'] = positional_spending
    team_dict['image_url'] = team_info.loc[team_info['team_abbrev']
                                           == team]['image_url'].values.item()
    team_dict['url'] = team_info.loc[team_info['team_abbrev']
                                     == team]['url'].values.item()
    team_dict['primary_color'] = team_info.loc[team_info['team_abbrev']
                                               == team]['primary_color'].values.item()
    team_dict['primary_color'] = int(
        team_dict['primary_color'].replace('#', ''), 16)
    team_dict['primary_color'] = int(hex(team_dict['primary_color']), 0)

    team_dict['positional_breakdown'] = list()

    for i in range(len(team_dict['players'])):
        team_dict['players'][i]['CapNumber'] = parse_dollars(
            team_dict['players'][i]['CapNumber'])

    for i in range(len(team_dict['positional_spending'])):
        split = team_dict['positional_spending'][i].split(': ')
        team_dict['positional_breakdown'].append({split[0]: split[1]})

    team_dict['positional_spending'] = {
        k: v for x in team_dict['positional_breakdown'] for k, v in x.items()}

    for k, v in team_dict['positional_spending'].items():
        team_dict['positional_spending'][k] = parse_dollars(v)

    return team_dict


def retrieve_players():
    filepath = r"C:\users\jordan\desktop\overthecap_bot\team_info.csv"
    team_info = pd.read_csv(filepath)

    team_dict = team_info[['nickname', 'team_abbrev']].set_index(
        'nickname').to_dict()['team_abbrev']

    url = 'https://overthecap.com/contracts/'
    df = pd.read_html(url)[0]

    http = httplib2.Http()
    status, response = http.request(url)

    links = []

    for link in BeautifulSoup(response, 'html.parser', parse_only=SoupStrainer('a')):
        if link.has_attr('href'):
            links.append(link['href'])

    links = [x for x in links if 'player' in x]

    df['Links'] = links
    df['Team'] = df['Team'].str.lower()
    df['Player'] = df['Player'].apply(parse_name)
    df['Team Abbrev'] = df['Team'].map(team_dict)
    df['URL'] = 'https://overthecap.com' + df['Links']

    return df


all_players = retrieve_players()


def get_player_contract(player, team):
    today = datetime.today()
    current_year = today.year

    player = player.lower()
    team = team.upper()

    parsed_player = parse_name(player)

    url = all_players.loc[(all_players['Player'] == parsed_player) & (
        all_players['Team Abbrev'] == team)]['URL'].item()

    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')

    bio = {}

    for s in soup.find(class_='player-bio-new').stripped_strings:
        key, value = s.split(': ')
        bio[key] = value

    if str(current_year) in bio['Free Agency']:
        bio['FA'] = True
    else:
        bio['FA'] = False

    bio['Team'] = team
    bio['Position'] = bio['Contract Ranking'].split(" at ")[1]
    bio['Entry'] = parse_draft(bio['Entry'])
    bio['Contract Ranking'] = bio['Contract Ranking'].split(" at ")[0]
    bio['URL'] = url

    if bio['FA'] == False:
        tables = pd.read_html(url)[0]

        tables = tables[tables['Year'] != 'Total']

        tables = tables.replace("Void", '0')

        tables['Year'] = tables['Year'].str.extract('([0-9]{4})')
        tables['Base Salary'] = tables['Base Salary'].apply(dollars_to_int)
        try:
            tables['Prorated Bonus'] = tables['Prorated Bonus'].apply(
                dollars_to_int)
        except KeyError:
            tables['Prorated Bonus'] = 0
        try:
            tables['Guaranteed Salary'] = tables['Guaranteed Salary'].apply(
                dollars_to_int)
        except KeyError:
            tables['Guaranteed Salary'] = 0
        tables['CapNumber'] = tables['CapNumber'].apply(dollars_to_int)

        tables = tables.fillna(0)

        tables['cumsum'] = tables['Prorated Bonus'][::-1].cumsum()
        tables['cumguaranteed'] = tables['Guaranteed Salary'][::-1].cumsum()
        tables['dead_cap'] = tables['cumsum'] + tables['cumguaranteed']

        ### Add to bio
        bio['Dead Cap'] = tables[tables['Year'].str.contains(
            str(current_year))]['dead_cap'].item()

        bio['Current Year Salary'] = tables[tables['Year'].str.contains(
            str(current_year))]['CapNumber'].item()

        ### Reformat values
        bio['Fully Guaranteed Money'] = parse_dollars(
            bio['Fully Guaranteed Money'])
        bio['Contract Value'] = parse_contract(bio['Contract Value'])
        bio['Dead Cap'] = parse_dollars(bio['Dead Cap'])
        bio['Current Year Salary'] = parse_dollars(bio['Current Year Salary'])

    return bio


def get_top_contracts(position, season=""):
    positionDict = {
        "QB": "quarterback",
        "RB": "running-back",
        "FB": "fullback",
        "WR": "wide-receiver",
        "TE": "tight-end",
        "LT": "left-tackle",
        "LG": "left-guard",
        "C": "center",
        "RG": "right-guard",
        "RT": "right-tackle",
        "IDL": "interior-defensive-line",
        "EDGE": "edge-rusher",
        "LB": "linebacker",
        "S": "safety",
        "CB": "cornerback",
        "K": "kicker",
        "P": "punter",
        "LS": "long-snapper"
    }

    fullPosition = positionDict[position]

    url = f"https://overthecap.com/position/{fullPosition}/{season}"

    salTable = pd.read_html(url)[0].head()

    dollarColumns = ['Total Value', 'Avg./Year',
                     'Total Guaranteed', 'Fully Guaranteed']

    for column in dollarColumns:
        salTable[column] = salTable[column].apply(parse_dollars)

    salTable['Contract'] = salTable['Total Value'] + \
        " (" + salTable['Avg./Year'] + " APY)"

    salJSON = salTable.to_json(orient="records")

    return json.loads(salJSON)

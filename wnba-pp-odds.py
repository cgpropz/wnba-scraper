import requests
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials
import logging
import json

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def dfs_scraper():
    logging.info("Starting data scrape from PrizePicks API")
    try:
        response = requests.get('https://partner-api.prizepicks.com/projections?per_page=1000')
        response.raise_for_status()  # Raise exception for bad status
        prizepicks = response.json()
    except Exception as e:
        logging.error(f"Failed to fetch data from PrizePicks: {str(e)}")
        raise

    pplist, library = [], {}

    for included in prizepicks['included']:
        if 'attributes' in included and 'name' in included['attributes']:
            PPname_id = included['id']
            PPname = included['attributes']['name']
            ppteam = included['attributes'].get('team', 'N/A')
            ppleague = included['attributes'].get('league', 'N/A')
            library[PPname_id] = {'name': PPname, 'team': ppteam, 'league': ppleague}

    for ppdata in prizepicks['data']:
        PPid = ppdata.get('relationships', {}).get('new_player', {}).get('data', {}).get('id', 'N/A')
        ppinfo = {
            "name_id": PPid,
            "Stat": ppdata.get('attributes', {}).get('stat_type', 'N/A'),
            "Prizepicks": ppdata.get('attributes', {}).get('line_score', 'N/A'),
            "Versus": ppdata.get('attributes', {}).get('description', 'N/A'),
            "Odds Type": ppdata.get('attributes', {}).get('odds_type', 'N/A')
        }
        pplist.append(ppinfo)

    for element in pplist:
        player_data = library.get(element['name_id'], {"name": "Unknown", "team": "N/A", "league": "N/A"})
        element.update({"Name": player_data['name'], "Team": player_data['team'], "League": player_data['league']})
        del element['name_id']

    df = pd.DataFrame([
        (e['Name'], e['League'], e['Team'], e['Stat'], e['Versus'], e['Prizepicks'], e['Odds Type'])
        for e in pplist if e['League'] == 'WNBA' and '+' not in e['Name']
    ], columns=['Name', 'League', 'Team', 'Stat', 'Versus', 'Prizepicks', 'Odds Type'])

    logging.info("Scraping complete, dataframe created")
    return df

def update_google_sheet(df):
    logging.info("Starting Google Sheets update")
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        logging.debug("Loading credentials from environment variable")
        creds_json = json.loads('''${{ secrets.GOOGLE_SHEETS_CREDENTIALS_PP }}''')
        creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
        logging.debug(f"Credentials loaded, service account: {creds.service_account_email}")
        client = gspread.authorize(creds)

        logging.debug("Opening Google Sheet by ID")
        sheet = client.open_by_key('14sXJ4m6x6Dtl1vh4QsHv1SOpvlLQCG0lNRj7RaEvdSg')
        worksheet = sheet.worksheet('PP_ODDS2')
        logging.debug("Worksheet PP_ODDS2 accessed")

        logging.debug("Clearing range A1:G")
        worksheet.batch_clear(['A1:G'])

        logging.debug("Uploading dataframe to Google Sheet")
        set_with_dataframe(worksheet, df)
        logging.info("Google Sheet updated successfully! ✅")
    except Exception as e:
        logging.error(f"Failed to update Google Sheet: {str(e)}")
        raise

if __name__ == "__main__":
    df = dfs_scraper()
    update_google_sheet(df)

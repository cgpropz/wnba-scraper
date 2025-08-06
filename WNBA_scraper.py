from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from io import StringIO

print("🚀 Starting WNBA odds scraper...")

# Chrome options setup
options = Options()
options.add_argument('--headless')  # Run in headless mode
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--log-level=3')

# Initialize Chrome driver
try:
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    print("✓ Chrome driver started successfully!")
except Exception as e:
    print(f"Failed to start Chrome driver: {e}")
    raise Exception("Could not start Chrome driver")

# Set timeouts
driver.set_page_load_timeout(60)
driver.implicitly_wait(10)

# Initialize WebDriverWait
wait = WebDriverWait(driver, 15)
long_wait = WebDriverWait(driver, 60)

def debug_page_elements(driver, url, df=None):
    """Debug function to inspect page elements and DataFrame"""
    try:
        print(f"Debugging elements on {url}:")
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"  Found {len(tables)} table elements")
        for i, table in enumerate(tables):
            classes = table.get_attribute("class")
            rows = table.find_elements(By.TAG_NAME, "tr")
            print(f"    Table {i}: classes = '{classes}', rows = {len(rows)}")
            for j, row in enumerate(rows[:3]):  # Limit to first three rows
                cells = row.find_elements(By.TAG_NAME, "td") or row.find_elements(By.TAG_NAME, "th")
                cell_texts = [cell.text.strip() for cell in cells]
                print(f"      Row {j}: {cell_texts}")
        if df is not None:
            print(f"  DataFrame columns: {list(df.columns)}")
            print(f"  DataFrame sample:\n{df.head(3)}")
        no_data = driver.find_elements(By.XPATH, "//*[contains(text(), 'No Data') or contains(text(), 'No Games') or contains(text(), 'No Events')]")
        if no_data:
            print(f"  Found 'No Games' message: {no_data[0].text}")
    except Exception as e:
        print(f"  Debug error: {e}")

# Navigate to login page
print("🔐 Navigating to login page...")
driver.get('https://beebettor.com/ev/data/wnba/player_points_over_under')

# Log in
print("📝 Logging in...")
try:
    email_input = wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/main/div/div[2]/div/form/div[1]/input')))
    email_input.send_keys('kahlilhodge@gmail.com')
    password_input = driver.find_element(By.XPATH, '/html/body/main/div/div[2]/div/form/div[2]/input')
    password_input.send_keys('Kmh050598!')
    login_button = driver.find_element(By.XPATH, '/html/body/main/div/div[2]/div/form/div[4]/input')
    login_button.click()
    print("✓ Login credentials submitted")
    time.sleep(3)
except Exception as e:
    print(f"Login failed: {e}")
    driver.quit()
    raise

# Define URLs to scrape
urls = [
    'https://beebettor.com/ev/data/wnba/player_points_over_under',
    'https://beebettor.com/ev/data/wnba/player_rebounds_over_under',
    'https://beebettor.com/ev/data/wnba/player_assists_over_under',
    'https://beebettor.com/ev/data/wnba/player_assists_points_rebounds_over_under',
    'https://beebettor.com/ev/data/wnba/player_assists_points_over_under',
    'https://beebettor.com/ev/data/wnba/player_assists_rebounds_over_under',
    'https://beebettor.com/ev/data/wnba/player_points_rebounds_over_under',
    'https://beebettor.com/ev/data/wnba/player_threes_over_under',
    'https://beebettor.com/ev/data/wnba/player_blocks_over_under',
    'https://beebettor.com/ev/data/wnba/player_steals_over_under',
    'https://beebettor.com/ev/data/wnba/player_blocks_steals_over_under',
    'https://beebettor.com/ev/data/wnba/player_turnovers_over_under'
]

# Scrape data
dfs = []
for url in urls:
    print(f"📊 Processing URL: {url}")
    driver.get(url)

    try:
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except TimeoutException:
        print(f"Timeout waiting for page to load: {url}")
        continue

    # Check for "No Games" message before proceeding
    try:
        no_data = driver.find_elements(By.XPATH, "//*[contains(text(), 'No Data') or contains(text(), 'No Games') or contains(text(), 'No Events')]")
        if no_data:
            print(f"❌ No games available on {url}: {no_data[0].text}")
            continue
    except:
        pass

    try:
        games_tab = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/main/div/div[3]/div[2]/div[1]")))
        driver.execute_script("arguments[0].click();", games_tab)
        print(f"Clicked Games tab on {url}")
        time.sleep(0.5)
        all_button = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/main/div/div[3]/div[2]/div[2]/div[1]/div[2]/button[1]")))
        driver.execute_script("arguments[0].click();", all_button)
        print(f"Clicked All button on {url}")
        time.sleep(2)
    except Exception as e:
        print(f"Failed to click Games tab or All button on {url}: {e}")
        continue

    print(f"Waiting for table to load on {url}...")
    table_selectors = ["table.table-fixed.relative", "table.mt-2.table-auto.w-full", "table"]
    table_found = False
    table_selector = None

    for selector in table_selectors:
        try:
            long_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            table = driver.find_element(By.CSS_SELECTOR, selector)
            rows = table.find_elements(By.TAG_NAME, "tr")
            if len(rows) > 1:  # Ensure table has more than just a header
                print(f"Found table using selector: {selector}")
                table_selector = selector
                table_found = True
                break
        except TimeoutException:
            continue

    if not table_found:
        print(f"No table found on {url}")
        debug_page_elements(driver, url)
        continue

    def table_has_content(driver):
        try:
            table = driver.find_element(By.CSS_SELECTOR, table_selector)
            rows = table.find_elements(By.TAG_NAME, "tr")
            print(f"Table rows found: {len(rows)}")
            return len(rows) >= 2  # Require at least header + 1 data row
        except:
            return False

    try:
        long_wait.until(table_has_content)
        print(f"Table loaded successfully on {url}")
    except TimeoutException:
        print(f"Timeout waiting for table content on {url}")
        debug_page_elements(driver, url)
        continue

    try:
        table = driver.find_element(By.CSS_SELECTOR, table_selector)
        html = table.get_attribute("outerHTML")
        df = pd.read_html(StringIO(html))[0]
        if len(df) <= 1:
            print(f"No data rows scraped from {url} (only header found)")
            debug_page_elements(driver, url, df)
            continue

        # Get column headers with fallback
        ths = table.find_elements(By.CSS_SELECTOR, "thead th")
        cols = []
        for i, th in enumerate(ths):
            try:
                imgs = th.find_elements(By.TAG_NAME, "img")
                if imgs:
                    src = imgs[0].get_attribute("src")
                    code = src.split("/")[-1].split("-")[0]
                    cols.append(code)
                else:
                    text = th.text.strip()
                    cols.append(text if text else f"Col_{i+1}")
            except:
                cols.append(f"Col_{i+1}")
        if len(cols) != len(df.columns):
            print(f"Warning: Header count ({len(cols)}) does not match DataFrame columns ({len(df.columns)})")
            cols = [f"Col_{i+1}" for i in range(len(df.columns))]
        df.columns = cols
        print(f"Columns scraped: {cols}")

        # Filter out non-data rows (e.g., headers or summaries)
        df = df[df[cols[0]].str.contains('@', na=False)]
        if df.empty:
            print(f"No valid data rows after filtering on {url}")
            debug_page_elements(driver, url, df)
            continue

        prop = url.rstrip("/").split("/")[-1].replace("_over_under", "")
        df["prop"] = prop
        dfs.append(df)
        print(f"✓ Scraped {len(df)} rows from {url}")
    except Exception as e:
        print(f"Error scraping table from {url}: {e}")
        debug_page_elements(driver, url, df)
        continue

# Process and upload data
if not dfs:
    print("❌ No data scraped from any URLs")
else:
    print(f"📈 Processing {len(dfs)} dataframes...")
    big_df = pd.concat(dfs, ignore_index=True)

    # Debug: Print the first few rows of big_df
    print("Debug: big_df sample:\n", big_df.head())
    print("Debug: big_df columns:", list(big_df.columns))

    # Dynamically find O/U column (look for column with player data)
    ou_cols = [col for col in big_df.columns if big_df[col].astype(str).str.contains('@').any()]
    if not ou_cols:
        print("❌ No columns found with '@' delimiter (expected for O/U data)")
        debug_page_elements(driver, urls[0], big_df)
        # Fallback: try first non-prop column with non-null data
        potential_cols = [col for col in big_df.columns if col != 'prop' and big_df[col].notna().any()]
        if potential_cols:
            ou_cols = [potential_cols[0]]
            print(f"Fallback: Using column '{ou_cols[0]}' for O/U data")
        else:
            print("❌ No suitable columns for O/U data")
            driver.quit()
            exit()

    big_df['O/U'] = big_df[ou_cols].bfill(axis=1).iloc[:, 0]
    big_df['info'] = big_df['O/U'].astype(str).replace('nan', '')

    # Debug: Check contents of 'info' column
    print("Debug: 'info' column sample:\n", big_df['info'].head())
    if big_df['info'].str.strip().eq('').all():
        print("❌ 'info' column is empty, skipping processing")
        debug_page_elements(driver, urls[0], big_df)
        driver.quit()
        exit()

    # Split 'info' column and handle cases where split doesn't produce two columns
    split1 = big_df['info'].str.split(' @ ', n=1, expand=True)
    print("Debug: split1 columns:", split1.shape[1])
    if split1.shape[1] == 2:
        split1.columns = ['prefix', 'suffix']
    else:
        print("❌ Split did not produce expected columns, using fallback")
        split1.columns = ['prefix'] if split1.shape[1] == 1 else ['prefix', 'suffix']
        if split1.shape[1] == 1:
            split1['suffix'] = ''  # Add empty suffix column if split fails

    # Further split prefix and suffix
    prefix_split = split1['prefix'].str.rsplit(' ', n=1, expand=True)
    prefix_split.columns = ['player', 'away'] if prefix_split.shape[1] == 2 else ['player', '']

    suffix_split = split1['suffix'].str.rsplit(' ', n=2, expand=True)
    suffix_split.columns = ['home', 'O/U', 'line'] if suffix_split.shape[1] == 3 else ['home', '', '']

    # Assign to big_df
    big_df['player'] = prefix_split['player']
    big_df['away'] = prefix_split['away']
    big_df['home'] = suffix_split['home']
    big_df['O/U'] = suffix_split['O/U']
    big_df['line'] = suffix_split['line']
    big_df = big_df.drop(columns=['info'] + ou_cols)

    # Reorder columns
    first_cols = ['player', 'prop', 'O/U', 'line', 'away', 'home']
    remaining = [c for c in big_df.columns if c not in first_cols]
    big_df = big_df[first_cols + remaining]
    big_df = big_df.dropna(subset=["away"])
    big_df = big_df.fillna('x')
    big_df['player'] = big_df['player'].str.replace(r'^\d+\.\s*', '', regex=True).str.strip()

    # Debug: Print final DataFrame
    print("Debug: Final big_df sample:\n", big_df.head())

    print("📊 Uploading to Google Sheets...")
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name("auth.json", scopes)
        gs = gspread.authorize(credentials)
        sheet = gs.open_by_url("https://docs.google.com/spreadsheets/d/14sXJ4m6x6Dtl1vh4QsHv1SOpvlLQCG0lNRj7RaEvdSg")
        ws = sheet.worksheet("Sports_Data")
        ws.clear()
        ws.append_row(big_df.columns.tolist())
        ws.append_rows(big_df.values.tolist())
        print(f"✅ Uploaded {len(big_df)} rows to Google Sheets")
    except Exception as e:
        print(f"Failed to upload to Google Sheets: {e}")

# Cleanup
print("🧹 Cleaning up...")
try:
    driver.quit()
    print("✓ Driver closed")
except Exception as e:
    print(f"Warning: Driver close failed: {e}")

print("🎉 Scraping complete!")

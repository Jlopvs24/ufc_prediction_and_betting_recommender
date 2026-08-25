import warnings
import pandas as pd, requests
from bs4 import BeautifulSoup

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from first_webscrape import get_all_fights_links, scrape_past_fight
from preprocess import prepare_data
from df_fights_creation import build_df_fights

def get_past_event_links(url, driver):
    """
    Retrieves all UFC event links that occurred after the most recent date found in the existing raw dataset.
    These events are considered "new" and need to be scraped.

    Args:
        url (str): URL containing the list of completed UFC events.

    Returns:
        list: A list of URLs (strings) corresponding to new UFC events to scrape.
    """

    # Load the existing raw dataset
    try:
        df = pd.read_csv("data/all_ufc_data_raw.csv")
    except FileNotFoundError:
        print("Error: The file 'data/all_ufc_data_raw.csv' was not found.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while reading the file: {e}")
        return None

    
    # Extract and sort event dates from the dataset
    try:
        
        df['Date'] = df['Date'].astype(str)
        
        df['Date'] = (
            df['Date']
            .str.replace('Date:', '', regex=False)
            .str.replace(r'[^0-9\-\./]', '', regex=True)
            .str.strip()
        )
        
        df["Date"] = pd.to_datetime(df["Date"], format='%Y-%m-%d', errors='coerce')
        
        df['Date'] = df['Date'].dt.date
        
        df.sort_values(by='Date', ascending=False, inplace=True)
        last_date_data = df.iloc[0]["Date"]

        print(f'Last date with data is: {last_date_data}')
    except Exception as e:
        print(f"Error processing dates in existing data: {e}")
        return []

    # Fetch the HTML page containing all UFC events
    try:
        
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "b-statistics__table-events"))
        )
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        """headers = {
            "User-Agent": 
                ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/127.0.0.1 Safari/537.36")
            }
        
        response = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        """
        # Locate the main event table and filter valid rows
        table = soup.find('table', class_='b-statistics__table-events')
        rows = table.find_all("tr", class_="b-statistics__table-row")[2:]
        rows = [row for row in rows if 'b-statistics__table-row_type_first' not in row.get('class', [])]
    except Exception as e:
        print(f"Error fetching or parsing the events page: {e}")
        return []
    
    event_links, n = [], 0

    # Iterate through event rows and collect links for newer events
    for row in rows[:-1]:
        if row is not None:
            try:
                col_tag = row.find("td", class_="b-statistics__table-col")
                content_tag = col_tag.find("i", class_="b-statistics__table-content")
                date_tag = content_tag.find("span", class_="b-statistics__date")
                
                # Extract and clean event date
                date = date_tag.get_text(strip=True) if date_tag else None
                date = date.replace("Date:", "").replace("Date :", "").strip() if date else None
                date = pd.to_datetime(date, errors='coerce').strftime('%Y-%m-%d') if not pd.isna(date) else None

                # Append events that are more recent than our last known date
                if date is not None:
                    if pd.to_datetime(date, errors='coerce') > pd.to_datetime(last_date_data, errors='coerce'):
                        print("Processing event date:", date)
                        event_link_tag = row.find("a", href = True)
                        event_link = event_link_tag['href'] if event_link_tag else None

                        event_links.append(event_link)
                        # print(f"Event number {n} obtained: {event_link}")
                        n += 1
                
                else:
                    break

            except Exception as e:
                print(f"Error processing row: {e}")
                continue
    
    print(f'{n} new events found after {last_date_data}.')
    return event_links

def calculate_winner_a(last_predictions, df_new_fights):
    """
    Matches new fights with past predictions to determine if Fighter A won,
    updating the 'Winner_A' column accordingly.

    Args:
        last_predictions (pd.DataFrame): The dataframe containing the last predictions made.
        df_new_fights (pd.DataFrame): The dataframe with the newly scraped fight results.

    Returns:
        pd.DataFrame: Updated dataframe with 'Winner_A' values filled based on actual outcomes.
    """
    
    updated_last_predictions = last_predictions.copy()
    
    # Match predicted fights with their actual outcomes
    for idx, row in updated_last_predictions.iterrows():
        
        matching_fight = df_new_fights[
            (
                (df_new_fights['Fighter_A_Name'] == row['Fighter_A_Name']) & (df_new_fights['Fighter_B_Name'] == row['Fighter_B_Name'])
                |
                (df_new_fights['Fighter_A_Name'] == row['Fighter_B_Name']) & (df_new_fights['Fighter_B_Name'] == row['Fighter_A_Name'])
            )
        ]

        if not matching_fight.empty:
            fight = matching_fight.iloc[0]
            if fight['Fighter_A_Name'] == row['Fighter_A_Name']:
                updated_last_predictions.at[idx, "Winner_A"] = fight["Winner_A"]
            else:
                # If order of fighters is reversed, invert the result
                updated_last_predictions.at[idx, "Winner_A"] = 1 - fight["Winner_A"]
        else:
            updated_last_predictions.at[idx, "Winner_A"] = None

    return updated_last_predictions

def refresh_data(url, driver):
    """
    Main function that refreshes the entire UFC dataset by:
    - Scraping new events since the last recorded date
    - Preprocessing the new data
    - Updating existing CSVs with the new content
    - Maintaining consistent data structure across all files

    Args:
        url (str): URL containing the list of completed UFC events.

    Returns:
        str: Message indicating the refresh status.
    """

    # Load the existing raw data    
    try:
        df = pd.read_csv("data/all_ufc_data_raw.csv")
    except FileNotFoundError:
        print("Error: The file 'data/all_ufc_data_raw.csv' was not found.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while reading the file: {e}")
        return None
    
    # Get events after last date
    print("Starting to scrape new events...")
    try:
        event_links = get_past_event_links(url=url, driver=driver)
    except Exception as e:
        print(f"Error obtaining event links: {e}")
        return "No new events to scrape."

    if not event_links or event_links == []:
        return None
    print("Event links obtained.")
    
    all_fighters_data = []

    # Scrape all fights from new events
    for event_link in event_links:
        fight_links, event_date, event_location = get_all_fights_links(event_link, driver)
        for fight_link in fight_links:
            fighter_a, fighter_b = scrape_past_fight(fight_link, event_date, event_location, driver)
            all_fighters_data.append(fighter_a)
            all_fighters_data.append(fighter_b)
            # print(f"Fight data obtained: {fight_link}")
    
    # Create a dataframe with all new fights
    df_new = pd.DataFrame(all_fighters_data)
    
    # Append new data to existing raw data
    df = pd.concat([df, df_new], ignore_index=True)
    df.drop_duplicates(subset=['Name', 'Opponent', 'Date'], keep='last', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    df.to_csv("data/all_ufc_data_raw.csv", index=False)
    print("Data scraped and saved to 'data/all_ufc_data_raw.csv'")
    
    # Process new fights and save
    df_new_processed = prepare_data(df_new)
    df_processed = pd.read_csv("data/all_ufc_data_processed.csv")
    
    df_processed = pd.concat([df_processed, df_new_processed], ignore_index=True)
    df_processed.drop_duplicates(subset=['Name', 'Opponent', 'Date'], keep='last', inplace=True)
    df_processed.reset_index(drop=True, inplace=True)
    
    df_processed.to_csv("data/all_ufc_data_processed.csv", index=False)
    print("Data preprocessed and saved to 'data/all_ufc_data_processed.csv'")

    # Update the fights dataframe (aggregated by fight)
    df_new_fights = build_df_fights(df_new_processed)
    df_fights = pd.read_csv("data/df_fights.csv")
    
    df_fights_to_save = pd.concat([df_fights, df_new_fights], ignore_index=True)
    df_fights_to_save.drop_duplicates(subset=['Fighter_A_Name', 'Fighter_B_Name', 'Date'], keep='last', inplace=True)
    df_fights_to_save.reset_index(drop=True, inplace=True)
    
    df_fights_to_save.to_csv("data/df_fights.csv", index=False)
    print("Fights dataframe updated and saved to 'data/df_fights.csv'")
    
    # Update df_fights_with_odds.csv
    try:
        last_predictions = pd.read_csv("data/last_predictions.csv")
    except FileNotFoundError:
        print(f'Error while trying to read "data/last_predictions.csv".')
    try:
        df_fights_with_odds = pd.read_csv("data/df_fights_with_odds.csv")
    except FileNotFoundError:
        print(f'Error while trying to read "data/df_fights_with_odds.csv".')
    
    odds_a, odds_b = last_predictions['Odds_A'], last_predictions['Odds_B']
    
    df_new_fights_with_odds = df_new_fights.copy()
    
    def create_fight_id(row):
        f_a, f_b, d = str(row['Fighter_A_Name'].strip().replace(" ", "_").lower()), str(row['Fighter_B_Name'].strip().replace(" ", "_").lower()), row['Date'].strftime("%Y_%m_%d") if pd.notnull(row['Date']) else None
        return f'{f_a}-{f_b}-{d}'
    
    # Apply odds and unique identifiers to new fights
    df_new_fights_with_odds['Date'] = pd.to_datetime(df_new_fights_with_odds['Date'], errors='coerce')
    df_new_fights_with_odds['fight_id'] = df_new_fights_with_odds.apply(create_fight_id, axis=1)
    df_new_fights_with_odds['Odds_A'] = odds_a
    df_new_fights_with_odds['Odds_B'] = odds_b
    
    df_fights_with_odds = pd.concat([df_fights_with_odds, df_new_fights_with_odds], ignore_index=True)
    df_fights_with_odds.drop_duplicates(subset=['Fighter_A_Name', 'Fighter_B_Name', 'Date'], keep='last', inplace=True)
    df_fights_with_odds.reset_index(drop=True, inplace=True)
    
    df_fights_with_odds.to_csv("data/df_fights_with_odds.csv", index=False)
    print("Fights with odds dataframe updated and saved to 'data/df_fights_with_odds.csv'.")

    # Update or create historical predictions file
    try:
        historical_predictions = pd.read_csv("data/historical_predictions.csv")
        
        updated_last_predictions = calculate_winner_a(last_predictions, df_new_fights)
        
        # Catch warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            historical_predictions = pd.concat([historical_predictions, updated_last_predictions], ignore_index=True)
        
        historical_predictions.reset_index(drop=True, inplace=True)
        historical_predictions.to_csv("data/historical_predictions.csv", index=False)

    except FileNotFoundError:
        updated_last_predictions = calculate_winner_a(last_predictions, df_new_fights)
        updated_last_predictions.to_csv("data/historical_predictions.csv", index=False)
        
    return "Data refresh completed successfully."


def main(url, driver):
    """
    Entry point for the update module.
    Calls `refresh_data()` and handles top-level exceptions.

    Args:
        url (str): URL containing the list of completed UFC events.

    Returns:
        str or None: Status message if successful, None otherwise.
    """
    
    print("........................................")
    print("Starting data refresh...")

    try:
        message = refresh_data(url, driver)
        return message
    except FileNotFoundError as e:
        print(f"File not found: {e}. Please check the CSV paths.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Network error during scraping: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

if __name__ == "__main__":
    main()
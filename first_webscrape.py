import pandas as pd, requests
from bs4 import BeautifulSoup
from datetime import datetime

import time
import random
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

#################################################################################################################
# IMPORTANT: This script scrapes all the data from the UFCStats website. 
# It may take around 2 hours to complete because it needs to iterate through every event and fight.
#################################################################################################################

def get_all_events_links(url, driver):
    """
    Retrieve all event links from the UFC events page.

    This function parses the main UFC events page and extracts hyperlinks
    for every past event. Each event will later be scraped individually to obtain
    detailed fight data.

    Parameters
    ----------
    url : str
        URL of the UFC events page (e.g., "http://ufcstats.com/statistics/events/completed?page=all").

    Returns
    -------
    list of str
        List containing the URLs of all UFC event pages.
    """
    
    driver.get(url)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CLASS_NAME, "b-statistics__table-events"))
    )
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Find all event rows in the statistics table
    event_rows = soup.find_all("tr", class_="b-statistics__table-row")

    event_links, n = [], 0
    for row in event_rows[2:]:          # Skip headers and empty rows from the table
        event_link_tag = row.find("a", href=True)
        event_link = event_link_tag['href'] if event_link_tag else None
        
        event_links.append(event_link)
        # print(f"Event number {n} obtained: {event_link}")
        n += 1
    
    print(f'{n} events found in total.')
    return event_links

def get_all_fights_links(event_link, driver):
    """
    Extract all fight links, event date, and location from a specific UFC event page.

    Parameters
    ----------
    event_link : str
        URL of the event page on UFCStats.

    Returns
    -------
    tuple
        (fight_links, event_date, event_location)
        fight_links : list of str
            List of URLs for all fights in this event.
        event_date : str
            Date of the event in 'YYYY-MM-DD' format.
        event_location : str
            Location of the event (e.g., 'Las Vegas, Nevada, USA').
    """
    
    driver.get(event_link)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CLASS_NAME, "b-fight-details__table-body"))
    )
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Locate the box containing date and location information
    date_location_section = soup.find("div", class_="b-list__info-box_style_large-width")
    date_location_items = date_location_section.find_all("li", class_="b-list__box-list-item") if date_location_section else []
    
    # Extract date text (normalize various formats)
    event_date_raw = date_location_items[0].get_text(strip=True).replace("Date:", "") if len(date_location_section) > 0 else None
    event_date = None
    if event_date_raw:
        try:
            event_date = datetime.strptime(event_date_raw, '%B %d, %Y').strftime('%Y-%m-%d') # September 27, 2025 -> YYYY-MM-DD
        except ValueError:
            try:
                event_date = datetime.strptime(event_date_raw, '%b. %d, %Y').strftime('%Y-%m-%d') # Sep. 27, 2025 -> YYYY-MM-DD
            except ValueError:
                print(f'Could not parse date: {event_date_raw}')
                event_date = event_date_raw
    
    # Extract location (if present)
    event_location = date_location_items[1].get_text(strip=True).replace("Location: ", "") if len(date_location_section) > 1 else None

    # Find all fight rows and extract links
    rows = soup.find_all('tr', class_='b-fight-details__table-row')

    fight_links, n = [], 0
    for row in rows[1:]:        # Skip table header
        fight_links.append(row.get("data-link"))
        # Debugging line:
        # print(f"Fight number {n} obtained: {row.get('data-link')}")
        n += 1

    print(f'{n} fights found in event on {event_date} at {event_location}.')
    return fight_links, event_date, event_location

def scrape_past_fight(fight_link, fight_date, fight_location, driver):
    """
    Scrape detailed statistics for a single past UFC fight.

    This function extracts fighter information, fight metadata, 
    and detailed performance statistics from a UFC fight page.
    It produces two dictionaries: one per fighter.

    Parameters
    ----------
    fight_link : str
        URL of the fight page on UFCStats.
    fight_date : str
        Date of the event in 'YYYY-MM-DD' format.
    fight_location : str
        Location of the event.
    driver : Selenium WebDriver
        The Selenium WebDriver instance used to load the fight page.

    Returns
    -------
    tuple
        (fighter_a, fighter_b)
        Two dictionaries containing fighter-level data for the fight.
    """
    
    driver.get(fight_link)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CLASS_NAME, "b-fight-details"))
    )
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    # Dictionaries for storing parsed data
    fight_data, fighter_a, fighter_b = dict(), dict(), dict()
    
    # ------------------ BASIC INFO: Names and Win/Loss ------------------
    fighters_tags = soup.find_all("div", class_="b-fight-details__person")
    fighter_a_name = fighters_tags[0].find("h3", class_="b-fight-details__person-name").get_text(strip=True) if len(fighters_tags) > 0 else None
    fighter_b_name = fighters_tags[1].find("h3", class_="b-fight-details__person-name").get_text(strip=True) if len(fighters_tags) > 1 else None
    winner_a = 1 if "W" in fighters_tags[0].find("i", class_="b-fight-details__person-status").get_text(strip=True) else 0
    winner_b = 1 if "W" in fighters_tags[1].find("i", class_="b-fight-details__person-status").get_text(strip=True) else 0
    
    # ------------------ FIGHT METADATA ------------------
    fight_details = soup.find("div", class_="b-fight-details__fight")
    weight_class_raw = fight_details.find("i", class_="b-fight-details__fight-title").get_text(strip=True) if fight_details else None
    
    # Detect if it's a title fight
    title_bout = int("Title Bout" in weight_class_raw) if weight_class_raw else 0

    # Extract weight class properly (ignore "UFC" and "Title Bout" if necessary)
    if title_bout:
        weight_class = " ".join(weight_class_raw.split()[1:len(weight_class_raw.split()) - 2]) if weight_class_raw else None
    else:
        weight_class = " ".join(weight_class_raw.split()[:len(weight_class_raw.split()) - 1]) if weight_class_raw else None
    
    # Method (KO/TKO, Decision, Submission, etc.)
    method_block = fight_details.find("i", class_="b-fight-details__text-item_first")
    method = method_block.find_all("i")[-1].get_text(strip=True)
    
    fight_data["Weight_Class"], fight_data["Title_Bout"], fight_data['Method'] = weight_class, title_bout, method
    
    # Extract round/time-related metadata
    items = fight_details.find_all("i", class_="b-fight-details__text-item")
    for item in items:
        label_tag = item.find("i", class_="b-fight-details__label")
        if label_tag:
            label = label_tag.get_text(strip=True)
            clean_label = label.strip().replace(":", "").replace(" ", "_").replace(".", "").replace("/", "_per_").replace("%", "Pct")
            value = item.get_text(strip=True).replace(label, "").replace(" ","_").strip()
            fight_data[clean_label] = value
    
    # Basic fight structure
    fighter_a["Name"], fighter_b["Name"] = fighter_a_name, fighter_b_name
    fighter_a["Opponent"], fighter_b["Opponent"] = fighter_b_name, fighter_a_name
    fighter_a["Win"], fighter_b["Win"] = winner_a, winner_b
    fight_data["Date"], fight_data["Location"] = fight_date, fight_location

    # Merge fight metadata into each fighter's record
    fighter_a = {**fighter_a, **fight_data}
    fighter_b = {**fighter_b, **fight_data}
    
    # ------------------ STATISTICAL TABLES ------------------
    tables = soup.find_all("table", class_="b-fight-details__table")

    for idx, table in enumerate(tables[:2]):        # Totals and Significant Strikes tables
        try:
            headers = [th.get_text(strip=True) for th in table.find("thead").find_all("th")]
            columns = table.find("tbody").find_all("td", class_="b-fight-details__table-col")

            values_list = []
            for column in columns:
                values = column.find_all("p", class_="b-fight-details__table-text")
                value_a = values[0].get_text(strip=True) if len(values) > 0 else None
                value_b = values[1].get_text(strip=True) if len(values) > 1 else None
                values_list.append((value_a, value_b))

            
            # Assign parsed values to fighter dictionaries
            for header, (value_a, value_b) in zip(headers, values_list):
                clean_header = header.strip().replace(":", "").replace(" ", "_").replace(".", "").replace("/", "_per_").replace("%", "Pct")
                prefix = "Totals" if idx == 0 else "Significant_Strikes"
                fighter_a[f"Fighter_A_{prefix}_{clean_header}"] = value_a
                fighter_b[f"Fighter_B_{prefix}_{clean_header}"] = value_b

        except Exception as e:
            print(f"Error processing table {idx} en {fight_link}: {e}")
            
            # Fill with None if parsing fails
            for header in headers if 'headers' in locals() else []:
                clean_header = header.strip().replace(":", "").replace(" ", "_").replace(".", "").replace("/", "_per_").replace("%", "Pct")
                prefix = "Totals" if idx == 0 else "Significant_Strikes"
                fighter_a[f"Fighter_A_{prefix}_{clean_header}"] = None
                fighter_b[f"Fighter_B_{prefix}_{clean_header}"] = None

    #       print(f"Fight with link {fight_link} scraped successfully")
    
    return fighter_a, fighter_b

def main(url, driver):
    """
    Main entry point for the web scraping process.

    It orchestrates the full pipeline:
    1. Fetch all UFC event links.
    2. For each event, get all fight links.
    3. For each fight, scrape fighter-level data.
    4. Aggregate results into a DataFrame and save to CSV.

    Parameters
    ----------
    url : str
        Main UFC events URL to start scraping from.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing all scraped fights with two rows per fight (one per fighter).
    """    
    
    print("........................................")
    print("Starting the webscraping process. This may take a while...")
    
    event_links = get_all_events_links(url=url, driver=driver)
    
    all_fighters_data = []
    
    # Iterate through all events and fights
    for event_link in event_links:
        fights_links, event_date, event_location = get_all_fights_links(event_link, driver)
        
        for fight_link in fights_links:
            fighter_a, fighter_b = scrape_past_fight(fight_link, event_date, event_location, driver)
            all_fighters_data.append(fighter_a)
            all_fighters_data.append(fighter_b)
    
    # Save all scraped data
    df = pd.DataFrame(all_fighters_data)
    df.to_csv("data/all_ufc_data_raw.csv", index=False)

    print("Webscraping completed and data saved to data/all_ufc_data_raw.csv")
    return df

if __name__ == "__main__":
    main()
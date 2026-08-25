import pandas as pd, requests, re
from bs4 import BeautifulSoup
from preprocess import country_to_continent

def get_next_event_link(url = "http://ufcstats.com/statistics/events/upcoming"):
    """
    Scrape the UFC Stats 'upcoming events' page to extract:
    - The URL of the next event
    - The date of the event
    - The event location (city/country)
    
    Args:
        url (str): URL of the upcoming events page.

    Returns:
        tuple: (next_event_link, next_event_date, next_event_location)
    """
    
    response = requests.get(url, timeout = 10)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Each event is listed as a row in the table
    rows = soup.find_all("tr", class_="b-statistics__table-row")
    event_rows = [row for row in rows if row.find("a", href=True)]
    
    # The first row corresponds to the next upcoming event
    next_event = event_rows[0]
    next_event_link = next_event.find("a", href=True)["href"]
    
    # Extract event date
    date_tag = next_event.find("span", class_="b-statistics__date")
    next_event_date = pd.to_datetime(date_tag.get_text(strip=True), errors='coerce') if date_tag else None

    # Extract event location (usually 'City, Country')
    location_tag = next_event.find_all("td", class_="b-statistics__table-col")[-1]
    next_event_location = location_tag.get_text(strip=True) if location_tag else None

    return next_event_link, next_event_date, next_event_location

def get_next_event_fights_links(url):
    """
    Given the link to an event page, extract all the individual fight links.
    
    Args:
        url (str): The URL of the event page.
    
    Returns:
        list[str]: List of fight page URLs.
    """
    
    response = requests.get(url, timeout = 10)
    soup = BeautifulSoup(response.text, "html.parser")

    fight_links = []
    rows = soup.find_all("tr", class_="b-fight-details__table-row")
    for row in rows:
        link = row.get("data-link")
        if link:
            fight_links.append(link)

    # fight_links is a list of fight_links
    return fight_links

def scrape_future_fight(fight_link, date):
    """
    Extracts information about a single upcoming fight:
    - Fighters' names
    - Weight class
    - Whether it is a title bout or not

    Args:
        fight_link (str): URL of the fight details page.
        date (datetime): Date of the event.
    
    Returns:
        dict: Basic fight data.
    """
    
    response = requests.get(fight_link, timeout = 10)
    soup = BeautifulSoup(response.content, "html.parser")

    # Extract fighter names (red corner = A, blue corner = B)
    fighter_names = soup.find_all("h3", class_="b-fight-details__person-name")
    fighter_a_name = fighter_names[0].get_text(strip=True) if len(fighter_names) > 0 else None
    fighter_b_name = fighter_names[1].get_text(strip=True) if len(fighter_names) > 1 else None

    # Extract weight class
    weight_class_tag = soup.find("i", class_="b-fight-details__fight-title")
    weight_class_raw = weight_class_tag.get_text(strip=True) if weight_class_tag else None
    
    weight_class = None
    title_bout = 0
    
    if weight_class_raw:
        # Extract known UFC divisions using regex
        match = re.search(r"(Featherweight|Lightweight|Welterweight|Middleweight|Heavyweight|Flyweight|Bantamweight|Catch Weight)", weight_class_raw, re.IGNORECASE)
        if match:
            weight_class = match.group(1)
        # Detect "title bout" phrases
        title_bout = int("title bout" in weight_class_raw.lower())

    return {"Fighter_A_Name": fighter_a_name, "Fighter_B_Name": fighter_b_name, "Weight_Class": weight_class, "Title_Bout": title_bout}

def prepare_location(location):
    """
    Split location string (e.g. 'Las Vegas, USA') and determine continent.
    Assumes the format may be 'City, Country' or 'City, State, Country'.

    Args:
        location (str): Full location string.

    Returns:
        dict: {'Country': str, 'Continent': str}
    """
    
    location_splitted = location.split(", ")
    if len(location_splitted) == 2:
        # Typical case: City, Country
        return {"Country": location_splitted[1].strip(), "Continent": country_to_continent(location_splitted[1].strip())}
    # Handle 3-part locations (e.g., City, State, Country)
    return {"Country": location_splitted[2].strip(), "Continent": country_to_continent(location_splitted[2].strip())}

def prepare_season(date):
    """
    Convert a date to its corresponding season (Winter, Spring, Summer, Fall).

    Args:
        date (datetime or str)

    Returns:
        str: Season name.
    """
    
    date=pd.to_datetime(date, errors='coerce')
    
    if date.month in [12, 1, 2]:
        return "Winter"
    elif date.month in [3, 4, 5]:
        return "Spring"
    elif date.month in [6, 7, 8]:
        return "Summer"
    else:
        return "Fall"

def fighter_historical_stats(fighter_name, date):
    """
    Compute historical statistics for a given fighter before a certain date.
    It combines data from 'all_ufc_data_processed.csv' (per-fight stats)
    and 'df_fights.csv' (aggregated fight info) to generate:
    - Averages of key performance metrics
    - Career totals (wins, losses, streaks, experience, etc.)
    - Whether this is the fighter's debut

    Args:
        fighter_name (str)
        date (datetime or str)
    
    Returns:
        dict: Fighter historical stats up to the given date.
    """
    
    df = pd.read_csv("data/all_ufc_data_processed.csv")
    df_fights = pd.read_csv("data/df_fights.csv")

    # Filter past fights for this fighter
    fighter_past_fights = df[
        (df["Name"] == fighter_name)
        & 
        (pd.to_datetime(df["Date"], errors='coerce') < pd.to_datetime(date, errors='coerce'))
    ].sort_values(by="Date", ascending=False).reset_index(drop=True)
    
    # Columns whose mean we’ll calculate (performance averages)
    columns_to_calculate_mean = [
        "Totals_KD", "Totals_Rev", "Totals_Sub_att", "Totals_Td_Pct", "Totals_Str_Landed", "Totals_Str_Attempted", "Totals_Ctrl_Sec",
        "Sig_Str_Landed", "Sig_Str_Attempted", "Sig_Str_Landed_Body", "Sig_Str_Attempted_Body", "Sig_Str_Landed_Head", "Sig_Str_Attempted_Head", "Sig_Str_Landed_Leg", "Sig_Str_Attempted_Leg", 
        "Sig_Str_Landed_Clinch", "Sig_Str_Attempted_Clinch", "Sig_Str_Landed_Distance", "Sig_Str_Attempted_Distance", "Sig_Str_Landed_Ground", "Sig_Str_Attempted_Ground"
        ]

    columns_to_calculate_totals = ["Wins", "Losses", "Draws", "Total_Fights", "Win_Streak", "Lose_Streak", "Experience_Years", "Days_Since_Last_Fight"]
    

    # Filter 'df_fights' for previous fights where this fighter participated
    df_fights_filtered = df_fights[
        ((df_fights["Fighter_A_Name"] == fighter_name) | (df_fights["Fighter_B_Name"] == fighter_name)) 
        & 
        (pd.to_datetime(df_fights["Date"], errors='coerce') < pd.to_datetime(date, errors='coerce'))
    ].sort_values(by="Date", ascending=False).reset_index(drop=True)
    
    # If fighter has no previous fights -> debut case
    if df_fights_filtered.empty:
        totals_dict = {**{col: 0 for col in columns_to_calculate_totals[:-1]}, **{"Days_Since_Last_Fight": None}}
    else:
        last_fight = df_fights_filtered.iloc[0]
        # Determine if fighter was in A or B corner and update stats accordingly
        if last_fight["Fighter_A_Name"] == fighter_name:
            if last_fight["Winner_A"] == 1:
                # Fighter A won last fight: 
                    # Wins and Win_Streak adds 1
                    # Losses and Draws stay the same
                    # Lose_Streak resets to 0
                totals_dict = {
                    "Wins": last_fight["Fighter_A_Wins"] + 1,
                    "Losses": last_fight["Fighter_A_Losses"],
                    "Draws": last_fight["Fighter_A_Draws"],
                    "Win_Streak": last_fight["Fighter_A_Win_Streak"] + 1,
                    "Lose_Streak": 0
                }
            else:
                # Fighter A lost last fight
                    # Wins and Draws stay the same
                    # Losses and Lose_Streak adds 1
                    # Win_Streak resets to 0
                totals_dict = {
                    "Wins": last_fight["Fighter_A_Wins"],
                    "Losses": last_fight["Fighter_A_Losses"] + 1,
                    "Draws": last_fight["Fighter_A_Draws"],
                    "Win_Streak": 0,
                    "Lose_Streak": last_fight["Fighter_A_Lose_Streak"] + 1,
                }
            # Total_Fights always adds 1
            totals_dict["Total_Fights"] = last_fight["Fighter_A_Total_Fights"] + 1
        
        else:               # If the fighter is the fighter B in the last fight
            if last_fight["Winner_A"] == 0:
                # Fighter B won last fight
                    # Wins and Win_Streak adds 1
                    # Losses and Draws stay the same
                    # Lose_Streak resets to 0
                totals_dict = {
                    "Wins": last_fight["Fighter_B_Wins"] + 1,
                    "Losses": last_fight["Fighter_B_Losses"],
                    "Draws": last_fight["Fighter_B_Draws"],
                    "Win_Streak": last_fight["Fighter_B_Win_Streak"] + 1,
                    "Lose_Streak": 0,
                }
            else:
            # Fighter B lost last fight
                # Wins and Draws stay the same
                # Losses and Lose_Streak adds 1
                # Win_Streak resets to 0
                totals_dict = {
                    "Wins": last_fight["Fighter_B_Wins"],
                    "Losses": last_fight["Fighter_B_Losses"] + 1,
                    "Draws": last_fight["Fighter_B_Draws"],
                    "Win_Streak": 0,
                    "Lose_Streak": last_fight["Fighter_B_Lose_Streak"] + 1,
                }
            # Total_Fights always adds 1
            totals_dict["Total_Fights"] = last_fight["Fighter_B_Total_Fights"] + 1
        
        # Compute experience in years and time since last fight
        totals_dict["Experience_Years"] = (pd.to_datetime(date, errors='coerce') - pd.to_datetime(df_fights_filtered.iloc[-1]["Date"], errors='coerce')).days / 365
        totals_dict["Days_Since_Last_Fight"] = (pd.to_datetime(date, errors='coerce') - pd.to_datetime(last_fight["Date"], errors='coerce')).days

    # Return combined averages + totals + debut flag
    if df_fights_filtered.empty:
        return {**{col: 0 for col in columns_to_calculate_mean}, **totals_dict, **{"Is_Debut": 1}} 
    return {**fighter_past_fights[columns_to_calculate_mean].mean().to_dict(), **totals_dict, **{"Is_Debut": 0}}

def get_upcoming_fights(url):
    """
    Collects and merges all relevant data for upcoming fights:
    - Event metadata (date, location, season)
    - Fighters' historical statistics
    - Fight-specific details (weight class, title bout, etc.)

    Args:
        url (str): UFC upcoming events URL.

    Returns:
        pd.DataFrame: Dataset of all upcoming fights ready for prediction.
    """
    
    event_link, event_date, event_location = get_next_event_link(url)
    fights_links = get_next_event_fights_links(event_link)
    
    upcoming_fights = []
    
    for fight_link in fights_links:
        fight_data = scrape_future_fight(fight_link, event_date)
        location_data = prepare_location(event_location)
        season = prepare_season(event_date)
        
        # Core fight info shared by both fighters
        general_columns = {
            "Fighter_A_Name": fight_data["Fighter_A_Name"],
            "Fighter_B_Name": fight_data["Fighter_B_Name"],
            "Date": event_date,
            "Weight_Class": fight_data["Weight_Class"],
            "Title_Bout": fight_data["Title_Bout"],
            "Referee": None,
            "Location": event_location,
            "Country": location_data["Country"],
            "Continent": location_data["Continent"],
            "Season": season,
            "N_Rounds": None,
            "Max_Time": None,
            "Method": None,
            "Round": None,
            "Time": None,
            "Time_format": None,
        }

        # Historical data for each fighter (prefix A or B)
        fighter_a_data = fighter_historical_stats(fight_data["Fighter_A_Name"], event_date)
        fighter_b_data = fighter_historical_stats(fight_data["Fighter_B_Name"], event_date)
        
        fighter_a_data = {f"Fighter_A_{k}": v for k, v in fighter_a_data.items()}
        fighter_b_data = {f"Fighter_B_{k}": v for k, v in fighter_b_data.items()}

        # Merge all into one fight record
        full_fight_data = {**general_columns, **fighter_a_data, **fighter_b_data, **{"Winner_A": None}}
        upcoming_fights.append(full_fight_data)
    
    return pd.DataFrame(upcoming_fights)


def main(url, output_file="data/upcoming_fights.csv"):
    """
    Main entry point for preparing upcoming UFC fight data.
    Combines all helper functions and exports the result to CSV.

    Args:
        url (str): UFC upcoming events URL.
        output_file (str): Output path for the resulting CSV.
    
    Returns:
        pd.DataFrame or None: Returns DataFrame on success, None on error.
    """
    
    print("........................................")
    print("Preparing upcoming UFC fights...")

    try:
        df_upcoming = get_upcoming_fights(url)
        df_upcoming.to_csv(output_file, index=False)
        
        print(f"Upcoming fights data prepared and saved to '{output_file}'.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

    return df_upcoming

if __name__ == "__main__":
    main()

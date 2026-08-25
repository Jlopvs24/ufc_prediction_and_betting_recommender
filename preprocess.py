import pandas as pd

def mix_columns(df):
    """
    Merge the fighter-specific columns into a unified structure based on who the current fighter is.

    This function determines whether each row corresponds to Fighter A or Fighter B and merges
    their respective statistics into a single standardized format.

    Args:
        df (pd.DataFrame): Original DataFrame containing both Fighter A and Fighter B columns.

    Returns:
        pd.DataFrame: Cleaned DataFrame with unified fighter statistics and general fight info.
    """
    
    df["is_fighter_A"] = df["Name"] == df["Fighter_A_Totals_Fighter"]
    
    fighter_a_cols = [c for c in df.columns if c.startswith("Fighter_A_")]
    fighter_b_cols = [c for c in df.columns if c.startswith("Fighter_B_")]
    
    clean_stats = pd.DataFrame(index=df.index)

    # Merge stats from A/B depending on who the fighter is
    for col_a, col_b in zip(sorted(fighter_a_cols), sorted(fighter_b_cols)):
        new_col = col_a.replace("Fighter_A_", "").replace("Fighter_B_", "")
        clean_stats[new_col] = df[col_a].where(df["is_fighter_A"], df[col_b])
        
    general_cols = ["Name","Opponent","Win","Weight_Class","Title_Bout","Method","Round","Time","Time_format","Referee","Date","Location"]
    final_df = pd.concat([df[general_cols], clean_stats], axis=1)

    return final_df

def categorize_weight_class(row):
    """
    Assign the correct weight class category or 'Other' if unknown.
    """
    l = ["Featherweight", "Flyweight", "Lightweight", "Catch Weight", "Bantamweight", "Welterweight", "Middleweight", "Light Heavyweight", "Heavyweight",
        "Women's Strawweight", "Women's Flyweight", "Women's Bantamweight", "Women's Featherweight"]
    if row["Weight_Class"] in l:
        return row["Weight_Class"]
    return "Other"

def categorize_method(row):
    """
    Categorize the fight-ending method into standard groups.
    """
    if "KO" in row["Method"] or "TKO" in row["Method"]:
        return "KO/TKO"
    elif "Decision" in row["Method"]:
        return "Decision"
    elif "Submission" in row["Method"]:
        return "Submission"
    else:
        return "Other"

def convert_time_to_seconds(row):
    """
    Convert the fight time (MM:SS format) into total seconds.
    """
    if pd.isnull(row["Time"]):
        return None
    try:
        minutes, seconds = map(int, row["Time"].split(":"))
        return minutes * 60 + seconds
    except:
        return None

def create_rounds_max_time(row):
    """
    Extract number of rounds and max fight time from the 'Time_format' column.
    Example: '3 Rnd (5-5-5)' -> N_Rounds=3, Max_Time=15
    """
    
    if row['Time_format'] == "No_Time_Limit":
        row['N_Rounds'], row['Max_Time'] = 0, 0
        return row

    rounds = row["Time_format"].split("(")[1].replace(")", "").split("-")
    row['N_Rounds'], row['Max_Time'] = int(len(rounds)), int(sum([int(v) for v in rounds]))
    return row

def month_to_season(month):
    """
    Convert a month number into a season name.
    """
    if month in [12, 1, 2]:
        return "Winter"
    elif month in [3, 4, 5]:
        return "Spring"
    elif month in [6, 7, 8]:
        return "Summer"
    elif month in [9, 10, 11]:
        return "Fall"

def preprocess_date_column(df):
    """
    Clean the 'Date' column and derive the 'Season' column.
    """
    df['Date'] = df['Date'].str.replace("Date:", "").str.strip()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Season'] = df['Date'].dt.month.apply(month_to_season)

    return df

def country_to_continent(country):
    """
    Map countries to their respective continents.
    """
    country_to_continent = {
    'USA': 'North America',
    'United States': 'North America',
    'Canada': 'North America',
    'Mexico': 'North America',
    'Puerto Rico': 'North America',

    'Brazil': 'South America',
    'Argentina': 'South America',
    'Chile': 'South America',
    'Uruguay': 'South America',

    'United Kingdom': 'Europe',
    'France': 'Europe',
    'Germany': 'Europe',
    'Sweden': 'Europe',
    'Poland': 'Europe',
    'Czech Republic': 'Europe',
    'Ireland': 'Europe',
    'Croatia': 'Europe',
    'Denmark': 'Europe',
    'Netherlands': 'Europe',
    'Russia': 'Europe',

    'China': 'Asia',
    'Japan': 'Asia',
    'Singapore': 'Asia',
    'Philippines': 'Asia',
    'South Korea': 'Asia',
    'United Arab Emirates': 'Asia',
    'Saudi Arabia': 'Asia',
    'Azerbaijan': 'Asia',

    'Australia': 'Oceania',
    'New Zealand': 'Oceania',
}
    return country_to_continent.get(country, 'Other')

def preprocess_location(df):
    """
    Clean the 'Location' column, extract the country and assign the continent.
    """
    df['Location'] = df['Location'].str.replace("Location:", "").str.strip()
    location_split = df['Location'].str.split(',',n = 2, expand=True)
    df['Country'] = location_split[2].str.strip()
    df['Country'] = df['Country'].fillna(location_split[1].str.strip())
    df['Continent'] = df['Country'].apply(country_to_continent)
    return df

def preprocess_sig_str(df):
    """
    Split the 'Totals_Sig_str' column into landed and attempted significant strikes.
    """
    df[['Sig_Str_Landed', 'Sig_Str_Attempted']] = df['Totals_Sig_str'].str.split(' of ', expand=True)
    df['Sig_Str_Landed'] = df['Sig_Str_Landed'].astype(int)
    df['Sig_Str_Attempted'] = df['Sig_Str_Attempted'].astype(int)
    df.drop(['Totals_Sig_str'], axis=1, inplace=True)
    return df

def preprocess_of_variables(df):
    """
    Split multiple 'Significant_Strikes_*' columns into 'landed' and 'attempted' pairs.
    """
    l = ['Significant_Strikes_Body', 'Significant_Strikes_Head', 'Significant_Strikes_Leg', 'Significant_Strikes_Clinch', 'Significant_Strikes_Distance', 'Significant_Strikes_Ground']
    
    for col in l:
        name_splitted = col.split('_')
        new_landed_name = f"Sig_Str_Landed_{name_splitted[-1]}"
        new_attempted_name = f"Sig_Str_Attempted_{name_splitted[-1]}"
        df[new_landed_name] = df[col].str.split(' of ', expand=True)[0].astype(int)
        df[new_attempted_name] = df[col].str.split(' of ', expand=True)[1].astype(int)
        df.drop([col], axis=1, inplace=True)
    return df

def preprocess_total_str(df):
    """
    Split 'Totals_Total_str' into landed and attempted total strikes.
    """
    col_splitted = df['Totals_Total_str'].str.split(' of ', expand=True)
    df['Totals_Str_Landed'] = col_splitted[0].astype(int)
    df['Totals_Str_Attempted'] = col_splitted[1].astype(int)
    df.drop(['Totals_Total_str'], axis=1, inplace=True)
    return df

def ctrl_to_sec(s):
    """
    Convert control time from MM:SS to total seconds.
    """
    if pd.isna(s) or s in ["0:00", '--', '---']:
        return 0
    else:
        minutes, seconds = map(int, s.split(':'))
        return minutes * 60 + seconds

def preprocess_totals(df):
    """
    Clean and convert numeric totals (KD, Rev, Sub_att, Ctrl, Td_Pct).
    """
    l = ['Totals_KD', 'Totals_Rev', 'Totals_Sub_att']
    df[l] = df[l].fillna(0).astype(int)

    df['Totals_Ctrl_Sec'] = df['Totals_Ctrl'].apply(ctrl_to_sec)
    df.drop('Totals_Ctrl', axis=1, inplace=True)
    
    df['Totals_Td_Pct'] = df['Totals_Td_Pct'].str.replace('---', '0%').str.replace('--', '0%').str.replace('%', '').astype(float) / 100
    
    return df

def prepare_data(df_initial = pd.read_csv("data/all_ufc_data_raw.csv")):
    """
    Complete UFC dataset preprocessing pipeline.
    
    Steps:
        1. Merge fighter A/B columns into one.
        2. Drop incomplete fight stats.
        3. Categorize weight class and fight method.
        4. Parse and transform time data.
        5. Extract date/season and location info.
        6. Clean and split striking and control stats.
    
    Args:
        df_initial (pd.DataFrame): Raw UFC data.

    Returns:
        pd.DataFrame: Fully preprocessed dataset.
    """
    
    df = df_initial.copy()
    
    df = mix_columns(df)
    
    # Drop fights missing core strike stats
    columns = [c for c in df.columns if c.startswith('Totals_') or c.startswith('Significant_Strikes_')]
    df.dropna(subset=columns, inplace=True)

    df["Weight_Class"] = df.apply(categorize_weight_class, axis=1)
    df["Method"] = df.apply(categorize_method, axis=1)
    df['Time'] = df.apply(convert_time_to_seconds, axis=1)
    df = df.apply(create_rounds_max_time, axis=1)
    df = preprocess_date_column(df)
    df = preprocess_location(df)
    
    df.drop(['Significant_Strikes_Fighter', 'Totals_Fighter', 'Significant_Strikes_Sig_str', 'Significant_Strikes_Sig_str_Pct', 'Totals_Sig_str_Pct'], axis=1, inplace=True)

    df = preprocess_sig_str(df)
    df = preprocess_of_variables(df)
    df = preprocess_total_str(df)
    df = preprocess_totals(df)

    return df

def main(input_file="data/all_ufc_data_raw.csv", output_file="data/all_ufc_data_processed.csv"):
    """
    Entry point for UFC data preprocessing pipeline.
    
    Reads the raw dataset, applies the full transformation pipeline, and saves the output.
    """
    
    print("........................................")
    print("Starting UFC data preprocessing...")
    print(f"Loading raw UFC data from '{input_file}'...")
    
    try:
        df_raw = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: The input file '{input_file}' was not found.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while reading the CSV: {e}")
        return None

    print("Preprocessing UFC data...")
    try:
        df_processed = prepare_data(df_raw)
        df_processed.to_csv(output_file, index=False)
        print(f"Processed UFC data saved to '{output_file}'.")
    except Exception as e:
        print(f"An unexpected error occurred during preprocessing: {e}")
        return None

    return df_processed

if __name__ == "__main__":
    main()
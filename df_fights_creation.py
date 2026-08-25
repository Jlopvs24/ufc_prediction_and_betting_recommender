import pandas as pd

pd.set_option('future.no_silent_downcasting', True)

def add_record_features(prefix, past, fight_date):
    """
    Compute fighter record and experience-related features.

    This function extracts summary statistics from a fighter's past fights:
    wins, losses, draws, streaks, experience, and activity level.
    It is used to create contextual features that represent a fighter's
    performance history prior to a given fight.

    Parameters
    ----------
    prefix : str
        Prefix used for the feature names (it should be "Fighter_A" or "Fighter_B").
    past : pandas.DataFrame
        DataFrame containing all past fights of the fighter before the given date.
    fight_date : str or datetime
        Date of the current fight (used to compute experience and inactivity).

    Returns
    -------
    dict
        Dictionary mapping feature names to their computed values.
    """
    
    # Basic record stats
    wins = (past["Win"] == 1).sum()
    losses = (past["Win"] == 0).sum()
    draws = (past["Method"].str.lower() == "draw").sum() if "Method" in past else 0
    total_fights = len(past)

    # Compute win/lose streak based on chronological order
    streak = 0
    if total_fights > 0:
        last_results = past.sort_values("Date")["Win"].tolist()
        for result in reversed(last_results):
            # Positive streak → consecutive wins
            if result == 1:
                if streak >= 0:
                    streak += 1
                else:
                    break
            # Negative streak → consecutive losses
            elif result == 0:
                if streak <= 0:
                    streak -= 1
                else:
                    break

    # Compute experience and time since last fight
    if total_fights > 0:
        first_fight = past["Date"].min()
        last_fight = past["Date"].max()
        exp_years = (pd.to_datetime(fight_date) - pd.to_datetime(first_fight)).days / 365
        days_since_last = (pd.to_datetime(fight_date) - pd.to_datetime(last_fight)).days
    else:
        exp_years = 0
        days_since_last = None

    return {
            f"{prefix}_Wins": wins,
            f"{prefix}_Losses": losses,
            f"{prefix}_Draws": draws,
            f"{prefix}_Total_Fights": total_fights,
            f"{prefix}_Win_Streak": max(streak, 0),
            f"{prefix}_Lose_Streak": abs(min(streak, 0)),
            f"{prefix}_Experience_Years": exp_years,
            f"{prefix}_Days_Since_Last_Fight": days_since_last
            }

def build_df_fights(df_preprocess = "data/all_ufc_data_processed.csv"):
    """
    Build the main fights DataFrame by combining fighter statistics, history, and outcomes.

    This function takes the preprocessed UFC dataset (fighter-level data per fight)
    and aggregates it into a structured fight-level dataset.
    Each row in the resulting DataFrame corresponds to one fight between two fighters,
    containing both historical averages and contextual features.

    Parameters
    ----------
    df_preprocess : str or pandas.DataFrame, optional
        File path to the preprocessed dataset or the DataFrame itself (default: CSV path).

    Returns
    -------
    pandas.DataFrame or None
        A DataFrame containing all fight-level features, or None if an error occurs.
    """
    
    # Load DataFrame if a file path is provided
    if isinstance(df_preprocess, str):
        try:
            df_preprocess = pd.read_csv(df_preprocess)
        except FileNotFoundError:
            print(f"Error: The input file '{df_preprocess}' was not found.")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while reading the file: {e}")
            return None
    
    # Ensure chronological order for streaks and experience computation
    df_preprocess = df_preprocess.sort_values("Date").reset_index(drop=True)

    fights_data, seen_fights = [], set()

    # Iterate through fighters and pair them using the "Opponent" field
    for _, row_A in df_preprocess.iterrows():
        
        name_A, name_B, fight_date = row_A["Name"], row_A["Opponent"], row_A["Date"]
        # Create a unique fight identifier (independent of fighter order)
        fight_key = tuple(sorted([name_A, name_B]) + [fight_date])
        
        # Skip duplicate fights
        if fight_key in seen_fights:
            continue
        
        # Find the matching row for the opponent
        match = df_preprocess[
            (df_preprocess["Name"] == name_B) & 
            (df_preprocess["Opponent"] == name_A) & 
            (df_preprocess["Date"] == fight_date)
        ]

        if match.empty:
            continue        # Skip if the opponent row was not found
        
        # Register the fight to avoid duplicates
        seen_fights.add(fight_key)

        # Core fight information
        fight_info = {
            "Fighter_A_Name": name_A,
            "Fighter_B_Name": name_B,
            "Date": fight_date,
            "Weight_Class": row_A["Weight_Class"],
            "Title_Bout": row_A["Title_Bout"],
            "Referee": row_A["Referee"],
            "Location": row_A["Location"],
            "Country": row_A["Country"],
            "Continent": row_A["Continent"],
            "Season": row_A["Season"],
            "N_Rounds": row_A["N_Rounds"],
            "Max_Time": row_A["Max_Time"],
            "Method": row_A["Method"],
            "Round": row_A["Round"],
            "Time": row_A["Time"],
            "Time_format": row_A["Time_format"]
        }

        # Retrieve all past fights for each fighter (before current date)
        past_A = df_preprocess[(df_preprocess["Name"] == name_A) & (df_preprocess["Date"] < fight_date)]
        past_B = df_preprocess[(df_preprocess["Name"] == name_B) & (df_preprocess["Date"] < fight_date)]

        # Statistical columns to compute historical averages
        stats_cols = ['Totals_KD','Totals_Rev','Totals_Sub_att','Totals_Td_Pct',
                    'Sig_Str_Landed','Sig_Str_Attempted','Sig_Str_Landed_Body',
                    'Sig_Str_Attempted_Body','Sig_Str_Landed_Head','Sig_Str_Attempted_Head',
                    'Sig_Str_Landed_Leg','Sig_Str_Attempted_Leg','Sig_Str_Landed_Clinch',
                    'Sig_Str_Attempted_Clinch','Sig_Str_Landed_Distance','Sig_Str_Attempted_Distance',
                    'Sig_Str_Landed_Ground','Sig_Str_Attempted_Ground','Totals_Str_Landed',
                    'Totals_Str_Attempted','Totals_Ctrl_Sec']

        # Compute mean statistics from fighter history (NaN if no previous fights)
        mean_A = past_A[stats_cols].mean()
        mean_B = past_B[stats_cols].mean()

        # Add averaged stats to fight info, prefixing by fighter
        for col in stats_cols:
            fight_info[f"Fighter_A_{col}"] = mean_A[col]
            fight_info[f"Fighter_B_{col}"] = mean_B[col]

        # Add record-based and experience features
        fight_info.update(add_record_features("Fighter_A", past_A, fight_date))
        fight_info.update(add_record_features("Fighter_B", past_B, fight_date))

        # Outcome label: 1 if Fighter A won, 0 otherwise
        fight_info["Winner_A"] = 1 if row_A["Win"] == 1 else 0   # o puedes usar el de row_B

        fights_data.append(fight_info)
    
    # Convert accumulated fight data into a DataFrame
    df = pd.DataFrame(fights_data)

    # Identify debut fighters (no past fight stats available)
    df["Fighter_A_Is_Debut"] = df[["Fighter_A_Totals_KD", "Fighter_A_Totals_Str_Landed", "Fighter_A_Totals_Ctrl_Sec"]].isna().all(axis=1).astype(int)
    df["Fighter_B_Is_Debut"] = df[["Fighter_B_Totals_KD", "Fighter_B_Totals_Str_Landed", "Fighter_B_Totals_Ctrl_Sec"]].isna().all(axis=1).astype(int)
    
    # Replace NaN values with zeros for modeling compatibility
    df = df.fillna(0)

    return df

def main():
    """
    Entry point for generating and saving the fight-level dataset.

    This function builds the fights DataFrame using `build_df_fights()`
    and saves it to disk as 'data/df_fights.csv'. It includes exception handling
    to ensure safe execution.
    """
    
    print("........................................")
    print("Starting df_fights creation process...")
    print(f"Building fights DataFrame called 'df_fights' from 'data/all_ufc_data_processed'...")

    try:
        df_fights = build_df_fights()
        df_fights.to_csv("data/df_fights.csv", index=False)
        
        print(f"Fights DataFrame created and saved to 'data/df_fights.csv'.")
    
    except Exception as e:
        
        print(f"An unexpected error occurred: {e}")
        return None

    return df_fights

if __name__ == "__main__":
    main()
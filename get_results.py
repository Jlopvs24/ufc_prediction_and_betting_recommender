import pandas as pd

def calculate_results():
    """
    Reads the historical predictions file and computes model and betting performance metrics.
    Displays accuracy, precision by fighter, betting ROI, hit rate, expected and real EV, 
    and streak information.
    
    This function assumes the file 'data/historical_predictions.csv' contains the following columns:
        - Date, Winner_A_Predicted, Winner_A, Bet, Bet_EV, Bet_Fighter_A, Odds_A, Odds_B, Stake_Amount, Profit
    
    Returns:
        None
    """
    
    print("Reading historical predictions...")
    try:
        df = pd.read_csv("data/historical_predictions.csv")
    except FileNotFoundError:
        print("Error: The file 'data/historical_predictions.csv' was not found. You need to run the update script first.")
        return
    except Exception as e:
        print(f"An unexpected error occurred while reading the file: {e}")
        return

    print("Analyzing historical predictions and calculating metrics...")
    
    # Keep only past fights
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
    df = df[df['Date'] < pd.Timestamp.today().date()]
    
    if len(df) == 0:
        print("No past predictions found in the historical data, so there are no metrics available.")
        return
    
    # --- MODEL PERFORMANCE METRICS ---
    total_preds = len(df[df['Bet'] != 'No Bet'])
    correct_preds = (df["Winner_A_Predicted"] == df["Winner_A"]).sum()
    accuracy = correct_preds / total_preds if total_preds > 0 else 0

    # Precision by predicted winner (A or B)
    preds_A = df[df["Winner_A_Predicted"] == 1]
    preds_B = df[df["Winner_A_Predicted"] == 0]

    precision_A = (preds_A["Winner_A"] == 1).mean() if len(preds_A) > 0 else 0
    precision_B = (preds_B["Winner_A"] == 0).mean() if len(preds_B) > 0 else 0

    # --- BETTING PERFORMANCE METRICS ---
    bets = df[df["Bet"] != 'No Bet'].copy()
    num_bets = len(bets)
    stake_total = bets["Stake_Amount"].sum()

    # Calculate profit/loss per bet
    def bet_outcome(row):
        """
        Compute profit or loss for a given bet depending on the predicted and actual winner.
        Returns positive profit for a correct bet, negative for a loss.
        """
        if row["Bet_Fighter_A"] == 1:  # Bet on Fighter A
            if row["Winner_A"] == 1:
                return row["Stake_Amount"] * (row["Odds_A"] - 1)
            else:
                return -row["Stake_Amount"]
        else:  # Bet on Fighter B
            if row["Winner_A"] == 0:
                return row["Stake_Amount"] * (row["Odds_B"] - 1)
            else:
                return -row["Stake_Amount"]

    bets["Profit"] = bets.apply(bet_outcome, axis=1)

    # Aggregate performance
    profit_total = bets["Profit"].sum()
    roi = profit_total / stake_total if stake_total > 0 else 0
    hit_rate = (bets["Profit"] > 0).mean() if num_bets > 0 else 0

    # Expected vs. real EV comparison
    ev_expected = bets["Bet_EV"].mean() if num_bets > 0 else 0
    ev_real = (profit_total / stake_total) if stake_total > 0 else 0

    # --- STREAK CALCULATION ---
    max_losing_streak, max_winning_streak = 0, 0
    current_streak, current_type = 0, None
    
    for outcome in bets["Profit"]:
        # Update current streak depending on profit outcome
        if outcome > 0:
            if current_type == 'Win':
                current_streak += 1
            else:
                current_type = 'Win'
                current_streak = 1
            max_winning_streak = max(max_winning_streak, current_streak)
        elif outcome < 0:
            if current_type == 'Lose':
                current_streak += 1
            else:
                current_type = 'Lose'
                current_streak = 1
            max_losing_streak = max(max_losing_streak, current_streak)
        else:
            current_type = None
            current_streak = 0
    
    current_streak_length, current_streak_type = current_streak, current_type

    # --- DISPLAY RESULTS ---
    print("======= Model Results =======")
    print(f"Accuracy: {accuracy:.2%}")
    print(f"Accuracy on A: {precision_A:.2%}")
    print(f"Accuracy on B: {precision_B:.2%}")

    print("\n===== Betting Results =====")
    print(f"Number of Bets: {num_bets}")
    print(f"Hit rate: {hit_rate:.2%}")
    print(f"Total stake: {stake_total:.2f}")
    print(f"Total profit: {profit_total:.2f}")
    print(f"ROI: {roi:.2%}")
    print(f"Average expected EV: {ev_expected:.3f}")
    print(f"Actual EV: {ev_real:.3f}")
    print(f"Max losing streak: {max_losing_streak}")
    print(f"Max winning streak: {max_winning_streak}")
    print(f"Current streak: {current_streak_length} ({current_streak_type})" if current_streak_type else "Current streak: None")

def show_betting_suggestions():
    """
    Displays betting suggestions for the latest upcoming event based on 
    the 'data/last_predictions.csv' file. It filters only fights with a 
    non-null betting recommendation.
    
    Returns:
    None
    """    
    
    print("Reading last predictions for betting suggestions...")
    try:
        df = pd.read_csv("data/last_predictions.csv")
    except FileNotFoundError:
        print("Error: The file 'data/last_predictions.csv' was not found. You need to run the prediction script first.")
        return
    except Exception as e:
        print(f"An unexpected error occurred while reading the file: {e}")
        return

    # Filter fights with valid bets
    df = df[df['Bet'] != 'No Bet']
    if df.empty:
        print("No betting suggestions available in the last predictions.")
        return

    print("Betting Suggestions for Upcoming Event:")
    for _, row in df.iterrows():
        print(f"For the fight between {row['Fighter_A_Name']} and {row['Fighter_B_Name']} on {row['Date']}: Bet on {row['Bet']} with expected value {row['Bet_EV']:.3f} and {row['Bet_Risk']} risk.")

if __name__ == "__main__":
    calculate_results()

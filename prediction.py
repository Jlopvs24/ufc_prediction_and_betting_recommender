import pandas as pd, xgboost as xgb, joblib, warnings
from sklearn.model_selection import GridSearchCV

def make_train_model(training_set = pd.read_csv("data/df_fights_with_odds.csv")):
    """
    Train an XGBoost model using historical fight data.

    This function performs preprocessing, one-hot encoding, hyperparameter tuning 
    with GridSearchCV, and saves the best trained model along with the feature column names.
    
    Args:
        training_set (pd.DataFrame, optional): The dataset containing historical fights and outcomes.
            Default loads 'data/df_fights_with_odds.csv'.
    
    Returns:
        bool: True if training and saving were successful.
    """
    
    # Encode categorical features into dummy variables (one-hot encoding)
    training_set = pd.get_dummies(training_set, columns=["Weight_Class", "Continent", "Season"], drop_first=True)
    
    # Define target variable (label) and training features
    y_train = training_set["Winner_A"]
    X_train = training_set.drop(columns=['Fighter_A_Name', 'Fighter_B_Name', 'Date', 'Referee', 'Location', 'Country',
                                'N_Rounds', 'Max_Time', 'Method', 'Round', 'Time', 'Time_format', 'Winner_A', 'fight_id'])
    
    # Create base model with consistent random state for reproducibility
    xgb_model = xgb.XGBClassifier(objective='binary:logistic', eval_metric='logloss', random_state=42)
    
    # Define grid of hyperparameters to search
    param_grid = {
        'n_estimators': [80, 100, 120],
        'learning_rate': [0.01, 0.05, 0.1],
        'max_depth': [3, 4, 5],
        'subsample': [0.7, 0.8, 0.9],
        'colsample_bytree': [0.8, 0.9, 1]
    }

    # Perform 5-fold cross-validation to find best hyperparameters
    grid = GridSearchCV(estimator=xgb_model, param_grid=param_grid, scoring='accuracy', cv=5)
    
    # Train the model with cross-validation
    grid.fit(X_train, y_train)
    
    # Save the best trained model and feature names for later use
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        joblib.dump(grid.best_estimator_, 'model/xgb_model.pkl')
        joblib.dump(X_train.columns, 'model/feature_columns.pkl')
    
    return True

def make_prediction(testing_set = pd.read_csv("data/upcoming_fights.csv")):
    """
    Generate predictions using the trained XGBoost model.

    Args:
        testing_set (pd.DataFrame, optional): Dataset with upcoming fights (no actual outcomes yet).
            Default loads 'data/upcoming_fights.csv'.
    
    Returns:
        pd.DataFrame: A DataFrame containing predicted outcomes and probabilities.
    """
    
    # Load the trained model and training feature columns
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = joblib.load('model/xgb_model.pkl')
        train_columns = joblib.load('model/feature_columns.pkl')
    
    # Encode categorical variables in test data
    testing_set = pd.get_dummies(testing_set, columns=["Weight_Class", "Continent", "Season"], drop_first=True)
    
    # Remove unnecessary columns not used for prediction
    X_test = testing_set.drop(columns=['Fighter_A_Name', 'Fighter_B_Name', 'Date', 'Referee', 'Location', 'Country',
                                'N_Rounds', 'Max_Time', 'Method', 'Round', 'Time', 'Time_format', 'Winner_A'])
    
    # Ensure 'Oddss_A' and 'Odds_B' are numeric
    X_test['Odds_A'] = pd.to_numeric(X_test['Odds_A'], errors='coerce')
    X_test['Odds_B'] = pd.to_numeric(X_test['Odds_B'], errors='coerce')
    
    # Ensure test set columns match training set columns (fill missing with zeros)
    X_test = X_test.reindex(columns=train_columns, fill_value=0)
    
    # Generate predictions and their associated probabilities
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]        # Probability of Fighter A winning

    # Build DataFrame to display results and predictions
    df_predicted = pd.DataFrame({
        'Fighter_A_Name': testing_set['Fighter_A_Name'],
        'Fighter_B_Name': testing_set['Fighter_B_Name'],
        'Date': testing_set['Date'],
        'Odds_A': testing_set['Odds_A'],
        'Odds_B': testing_set['Odds_B'],
        'Winner_A_Predicted': y_pred,
        'Winner_A_Probability': y_pred_proba,
        'Winner_B_Probability': 1 - y_pred_proba
    })

    return df_predicted

def get_odds():
    """
    Retrieve betting odds for each upcoming fight interactively from the user.

    Returns:
        pd.DataFrame: A DataFrame including fight IDs and betting odds entered by the user.
    
    Raises:
        FileNotFoundError: If the file 'data/upcoming_fights.csv' does not exist.
    """
    
    try:
        df_prepared = pd.read_csv("data/upcoming_fights.csv")
    except FileNotFoundError:
        raise FileNotFoundError("The file data/upcoming_fights.csv does not exist.")
    
    df_prepared['Date'] = pd.to_datetime(df_prepared['Date'], errors='coerce')
    df_prepared['fight_id'], df_prepared['Odds_A'], df_prepared['Odds_B'] = None, None, None
    
    # Loop through each fight and ask the user for betting odds
    for _, row in df_prepared.iterrows():
        print(f"Fight between {row['Fighter_A_Name']} and {row['Fighter_B_Name']} on {row['Date']}")
        while True:
            try:
                # Input validation: odds must be > 1
                odds_a = float(input(f"Enter the betting odds for {row['Fighter_A_Name']}: "))
                odds_b = float(input(f"Enter the betting odds for {row['Fighter_B_Name']}: "))
                if odds_a <= 1 or odds_b <= 1:
                    print("Odds must be greater than 1. Please try again.")
                    continue
                break
            except ValueError:
                print("Invalid input. Please enter numeric values for the odds.")
        
        # Create a unique fight ID for each matchup
        fighter_a = str(row['Fighter_A_Name'].strip().replace(" ", "_").lower())
        fighter_b = str(row['Fighter_B_Name'].strip().replace(" ", "_").lower())
        date_str = row['Date'].strftime("%Y_%m_%d") if pd.notnull(row['Date']) else "unknown_date"
        fight_id = f"{fighter_a}-{fighter_b}-{date_str}"
        
        # Store odds and ID in the DataFrame
        df_prepared.loc[_, 'fight_id'] = fight_id
        df_prepared.loc[_, 'Odds_A'] = odds_a
        df_prepared.loc[_, 'Odds_B'] = odds_b

    return df_prepared

def make_betting_suggestions(df_with_odds, bankroll=100):
    """
    Generate betting suggestions based on expected value (EV) and risk level.

    Args:
        df_with_odds (pd.DataFrame): DataFrame with predicted probabilities and betting odds.
        bankroll (float, optional): Total bankroll for bet sizing. Default is 100.

    Returns:
        pd.DataFrame: DataFrame including suggested bets, EV, risk category, and stake amount.
    """
    
    df = df_with_odds.copy()

    # Calculate Expected Value (EV) for both fighters
    df['Expected_Value_A'] = df['Winner_A_Probability'] * df['Odds_A'] - 1
    df['Expected_Value_B'] = df['Winner_B_Probability'] * df['Odds_B'] - 1

    # Define logic to select which fighter to bet on
    def select_bet(row, th = 1, m = 0.5, bankroll = bankroll):
        """
        Decide which fighter to bet on based on expected value and probability thresholds.
        Returns the selected fighter, EV, encoded bet (1 for A, 0 for B), and risk level.
        """
        ev_a, ev_b = row['Expected_Value_A'], row['Expected_Value_B']
        p_a, p_b = row['Winner_A_Probability'], row['Winner_B_Probability']
        
        # Risk category determination based on EV margin
        def bet_risk(ev):
            if ev <= th:
                return 'No Bet'
            elif ev >= th * 1.6:
                return 'Low'
            elif ev >= th * 1.3:
                return 'Medium'
            else:
                return 'High'

        # Conditional logic for selecting bets
        if ev_a <= 0 and ev_b <= 0:
            # Neither fighter has positive EV → skip bet
            return 'No Bet', 0, 'No Bet', 'No Bet'
        if ev_a >= ev_b and ev_a > th and p_a > m:
            # Fighter A has better EV than Fighter B, EV is greater than minimum, and sufficient win probability
            return row['Fighter_A_Name'], ev_a, 1, bet_risk(ev_a)
        elif ev_b > ev_a and ev_b > th and p_b > m:
            # Fighter B has better EV than Fighter A, EV is greater than minimum, and sufficient win probability
            return row['Fighter_B_Name'], ev_b, 0, bet_risk(ev_b)
        else:
            # No favorable bet found
            return 'No Bet', 0, 'No Bet', 'No Bet'

    # Apply bet selection to each row and unpack results into new columns
    bet_info = df.apply(select_bet, axis=1, result_type='expand')
    df['Bet'] = bet_info[0]
    df['Bet_EV'] = bet_info[1]
    df['Bet_Fighter_A'] = bet_info[2]
    df['Bet_Risk'] = bet_info[3]

    # Assign stake amount based on risk category
    def select_stake(row, initial_bankroll = bankroll):
        """
        Allocate stake proportionally to risk:
            - Low risk: 30% of bankroll
            - Medium risk: 15% of bankroll
            - High risk: 5% of bankroll
        """
        
        if row['Bet_Risk'] == 'Low':
            return initial_bankroll * 0.3
        elif row['Bet_Risk'] == 'Medium':
            return initial_bankroll * 0.15
        elif row['Bet_Risk'] == 'High':
            return initial_bankroll * 0.05
        return 0
    
    df['Stake_Amount'] = df.apply(select_stake, axis=1)

    return df

def main(budget = 100):
    """
    Main pipeline to:
        1. Retrieve odds
        2. Generate predictions
        3. Compute betting suggestions
        4. Save results to CSV
    
    Args:
        budget (float, optional): Total budget (bankroll) for betting. Default is 100.
    
    Returns:
        pd.DataFrame: Final DataFrame with all betting suggestions.
    """
        
    print("........................................")
    print(f"Preparing predictions with a budget of {budget}...")

    # Get user-provided betting odds
    df_with_odds = get_odds()
    print("Odds retrieved and merged with predictions successfully.")
    
    # Generate predictions for upcoming fights
    df_predicted = make_prediction(df_with_odds)
    print("Predictions made successfully.")
    
    # Generate betting suggestions using predictions
    df_betting_suggestions = make_betting_suggestions(df_predicted, budget)
    print("Betting suggestions generated successfully.")
    
    # Save the output to CSV for future reference
    df_betting_suggestions.to_csv("data/last_predictions.csv", index=False)
    print("Predictions and betting suggestions saved to data/last_predictions.csv")
    
    return df_betting_suggestions

if __name__ == "__main__":
    main()
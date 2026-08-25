import sys

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from first_webscrape import main as webscrape_main
from preprocess import main as preprocess_main
from df_fights_creation import main as df_fights_main
from prepare_prediction import main as prepare_prediction_main
from prediction import main as prediction_main, make_train_model
from update import main as update_main
from get_results import calculate_results, show_betting_suggestions

def init_driver(headless=True, chrome_version=149):
    """
    Create a Selenium-controlled Chrome driver via undetected-chromedriver.

    Args:
        headless : bool. Run without a visible window.
        chrome_version : int. The version of Chrome to use.
    Returns:
        uc.Chrome: Ready-to-use driver instance.
    """
    
    options = uc.ChromeOptions()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.1 Safari/537.36"
    )

    driver = uc.Chrome(options=options, version_main=chrome_version)
    driver.set_page_load_timeout(30)

    return driver


def menu():
    """
    Display the main menu options for the UFC Data Project.

    This function prints a simple numbered list of available actions
    for the user to choose from. It serves as the interactive interface
    to run different parts of the UFC pipeline (scraping, training, prediction, etc.).
    """
    
    print("\n========== UFC Data Project ===========")
    print("1. Initial setup (webscrape + preprocess + create fights dataframe). Run once. Attention: this may take a while.")
    print("2. Train the prediction model. Run once after initial setup or to retrain the model.")
    print("3. Generate predictions for upcoming fights")
    print("4. Show betting suggestions for upcoming event")
    print("5. Refresh data with new events")
    print("6. Get metrics from past predictions")
    print("7. Exit")

def main():
    """
    Main control loop of the UFC Data Project.

    This function provides an interactive CLI that allows the user to:
    - Run the initial setup (web scraping, preprocessing, fight dataset creation)
    - Train or retrain the prediction model
    - Generate predictions for upcoming fights
    - Display betting suggestions
    - Update existing fight data with new events
    - Calculate performance metrics from past predictions

    The function runs continuously until the user chooses to exit.
    """

    # URLs for scraping UFC event data
    URL_COMPLETED = "http://ufcstats.com/statistics/events/completed?page=all"
    URL_UPCOMING = "http://ufcstats.com/statistics/events/upcoming"
    
    # Initialize the Selenium driver (headless mode)
    try:
        DRIVER = init_driver(headless=True)
    except WebDriverException as e:
        print(f"Error initializing web driver: {e}")
        sys.exit(1)
    
    # Infinite loop for menu-driven interface
    while True:
        menu()
        choice = input("Select an option (1-7): ").strip()
        
        # Option 1: Initial setup (scrape + preprocess + build fight dataframe)
        if choice == "1":
            print("\nStarting initial setup...")
            try:
                webscrape_main(URL_COMPLETED, DRIVER)
                preprocess_main()
                df_fights_main()
                print("Initial setup completed successfully!")
            except Exception as e:
                print(f"Error during initial setup: {e}")
        
        # Option 2: Train or retrain the prediction model
        elif choice == "2":
            print("\nMaking and training the model, this may take a while...")
            try:
                make_train_model()
            except Exception as e:
                print(f"Error training the model: {e}")
        
        # Option 3: Generate predictions for upcoming fights
        elif choice == "3":
            budget_input = input("Enter budget for betting suggestions (default = 100): ").strip()
            budget = float(budget_input) if budget_input else 100
            print(f"\nPreparing upcoming fights and generating predictions with budget: {budget}...")
            try:
                prepare_prediction_main(URL_UPCOMING, DRIVER)
                result = prediction_main(budget=budget)
                print(result[['Fighter_A_Name', 'Fighter_B_Name', 'Date', 'Odds_A', 'Odds_B', 'Winner_A_Probability', 'Bet', 'Bet_EV', 'Bet_Risk']])
            except Exception as e:
                print(f"Error generating predictions: {e}")
        
        # Option 4: Display betting suggestions for next event
        elif choice == "4":
            try:
                show_betting_suggestions()
            except Exception as e:
                print(f"Error retrieving betting suggestions: {e}")

        # Option 5: Update database with newly completed UFC events
        elif choice == "5":
            print("\nRefreshing UFC data with new events...")
            try:
                result = update_main(URL_COMPLETED, DRIVER)
                if result is None:
                    print("No new events found to scrape, data is already refreshed.")
                else:
                    print(result)
            except Exception as e:
                print(f"Error refreshing data: {e}")
        
        # Option 6: Compute model performance metrics on past predictions
        elif choice == "6":
            print("\nCalculating and displaying metrics from past predictions...")
            try:
                calculate_results()
            except Exception as e:
                print(f"Error calculating results: {e}")
        
        # Option 7: Exit program
        elif choice == "7":
            print("Exiting application. Goodbye!")
            sys.exit()

        # Invalid input handling
        else:
            print("Invalid option. Please select a number between 1 and 7.")

if __name__ == "__main__":
    """
    Entry point for the application.

    When the script is run directly, this block executes the main function.
    It also handles graceful termination when the user interrupts the program.
    """
    
    try:
        main()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user. Exiting...")
        sys.exit()
# UFC Fights Prediction & Quantitative Betting Recommender

An end-to-end predictive Machine Learning pipeline and quantitative betting strategy engine designed to forecast UFC fights outcomes, detect market mispricings, and generate positive-EV betting allocations.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![XGBoost](https://img.shields.io/badge/Model-XGBoost-orange.svg)](https://xgboost.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Portfolio](https://img.shields.io/badge/Portfolio-jlopvs24.github.io-blueviolet.svg)](https://jlopvs24.github.io)

---

## 📌 Executive Summary

Sports betting markets frequently suffer from behavioral bias, narrative-driven public action, and inefficient underdog pricing. This project provides a full-stack automated decision system:

1. **Automated Data Ingestion:** Scrapes completed historical fights, bout-by-bout dynamic statistics, fighter biometrics, and opening/closing sportsbook odds via `undetected-chromedriver`.
2. **Feature Engineering Engine:** Constructs contextual differential statistics (strike differential rate, takedown defense sustainability, control time, and reach/age advantage ratios).
3. **Probabilistic Modeling:** Trains an XGBoost classifier with custom thresholding to output calibrated bout outcome probabilities.
4. **Capital Allocation & Betting Simulator:** Uses an interactive terminal CLI (`app.py`) evaluating live fight cards against betting odds to output high-probability, positive Expected Value (`EV > 0`) recommendations—**achieving a 60% historical backtested ROI**.

> **Note on Data Scraping:** The scraping scripts (`first_webscrape.py`, `get_results.py`, `update.py`) extract data from UFCStats endpoints. Due to bot detection mechanisms on live sources, complete pre-scraped and processed datasets are preserved within `/data` for immediate model training and reproducibility.

---

## 🏗 System Architecture & Workflow

```text
[ UFCStats & Odds Endpoints ]
              │
              ▼ (undetected-chromedriver)
      first_webscrape.py / update.py
              │
              ▼
    [ Raw Event & Fighter Data ] (data/all_ufc_data_raw.csv)
              │
              ▼ (Data Cleaning & Imputation)
        preprocess.py
              │
              ▼ (Differential Metrics & Matchup Pairing)
      df_fights_creation.py
              │
              ▼
    [ Processed Matchup Matrix ] (data/all_ufc_data_processed.csv)
              │
              ▼
      prediction.py (make_train_model)
      ├── XGBoost Training & Serialization (model/xgb_model.json)
      └── Out-of-Sample Evaluation & Metric Calculation
              │
              ▼
            app.py (Interactive CLI)
              ├── Live Prediction for Upcoming Events (prepare_prediction.py)
              ├── Budget-Sized EV Betting Suggestions (get_results.py)
              └── Settlement & ROI Tracking
```

---

## 📂 Repository Structure

```text
├── data/
│   ├── all_ufc_data_raw.csv          # Scraped historical bout and fighter metrics
│   ├── all_ufc_data_processed.csv    # Cleaned dataset with computed differentials
│   ├── df_fights_with_odds.csv       # Historical dataset aligned with sportsbook odds
├── model/
│   ├── feature_columns.pkl           # Exact feature matrix schema for inference
│   ├── xgb_model.json                # Serialized XGBoost model (native format)
│   └── xgb_model.pkl                 # Serialized model artifact
├── notebooks/
│   ├── model_evaluation.ipynb        # Calibration, confusion matrices & metrics
│   ├── odds_testing.ipynb            # EV simulation & Kelly Criterion backtests
│   ├── roc_auc_over_time.html        # Interactive AUC stability plot
│   └── walkforward_results.csv       # Out-of-sample backtest records
├── app.py                            # Main interactive CLI orchestrator
├── df_fights_creation.py             # Feature engineering & differential creation
├── first_webscrape.py                # Initial historical scraper
├── get_results.py                    # Settlement verification & betting recommendation engine
├── prediction.py                     # Training logic, inference & EV calculations
├── prepare_prediction.py             # Live scraper and parser for upcoming cards
├── preprocess.py                     # Data cleaning, null handling & standardization
├── update.py                         # Incremental data refresher for new events
└── requirements.txt                  # Python dependencies
```

## 💻 CLI Functionality (`app.py`)

The main entry point provides an interactive command-line interface with 7 modules:

1. **Initial setup:** Executes `first_webscrape.py`, `preprocess.py`, and `df_fights_creation.py` to build the training matrix from scratch.
2. **Train the prediction model:** Trains, tunes, and serializes the XGBoost model artifacts to `/model`.
3. **Generate predictions for upcoming fights:** Scrapes the upcoming card, computes differential metrics, and outputs win probabilities, optimal bet allocation, Expected Value (`Bet_EV`), and risk tiering based on user budget.
4. **Show betting suggestions for upcoming event:** Displays filtered high-conviction value bets.
5. **Refresh data with new events:** Fetches recent fight cards incrementally to keep database updated.
6. **Get metrics from past predictions:** Evaluates model precision, profit/loss, and ROI metrics.
7. **Exit:** Gracefully terminates browser sessions and runtime.

---

## 📊 Key Engineering & Feature Logic

- **Differential Feature Matrix:** Absolute fight statistics are transformed into contextual differentials:
  - Strike Differential Rate (Significant Strikes Landed vs. Absorbed per minute).
  - Takedown Defense and Control-Time Dominance indices.
  - Physical Leverage Metrics (Reach differential, Height differential, Stance matching).
  - Biological Decay & Layoff Penalty (Age differences and inactivity duration).
- **Expected Value (EV) Strategy:** Identifies market mispricing by comparing model predicted probability ($P$) against bookmaker implied probability:
  
  $$\text{EV} = (P \times (\text{Decimal Odds} - 1)) - (1 - P)$$

- **Risk & Capital Management:** Implements fractional Kelly Criterion sizing to optimize bankroll growth while avoiding drawdown risk across out-of-sample events.

---

## 🚀 Getting Started

### 1. Prerequisites & Environment Setup
```bash
git clone https://github.com/Jlopvs24/ufc_prediction_and_betting_recommender.git
cd ufc_prediction_and_betting_recommender

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```


2. Run Application
```bash
python app.py
```

## 📬 Contact & Author

### Juan López Blasco

### [Website](https://jlopvs24.github.io/)

### [Linkedin](https://www.linkedin.com/in/juanlobl/)

### Email: juanlb2410@gmail.com

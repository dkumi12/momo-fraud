# MoMo Fraud Detection

An end-to-end machine learning pipeline for detecting fraudulent mobile money transactions using the PaySim dataset.

## Project Structure

```
MoMo_Fraud_Project/
├── Pay-sim.csv                     # Raw dataset (included)
├── 01_eda.ipynb                    # Exploratory Data Analysis
├── 02_cleaning.ipynb               # Data Cleaning
├── 03_feature_engineering.ipynb    # Feature Engineering
├── 04_modelling.ipynb              # Model Training
├── 05_evaluation.ipynb             # Model Evaluation
├── 06_tuning.ipynb                 # Hyperparameter Tuning
├── data/
│   └── README.md                   # Dataset info
├── models/                         # Saved models (generated after training)
├── requirements.txt
└── README.md
```

## ML Pipeline

| Step | Notebook | What it does |
|------|----------|--------------|
| 1 | `01_eda.ipynb` | Explore raw data, find patterns and fraud signals |
| 2 | `02_cleaning.ipynb` | Remove errors, encode columns, drop ID fields |
| 3 | `03_feature_engineering.ipynb` | Create balance-error features, log transforms |
| 4 | `04_modelling.ipynb` | Train Logistic Regression, Random Forest, XGBoost |
| 5 | `05_evaluation.ipynb` | Compare models using F1, ROC-AUC, confusion matrix |
| 6 | `06_tuning.ipynb` | Tune best model, save final trained model |

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/your-username/momo-fraud.git
cd momo-fraud
```

### 2. Create virtual environment
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac / Linux
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Register Jupyter kernel
```bash
python -m ipykernel install --user --name "momo-fraud" --display-name "Python (momo-fraud)"
```

### 5. Run the notebooks in order
Open VS Code, select the `Python (momo-fraud)` kernel, and run notebooks `01` through `06`.

## Dataset

- **Source:** PaySim Synthetic Mobile Money Transactions
- **Size:** 100,000 transactions
- **Target:** `isFraud` (1 = fraud, 0 = legitimate)
- **Fraud rate:** ~8.2% (imbalanced)

## Techniques Used

- SMOTE for class imbalance
- Winsorization for outlier capping
- Log1p transformation for skewed features
- Balance error feature engineering
- RandomizedSearchCV for hyperparameter tuning

## Results

| Model | F1-Score | ROC-AUC |
|-------|----------|---------|
| Logistic Regression | TBD | TBD |
| Random Forest | TBD | TBD |
| XGBoost (tuned) | TBD | TBD |

*Fill in after running the notebooks.*

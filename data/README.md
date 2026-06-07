# Dataset

## PaySim Mobile Money Transaction Dataset

`Pay-sim.csv` is included in this repository — no download needed.

### Included file
| File | Description | Size |
|------|-------------|------|
| `Pay-sim.csv` | Raw PaySim synthetic mobile money transactions | 100,000 rows, 7.5 MB |

### Generated files
These files are **not** included — they are created automatically when you run the notebooks in order.

| File | Created by | Description |
|------|-----------|-------------|
| `Pay-sim_cleaned.csv` | `02_cleaning.ipynb` | Cleaned dataset |
| `Pay-sim_features.csv` | `03_feature_engineering.ipynb` | Engineered features dataset |
| `models/*.pkl` | `04_modelling.ipynb` and `06_tuning.ipynb` | Trained model files |

### About the dataset
- **Source:** PaySim — a synthetic financial dataset that simulates mobile money transactions
- **Original source:** Kaggle — search `PaySim fraud detection dataset`
- **Target column:** `isFraud` (1 = fraud, 0 = legitimate)
- **Fraud rate:** ~8.2% (imbalanced dataset)

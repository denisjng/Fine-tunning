# Recipe: tabular

## Use when
Data is rows and columns (CSV/parquet) of numbers and categories; target is a class or a number. No neural fine-tuning: gradient boosting wins here.

## Pick the model
- Day-of check (≤15 min): search recent winning solutions for similar tabular competitions; stay with gradient boosting unless the rules or the data clearly favour something else.
- Default: LightGBM.
- Many categorical columns: CatBoost. Ensemble partner: XGBoost.
- Smallest fallback: LightGBM with defaults and 500 trees.

## Starting hyperparameters
- objective from the task: `binary` / `multiclass` / `regression` (match the metric, e.g. `regression_l1` for MAE).
- learning_rate 0.05, num_leaves 31, min_child_samples 20, feature_fraction 0.8, bagging_fraction 0.8, bagging_freq 1.
- n_estimators 5000 with early stopping (100 rounds) on the validation fold.
- Categorical columns as pandas `category` dtype, with the same categories in train and test.

## Script outline
- 5-fold CV (StratifiedKFold for classification, GroupKFold if an entity repeats, time split if test is later). Fold ids saved once to `data/folds.csv` (seed 42) and frozen: this is the val split.
- Out-of-fold score = val score. Test prediction = average of the 5 fold models.

## Levers
1. Drop ID and leaky columns; correct dtypes.
2. learning_rate 0.02 with more trees.
3. Feature engineering: ratios, date parts, group aggregates, count encoding.
4. Class weights or threshold tuning for the metric.
5. Tune num_leaves, min_child_samples, learning_rate, feature_fraction and lambda_l2 with an Optuna search (SKILL.md "Automatic hyperparameter search", run by a helper in parallel).
6. CatBoost / XGBoost and average with LightGBM.
7. Average 3 seeds.

## Crashes
- Category mismatch between train and test → build categories from train+test, `pd.Categorical(..., categories=...)`.
- Val ≫ LB → leakage; switch to group or time split.
- Out of memory → downcast float64 → float32.

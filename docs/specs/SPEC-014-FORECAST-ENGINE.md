# SPEC-014 — Forecast Engine
Candidate models: naive, ARIMA, ARIMA-XREG, TimesFM, XGBoost/custom where justified.
Backtesting computes MAE/MAPE/RMSE/Bias.
Champion promotion requires configured metric gate and approval when production behavior changes.
Store training window, feature version, model artifact and metrics.

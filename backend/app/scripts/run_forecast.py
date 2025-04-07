# run_forecast.py
from app.models.demand_forecast.forecast_service import run_demand_forecast

if __name__ == "__main__":
    print("Starting demand forecasting...")
    results = run_demand_forecast()
    print("Forecasting completed!")
# forecast_runner.py
from app.models.demand_forecast.forecast_service import ForecastService

# Initialize the service
service = ForecastService()

# Run the full forecasting workflow
try:
    print("Starting AI forecasting process...")
    results = service.run_ai_forecast(
        train_models=True, 
        generate_forecasts=True,
        save_to_mongodb=True,
        forecast_horizon=12
    )
    print("Forecasting completed:", results)
except Exception as e:
    print(f"Error in forecasting process: {e}")
    # Log the exception with traceback for debugging
    import traceback
    traceback.print_exc()
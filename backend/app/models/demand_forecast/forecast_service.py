import pandas as pd
import numpy as np
import os
import json
import pickle
import logging
from datetime import datetime
from app.models.database import fetch_data, insert_data
from app.models.demand_forecast.data_processor import DemandDataProcessor
from app.models.demand_forecast.feature_engineering import FeatureEngineer
from app.models.demand_forecast.time_series_models import TimeSeriesModels
from app.models.demand_forecast.ensemble_models import EnsembleForecaster
from app.models.demand_forecast.model_evaluation import ModelEvaluator

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('forecast_service')

class ForecastService:
    """Service class for managing demand forecasting workflows."""
    
    def __init__(self, model_dir='models', data_dir='data'):
        """
        Initialize the forecast service.
        
        Args:
            model_dir (str): Directory to store trained models
            data_dir (str): Directory to store data
        """
        self.model_dir = model_dir
        self.data_dir = data_dir
        
        # Create directories if they don't exist
        os.makedirs(model_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize components
        self.data_processor = DemandDataProcessor()
        self.feature_engineer = FeatureEngineer()
        self.ts_models = TimeSeriesModels()
        self.ensemble_forecaster = EnsembleForecaster()
        self.model_evaluator = ModelEvaluator()
        
        # Model registry to track trained models
        self.model_registry = {}
        
        logger.info("Forecast service initialized")
        
    def load_model_registry(self):
        """
        Load model registry from disk.
        
        Returns:
            bool: True if successful, False otherwise
        """
        registry_path = os.path.join(self.model_dir, 'model_registry.json')
        
        if os.path.exists(registry_path):
            try:
                with open(registry_path, 'r') as f:
                    self.model_registry = json.load(f)
                    
                logger.info(f"Loaded model registry with {len(self.model_registry)} entries")
                return True
                
            except Exception as e:
                logger.error(f"Error loading model registry: {e}")
                return False
        else:
            logger.warning(f"Model registry file not found at {registry_path}")
            return False
            
    def save_model_registry(self):
        """
        Save model registry to disk.
        
        Returns:
            bool: True if successful, False otherwise
        """
        registry_path = os.path.join(self.model_dir, 'model_registry.json')
        
        try:
            with open(registry_path, 'w') as f:
                json.dump(self.model_registry, f, indent=2)
                
            logger.info(f"Saved model registry with {len(self.model_registry)} entries")
            return True
            
        except Exception as e:
            logger.error(f"Error saving model registry: {e}")
            return False
            
    def register_model(self, model_id, model_type, category, specification=None, metrics=None):
        """
        Register a trained model in the registry.
        
        Args:
            model_id (str): Model identifier
            model_type (str): Type of model
            category (str): Category the model is trained for
            specification (str): Product specification the model is trained for
            metrics (dict): Model performance metrics
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            self.model_registry[model_id] = {
                'model_id': model_id,
                'model_type': model_type,
                'category': category,
                'specification': specification,
                'timestamp': timestamp,
                'metrics': metrics
            }
            
            # Save updated registry
            self.save_model_registry()
            
            logger.info(f"Registered model {model_id} for {category} ({model_type})")
            return True
            
        except Exception as e:
            logger.error(f"Error registering model {model_id}: {e}")
            return False
            
    def get_registered_models(self, category=None, model_type=None):
        """
        Get registered models filtered by category and/or model type.
        
        Args:
            category (str): Filter by category
            model_type (str): Filter by model type
            
        Returns:
            dict: Filtered model registry
        """
        filtered_registry = {}
        
        for model_id, info in self.model_registry.items():
            if category and info['category'] != category:
                continue
                
            if model_type and info['model_type'] != model_type:
                continue
                
            filtered_registry[model_id] = info
            
        return filtered_registry
        
    def get_best_model(self, category, metric='rmse'):
        """
        Get the best model for a category based on a metric.
        
        Args:
            category (str): Category to get the best model for
            metric (str): Metric to use for comparison (lower is better)
            
        Returns:
            str: Best model ID
        """
        # Get models for this category
        category_models = self.get_registered_models(category=category)
        
        if not category_models:
            logger.warning(f"No models found for category {category}")
            return None
            
        # Find best model
        best_model = None
        best_metric = float('inf')
        
        for model_id, info in category_models.items():
            if info['metrics'] and metric in info['metrics']:
                current_metric = info['metrics'][metric]
                
                if current_metric < best_metric:
                    best_metric = current_metric
                    best_model = model_id
                    
        if best_model:
            logger.info(f"Best model for {category}: {best_model} with {metric}={best_metric:.4f}")
        else:
            logger.warning(f"No models with metric {metric} found for category {category}")
            
        return best_model
        
    def fetch_training_data(self, start_year=None, end_year=None, categories=None):
        """
        Fetch data for model training.
        
        Args:
            start_year (int): Start year for data
            end_year (int): End year for data
            categories (list): List of categories to fetch data for
            
        Returns:
            pandas.DataFrame: Training data
        """
        logger.info(f"Fetching training data for {categories or 'all categories'} "
                   f"from {start_year or 'earliest'} to {end_year or 'latest'}")
                   
        # Fetch category-level demand data
        category_data = self.data_processor.fetch_historical_data(
            collection="category_monthly_demand",
            start_year=start_year,
            end_year=end_year,
            categories=categories
        )
        
        if category_data is None or len(category_data) == 0:
            logger.warning("No category-level demand data found")
            return None
            
        # Preprocess data
        processed_data = self.data_processor.preprocess_data(
            category_data, 
            remove_outliers=True, 
            fill_missing=True
        )
        
        if processed_data is None or len(processed_data) == 0:
            logger.warning("Failed to preprocess data")
            return None
            
        logger.info(f"Fetched {len(processed_data)} records for training")
        return processed_data
        
    def create_features(self, df, target_col='total_quantity', add_lags=True, 
                      add_rolling=True, add_seasonal=True, add_external=True):
        """
        Create features for model training.
        
        Args:
            df (pandas.DataFrame): Input dataframe
            target_col (str): Target column
            add_lags (bool): Add lag features
            add_rolling (bool): Add rolling window features
            add_seasonal (bool): Add seasonal features
            add_external (bool): Add external data features
            
        Returns:
            pandas.DataFrame: Dataframe with additional features
        """
        logger.info("Creating features for forecasting")
        
        # Make a copy of the input dataframe
        result_df = df.copy()
        
        # Create time series features
        if add_lags or add_rolling:
            # Create time series features by category
            result_df = self.data_processor.create_time_series_features(
                result_df,
                add_lag_features=add_lags,
                add_rolling_features=add_rolling,
                add_seasonal_features=add_seasonal
            )
            
        # Add seasonal features
        if add_seasonal:
            result_df = self.feature_engineer.create_seasonal_features(result_df)
            
        # Add external data if requested
        if add_external:
            result_df = self.feature_engineer.add_external_data(result_df)
            
        logger.info(f"Created features. Final dataframe shape: {result_df.shape}")
        return result_df
        
    def train_models_for_category(self, df, category, forecast_horizon=12, test_size=0.2,
                               train_timeseries=True, train_ensemble=True):
        """
        Train models for a specific category.
        
        Args:
            df (pd.DataFrame): Input dataframe
            category (str): Category to train for
            forecast_horizon (int): Number of periods to forecast
            test_size (float): Proportion of data to use for testing
            train_timeseries (bool): Whether to train time series models
            train_ensemble (bool): Whether to train ensemble models
            
        Returns:
            dict: Dictionary with training results
        """
        logger.info(f"Training models for category: {category}")
        
        results = {
            'category': category,
            'timeseries_models': {},
            'ensemble_models': {},
            'evaluation': {}
        }
        
        # Train time series models if requested
        if train_timeseries:
            logger.info("Training time series models")
            
            # Filter data for this category
            category_data = df[df['القسم'] == category].copy()
            
            # Prepare time series data
            ts_data = self.ts_models.prepare_data(category_data, category=category)
            
            if ts_data is None or len(ts_data) < 12:  # Need at least a year of data
                logger.warning(f"Insufficient data for time series modeling of {category}")
            else:
                # Split data
                train_data, test_data = self.ts_models.train_test_split(ts_data, test_size=test_size)
                
                # Train ARIMA model
                arima_model = self.ts_models.train_arima(train_data, category=category)
                if arima_model:
                    model_id = f"arima_{category}"
                    # Generate forecast
                    arima_forecast = self.ts_models.forecast_arima(
                        model_id, steps=forecast_horizon, test_data=test_data)
                    
                    # Store model info
                    results['timeseries_models']['arima'] = {
                        'model_id': model_id,
                        'metrics': self.ts_models.metrics.get(model_id)
                    }
                    
                    # Register model
                    self.register_model(
                        model_id=model_id,
                        model_type="arima",
                        category=category,
                        metrics=self.ts_models.metrics.get(model_id)
                    )
                
                # Train Exponential Smoothing model
                es_model = self.ts_models.train_exponential_smoothing(train_data, category=category)
                if es_model:
                    model_id = f"exp_smoothing_{category}"
                    # Generate forecast
                    es_forecast = self.ts_models.forecast_exponential_smoothing(
                        model_id, steps=forecast_horizon, test_data=test_data)
                    
                    # Store model info
                    results['timeseries_models']['exp_smoothing'] = {
                        'model_id': model_id,
                        'metrics': self.ts_models.metrics.get(model_id)
                    }
                    
                    # Register model
                    self.register_model(
                        model_id=model_id,
                        model_type="exp_smoothing",
                        category=category,
                        metrics=self.ts_models.metrics.get(model_id)
                    )
                
                # Train Prophet model
                prophet_model = self.ts_models.train_prophet(train_data, category=category)
                if prophet_model:
                    model_id = f"prophet_{category}"
                    # Generate forecast
                    prophet_forecast = self.ts_models.forecast_prophet(
                        model_id, steps=forecast_horizon, test_data=test_data)
                    
                    # Store model info
                    results['timeseries_models']['prophet'] = {
                        'model_id': model_id,
                        'metrics': self.ts_models.metrics.get(model_id)
                    }
                    
                    # Register model
                    self.register_model(
                        model_id=model_id,
                        model_type="prophet",
                        category=category,
                        metrics=self.ts_models.metrics.get(model_id)
                    )
                
                # Compare time series models
                if self.ts_models.metrics:
                    # Find best model
                    best_model = min(self.ts_models.metrics.items(), key=lambda x: x[1]['rmse'])
                    results['evaluation']['best_timeseries_model'] = best_model[0]
                    results['evaluation']['best_timeseries_metrics'] = best_model[1]
                    logger.info(f"Best time series model for {category}: {best_model[0]} "
                               f"with RMSE={best_model[1]['rmse']:.2f}")
        
        # Train ensemble models if requested
        if train_ensemble:
            logger.info("Training ensemble models")
            
            # Filter data for this category
            category_data = df[df['القسم'] == category].copy()
            
            # Check if we have enough data
            if len(category_data) < 12:  # Need at least a year of data
                logger.warning(f"Insufficient data for ensemble modeling of {category}")
            else:
                # Create features
                X, y, feature_names, feature_sets = self.ensemble_forecaster.prepare_features(
                    category_data, target_col='total_quantity', category_col='القسم')
                
                if X is None or y is None:
                    logger.warning(f"Failed to prepare features for ensemble modeling of {category}")
                else:
                    # Train and evaluate models
                    model_types = ['random_forest', 'gradient_boosting', 'linear', 'ridge']
                    
                    ensemble_results = self.ensemble_forecaster.train_and_evaluate(
                        X, y, feature_names, model_types=model_types, 
                        test_size=test_size, date_col=category_data['date'])
                    
                    # Store results
                    for model_type, metrics in ensemble_results.items():
                        model_id = f"ensemble_{model_type}_{category}"
                        
                        results['ensemble_models'][model_type] = {
                            'model_id': model_id,
                            'metrics': metrics
                        }
                        
                        # Register model
                        self.register_model(
                            model_id=model_id,
                            model_type=f"ensemble_{model_type}",
                            category=category,
                            metrics=metrics
                        )
                    
                    # Find best ensemble model
                    if ensemble_results:
                        best_model = min(ensemble_results.items(), key=lambda x: x[1]['rmse'])
                        results['evaluation']['best_ensemble_model'] = f"ensemble_{best_model[0]}_{category}"
                        results['evaluation']['best_ensemble_metrics'] = best_model[1]
                        logger.info(f"Best ensemble model for {category}: {best_model[0]} "
                                 f"with RMSE={best_model[1]['rmse']:.2f}")
        
        # Determine overall best model
        if 'best_timeseries_metrics' in results['evaluation'] and 'best_ensemble_metrics' in results['evaluation']:
            ts_rmse = results['evaluation']['best_timeseries_metrics']['rmse']
            ens_rmse = results['evaluation']['best_ensemble_metrics']['rmse']
            
            if ts_rmse <= ens_rmse:
                results['evaluation']['best_overall_model'] = results['evaluation']['best_timeseries_model']
                results['evaluation']['best_overall_metrics'] = results['evaluation']['best_timeseries_metrics']
                logger.info(f"Best overall model for {category}: {results['evaluation']['best_timeseries_model']}")
            else:
                results['evaluation']['best_overall_model'] = results['evaluation']['best_ensemble_model']
                results['evaluation']['best_overall_metrics'] = results['evaluation']['best_ensemble_metrics']
                logger.info(f"Best overall model for {category}: {results['evaluation']['best_ensemble_model']}")
                
        elif 'best_timeseries_metrics' in results['evaluation']:
            results['evaluation']['best_overall_model'] = results['evaluation']['best_timeseries_model']
            results['evaluation']['best_overall_metrics'] = results['evaluation']['best_timeseries_metrics']
            
        elif 'best_ensemble_metrics' in results['evaluation']:
            results['evaluation']['best_overall_model'] = results['evaluation']['best_ensemble_model']
            results['evaluation']['best_overall_metrics'] = results['evaluation']['best_ensemble_metrics']
            
        return results
    
    def train_models_for_all_categories(self, df=None, categories=None, forecast_horizon=12, 
                                     test_size=0.2, train_timeseries=True, train_ensemble=True):
        """
        Train models for all categories or specified categories.
        
        Args:
            df (pandas.DataFrame): Input dataframe, or None to fetch data
            categories (list): List of categories to train for, or None for all
            forecast_horizon (int): Number of periods to forecast
            test_size (float): Proportion of data to use for testing
            train_timeseries (bool): Whether to train time series models
            train_ensemble (bool): Whether to train ensemble models
            
        Returns:
            dict: Dictionary with training results by category
        """
        # If no dataframe provided, fetch data
        if df is None:
            df = self.fetch_training_data()
            
            if df is None:
                logger.error("Failed to fetch training data")
                return None
                
            # Create features
            df = self.create_features(df)
        
        # If no categories specified, extract all categories from data
        if categories is None:
            categories = df['القسم'].unique().tolist()
            
        logger.info(f"Training models for {len(categories)} categories")
        
        results = {}
        for category in categories:
            logger.info(f"Processing category: {category}")
            
            # Train models for this category
            category_results = self.train_models_for_category(
                df, category, forecast_horizon=forecast_horizon, test_size=test_size,
                train_timeseries=train_timeseries, train_ensemble=train_ensemble
            )
            
            results[category] = category_results
            
        # Identify best model across all categories
        best_model_id = None
        best_rmse = float('inf')
        best_category = None
        
        for category, result in results.items():
            if 'best_overall_metrics' in result['evaluation']:
                rmse = result['evaluation']['best_overall_metrics']['rmse']
                
                if rmse < best_rmse:
                    best_rmse = rmse
                    best_model_id = result['evaluation']['best_overall_model']
                    best_category = category
                    
        if best_model_id:
            logger.info(f"Best model across all categories: {best_model_id} for {best_category} "
                       f"with RMSE={best_rmse:.2f}")
            
        return results
    
    def generate_forecast(self, model_id, steps=12, category=None, specification=None, freq='M'):
        """
        Generate forecast using a trained model.
        
        Args:
            model_id (str): ID of the model to use
            steps (int): Number of steps to forecast
            category (str): Category to forecast for (required for some models)
            specification (str): Product specification to forecast for
            freq (str): Frequency of the forecast ('M', 'W', 'D', etc.)
            
        Returns:
            pandas.Series: Forecast values with datetime index
        """
        logger.info(f"Generating {steps}-step forecast with model {model_id}")
        
        # Check if model exists in the registry
        if model_id not in self.model_registry:
            logger.warning(f"Model {model_id} not found in registry")
            # Try to load model registry
            self.load_model_registry()
            if model_id not in self.model_registry:
                logger.error(f"Model {model_id} not found in registry after reload")
                return None
        
        model_info = self.model_registry[model_id]
        model_type = model_info['model_type']
        
        # Determine if it's a time series or ensemble model
        if model_type.startswith('ensemble_'):
            # Load ensemble model
            ensemble_model_type = model_type.replace('ensemble_', '')
            self.ensemble_forecaster.load_model(model_id, folder_path=self.model_dir)
            
            # Fetch the latest data
            latest_data = self.fetch_training_data(categories=[category] if category else None)
            
            # Create features
            latest_data = self.create_features(latest_data)
            
            # Generate forecast
            forecast = self.ensemble_forecaster.forecast_future(
                latest_data, steps=steps, freq=freq, category=category)
                
        else:
            # Time series model
            self.ts_models.load_model(model_id, folder_path=self.model_dir)
            
            # Generate forecast based on model type
            if model_type == 'arima' or model_type == 'sarima':
                forecast = self.ts_models.generate_future_forecast(
                    model_id, future_periods=steps, freq=freq)
                    
            elif model_type == 'exp_smoothing':
                forecast = self.ts_models.generate_future_forecast(
                    model_id, future_periods=steps, freq=freq)
                    
            elif model_type == 'prophet':
                forecast = self.ts_models.generate_future_forecast(
                    model_id, future_periods=steps, freq=freq)
                    
            else:
                logger.error(f"Unsupported model type: {model_type}")
                return None
                
        if forecast is None:
            logger.error(f"Failed to generate forecast with model {model_id}")
            return None
            
        logger.info(f"Generated {len(forecast)} forecasts with model {model_id}")
        return forecast
    
    def generate_forecast_for_all_categories(self, steps=12, freq='M', use_best_model=True):
        """
        Generate forecasts for all categories.
        
        Args:
            steps (int): Number of steps to forecast
            freq (str): Frequency of the forecast ('M', 'W', 'D', etc.)
            use_best_model (bool): Whether to use the best model for each category
            
        Returns:
            dict: Dictionary with forecasts by category
        """
        # Ensure model registry is loaded
        if not self.model_registry:
            self.load_model_registry()
            
            if not self.model_registry:
                logger.error("Model registry is empty. Run train_models_for_all_categories first.")
                return None
                
        # Get all categories
        categories = list(set([info['category'] for info in self.model_registry.values()]))
        
        logger.info(f"Generating forecasts for {len(categories)} categories")
        
        forecasts = {}
        for category in categories:
            if use_best_model:
                model_id = self.get_best_model(category)
                if not model_id:
                    logger.warning(f"No best model found for category {category}")
                    continue
            else:
                # Get all models for this category
                category_models = self.get_registered_models(category=category)
                if not category_models:
                    logger.warning(f"No models found for category {category}")
                    continue
                    
                # Use the first model
                model_id = next(iter(category_models.keys()))
                
            # Generate forecast
            forecast = self.generate_forecast(model_id, steps=steps, category=category, freq=freq)
            
            if forecast is not None:
                forecasts[category] = forecast
                
        return forecasts
    
    def save_forecasts_to_mongodb(self, forecasts, collection_name="predicted_demand_2025"):
        """
        Save forecasts to MongoDB.
        
        Args:
            forecasts (dict): Dictionary with forecasts by category
            collection_name (str): Name of the collection to save to
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"Saving forecasts to MongoDB collection: {collection_name}")
        
        # Prepare records for MongoDB
        records = []
        for category, forecast in forecasts.items():
            for date, value in forecast.items():
                # Extract year and month from date - handle both Period and datetime objects
                if hasattr(date, 'year') and hasattr(date, 'month'):
                    # This is for datetime objects
                    year = date.year
                    month = date.month
                else:
                    # For Period objects or string dates, convert to string and parse
                    date_str = str(date)
                    date_parts = date_str.split('-')
                    if len(date_parts) >= 2:
                        year = int(date_parts[0])
                        month = int(date_parts[1])
                    else:
                        # Skip invalid dates
                        logger.warning(f"Skipping invalid date format: {date}")
                        continue
                
                record = {
                    "القسم": category,
                    "year": year,
                    "month": month,
                    "predicted_quantity": float(value),
                    "predicted_money_sold": float(value * 100)  # Placeholder, should use actual price data
                }
                
                records.append(record)
                
        # Insert into MongoDB
        try:
            inserted_count = insert_data(collection_name, records)
            logger.info(f"Inserted {inserted_count} forecast records into {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving forecasts to MongoDB: {e}")
            return False

    def save_item_forecasts_to_mongodb(self, forecasts, collection_name="predicted_item_demand_2025"):
        """
        Save item-level forecasts to MongoDB.
        
        Args:
            forecasts (dict): Dictionary with forecasts by category and specification
            collection_name (str): Name of the collection to save to
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"Saving item-level forecasts to MongoDB collection: {collection_name}")
        
        # Prepare records for MongoDB
        records = []
        for category, specs in forecasts.items():
            for spec, forecast in specs.items():
                for date, value in forecast.items():
                    # Extract year and month from date - handle both Period and datetime objects
                    if hasattr(date, 'year') and hasattr(date, 'month'):
                        # This is for datetime objects
                        year = date.year
                        month = date.month
                    else:
                        # For Period objects or string dates, convert to string and parse
                        date_str = str(date)
                        date_parts = date_str.split('-')
                        if len(date_parts) >= 2:
                            year = int(date_parts[0])
                            month = int(date_parts[1])
                        else:
                            # Skip invalid dates
                            logger.warning(f"Skipping invalid date format: {date}")
                            continue
                    
                    record = {
                        "القسم": category,
                        "product_specification": spec,
                        "year": year,
                        "month": month,
                        "predicted_quantity": float(value),
                        "predicted_money_sold": float(value * 100)  # Placeholder, should use actual price data
                    }
                    
                    records.append(record)
                    
        # Insert into MongoDB
        try:
            inserted_count = insert_data(collection_name, records)
            logger.info(f"Inserted {inserted_count} item-level forecast records into {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving item-level forecasts to MongoDB: {e}")
            return False
    
    def generate_item_level_forecasts(self, categories=None, specifications=None, steps=12, freq='M'):
        """
        Generate item-level forecasts (category + product specification).
        
        Args:
            categories (list): List of categories to forecast for, or None for all
            specifications (dict): Dictionary of specifications by category, or None for all
            steps (int): Number of steps to forecast
            freq (str): Frequency of the forecast ('M', 'W', 'D', etc.)
            
        Returns:
            dict: Dictionary with forecasts by category and specification
        """
        logger.info("Generating item-level forecasts")
        
        # Fetch item-level historical data
        item_data = self.data_processor.fetch_item_specification_data(
            categories=categories)
            
        if item_data is None or len(item_data) == 0:
            logger.warning("No item-level data found")
            return None
            
        # Preprocess data
        processed_data = self.data_processor.preprocess_data(
            item_data, 
            remove_outliers=True, 
            fill_missing=True
        )
        
        if processed_data is None:
            logger.warning("Failed to preprocess item-level data")
            return None
            
        # If no categories specified, extract all categories from data
        if categories is None:
            categories = processed_data['القسم'].unique().tolist()
            
        # Dictionary to store forecasts by category and specification
        item_forecasts = {}
        
        # Process each category
        for category in categories:
            logger.info(f"Processing item-level forecasts for category: {category}")
            
            # Get all specifications for this category
            if specifications and category in specifications:
                # Use provided specifications
                category_specs = specifications[category]
            else:
                # Extract all specifications for this category from data
                category_data = processed_data[processed_data['القسم'] == category]
                category_specs = category_data['product_specification'].unique().tolist()
                
            # Skip if no specifications
            if not category_specs:
                logger.warning(f"No specifications found for category {category}")
                continue
                
            # Store forecasts for this category
            item_forecasts[category] = {}
            
            # Get the best model for this category
            model_id = self.get_best_model(category)
            if not model_id:
                logger.warning(f"No model found for category {category}. Using general time series model.")
                # Try to use a time series model
                model_id = f"arima_all"
                
            # Process each specification
            for spec in category_specs:
                logger.info(f"Generating forecast for {category} - {spec}")
                
                # Filter data for this category and specification
                spec_data = processed_data[
                    (processed_data['القسم'] == category) & 
                    (processed_data['product_specification'] == spec)
                ]
                
                # Skip if insufficient data
                if len(spec_data) < 5:  # Need at least a few data points
                    logger.warning(f"Insufficient data for {category} - {spec}")
                    continue
                    
                try:
                    # Prepare time series data
                    ts_data = self.ts_models.prepare_data(
                        spec_data, category=category, product_specification=spec)
                        
                    if ts_data is None or len(ts_data) < 5:
                        logger.warning(f"Failed to prepare time series data for {category} - {spec}")
                        continue
                        
                    # Get the mean ratio of this specification to the category total
                    category_data = processed_data[processed_data['القسم'] == category]
                    category_monthly = category_data.groupby(['year', 'month'])['total_quantity'].sum().reset_index()
                    spec_monthly = spec_data.groupby(['year', 'month'])['total_quantity'].sum().reset_index()
                    
                    # Merge to calculate ratios
                    merged = pd.merge(
                        spec_monthly, 
                        category_monthly, 
                        on=['year', 'month'], 
                        suffixes=('_spec', '_category')
                    )
                    
                    # Calculate ratio
                    merged['ratio'] = merged['total_quantity_spec'] / merged['total_quantity_category']
                    mean_ratio = merged['ratio'].mean()
                    
                    if np.isnan(mean_ratio) or mean_ratio == 0:
                        mean_ratio = 0.1  # Default to 10% if ratio is invalid
                        
                    # Generate category forecast
                    category_forecast = self.generate_forecast(
                        model_id, steps=steps, category=category, freq=freq)
                        
                    if category_forecast is None:
                        logger.warning(f"Failed to generate category forecast for {category}")
                        continue
                        
                    # Apply ratio to get specification forecast
                    spec_forecast = category_forecast * mean_ratio
                    
                    # Ensure non-negative values
                    spec_forecast = spec_forecast.clip(lower=0)
                    
                    # Store forecast
                    item_forecasts[category][spec] = spec_forecast
                    logger.info(f"Generated {len(spec_forecast)} forecasts for {category} - {spec}")
                    
                except Exception as e:
                    logger.error(f"Error generating forecast for {category} - {spec}: {e}")
                    continue
        
        return item_forecasts
    
    def run_ai_forecast(self, train_models=True, generate_forecasts=True, 
                      save_to_mongodb=True, forecast_horizon=12):
        """
        Run the full AI forecasting workflow.
        
        Args:
            train_models (bool): Whether to train new models
            generate_forecasts (bool): Whether to generate forecasts
            save_to_mongodb (bool): Whether to save forecasts to MongoDB
            forecast_horizon (int): Number of periods to forecast
            
        Returns:
            dict: Dictionary with results
        """
        results = {
            'success': True,
            'message': 'AI forecast completed successfully',
            'steps': {}
        }
        
        # Step 1: Fetch and prepare data
        try:
            logger.info("Step 1: Fetching and preparing data")
            
            # Fetch data
            df = self.fetch_training_data()
            
            if df is None:
                results['success'] = False
                results['message'] = 'Failed to fetch training data'
                return results
                
            # Create features
            df_with_features = self.create_features(df)
            
            if df_with_features is None:
                results['success'] = False
                results['message'] = 'Failed to create features'
                return results
                
            results['steps']['data_preparation'] = {
                'success': True,
                'records': len(df_with_features),
                'categories': len(df_with_features['القسم'].unique())
            }
            logger.info("Step 1 completed successfully")
            
        except Exception as e:
            logger.error(f"Error in Step 1: {e}")
            results['success'] = False
            results['message'] = f'Error in data preparation: {e}'
            results['steps']['data_preparation'] = {
                'success': False,
                'error': str(e)
            }
            return results
            
        # Step 2: Train models
        if train_models:
            try:
                logger.info("Step 2: Training models")
                
                # Get all categories
                categories = df_with_features['القسم'].unique().tolist()
                
                # Train models for all categories
                training_results = self.train_models_for_all_categories(
                    df=df_with_features,
                    categories=categories,
                    forecast_horizon=forecast_horizon
                )
                
                if training_results is None:
                    results['success'] = False
                    results['message'] = 'Failed to train models'
                    return results
                    
                results['steps']['model_training'] = {
                    'success': True,
                    'categories_trained': len(training_results),
                    'models_trained': sum([
                        len(result['timeseries_models']) + len(result['ensemble_models'])
                        for result in training_results.values()
                    ])
                }
                logger.info("Step 2 completed successfully")
                
            except Exception as e:
                logger.error(f"Error in Step 2: {e}")
                results['success'] = False
                results['message'] = f'Error in model training: {e}'
                results['steps']['model_training'] = {
                    'success': False,
                    'error': str(e)
                }
                return results
        else:
            results['steps']['model_training'] = {
                'success': True,
                'message': 'Model training skipped'
            }
        
        # Step 3: Generate forecasts
        if generate_forecasts:
            try:
                logger.info("Step 3: Generating forecasts")
                
                # Generate category-level forecasts
                category_forecasts = self.generate_forecast_for_all_categories(
                    steps=forecast_horizon, freq='M', use_best_model=True)
                    
                if category_forecasts is None or len(category_forecasts) == 0:
                    results['success'] = False
                    results['message'] = 'Failed to generate category-level forecasts'
                    return results
                    
                # Generate item-level forecasts
                item_forecasts = self.generate_item_level_forecasts(
                    steps=forecast_horizon, freq='M')
                    
                results['steps']['forecast_generation'] = {
                    'success': True,
                    'category_forecasts': len(category_forecasts),
                    'item_forecasts': len(item_forecasts) if item_forecasts else 0
                }
                logger.info("Step 3 completed successfully")
                
            except Exception as e:
                logger.error(f"Error in Step 3: {e}")
                results['success'] = False
                results['message'] = f'Error in forecast generation: {e}'
                results['steps']['forecast_generation'] = {
                    'success': False,
                    'error': str(e)
                }
                return results
        else:
            results['steps']['forecast_generation'] = {
                'success': True,
                'message': 'Forecast generation skipped'
            }
            
        # Step 4: Save forecasts to MongoDB
        if save_to_mongodb and generate_forecasts:
            try:
                logger.info("Step 4: Saving forecasts to MongoDB")
                
                # Save category-level forecasts
                category_saved = self.save_forecasts_to_mongodb(
                    category_forecasts, collection_name="predicted_demand_2025")
                    
                # Save item-level forecasts if available
                item_saved = False
                if item_forecasts:
                    item_saved = self.save_item_forecasts_to_mongodb(
                        item_forecasts, collection_name="predicted_item_demand_2025")
                        
                results['steps']['save_to_mongodb'] = {
                    'success': category_saved,
                    'category_records_saved': len(category_forecasts) * forecast_horizon,
                    'item_records_saved': sum([len(specs) for specs in item_forecasts.values()]) * forecast_horizon if item_forecasts else 0
                }
                logger.info("Step 4 completed successfully")
                
            except Exception as e:
                logger.error(f"Error in Step 4: {e}")
                results['success'] = False
                results['message'] = f'Error in saving forecasts: {e}'
                results['steps']['save_to_mongodb'] = {
                    'success': False,
                    'error': str(e)
                }
                return results
        else:
            results['steps']['save_to_mongodb'] = {
                'success': True,
                'message': 'Saving to MongoDB skipped'
            }
            
        logger.info("AI forecast completed successfully")
        return results
        
    def get_model_metrics(self, category=None, model_id=None):
        """
        Get metrics for trained models.
        
        Args:
            category (str): Filter by category
            model_id (str): Get metrics for a specific model
            
        Returns:
            dict: Dictionary with model metrics
        """
        # Ensure model registry is loaded
        if not self.model_registry:
            self.load_model_registry()
            
        # If model_id is provided, get metrics for that model
        if model_id:
            if model_id in self.model_registry:
                model_info = self.model_registry[model_id]
                return {
                    model_id: {
                        'model_type': model_info['model_type'],
                        'category': model_info['category'],
                        'metrics': model_info['metrics']
                    }
                }
            else:
                logger.warning(f"Model {model_id} not found in registry")
                return {}
                
        # Filter by category if provided
        if category:
            category_models = self.get_registered_models(category=category)
            
            if not category_models:
                logger.warning(f"No models found for category {category}")
                return {}
                
            return {
                model_id: {
                    'model_type': info['model_type'],
                    'category': info['category'],
                    'metrics': info['metrics']
                }
                for model_id, info in category_models.items()
                if info['metrics']
            }
            
        # Return metrics for all models
        return {
            model_id: {
                'model_type': info['model_type'],
                'category': info['category'],
                'metrics': info['metrics']
            }
            for model_id, info in self.model_registry.items()
            if info['metrics']
        }
        
    def get_seasonal_patterns(self, categories=None):
        """
        Get seasonal patterns from historical data.
        
        Args:
            categories (list): Filter by categories
            
        Returns:
            list: List of seasonal patterns by month
        """
        # Fetch historical data
        df = self.fetch_training_data(categories=categories)
        
        if df is None:
            logger.warning("No data found for seasonal analysis")
            return []
            
        # Group by month to get seasonal patterns
        monthly_data = df.groupby('month')['total_quantity'].mean().reset_index()
        
        # Calculate relative strength (percentage of annual average)
        annual_avg = monthly_data['total_quantity'].mean()
        monthly_data['relative_strength'] = (monthly_data['total_quantity'] / annual_avg) * 100
        
        # Create seasonal patterns
        seasonal_patterns = []
        for _, row in monthly_data.iterrows():
            seasonal_patterns.append({
                'month': int(row['month']),
                'average_quantity': float(row['total_quantity']),
                'relative_strength': float(row['relative_strength'])
            })
            
        return seasonal_patterns
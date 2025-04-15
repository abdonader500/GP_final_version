import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import logging
import pickle
import os
import warnings

from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Suppress StatsModels warning messages
import statsmodels.api as sm
warnings.filterwarnings("ignore", "No frequency information was provided", UserWarning)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('time_series_models')

class TimeSeriesModels:
    """Class for training and evaluating time series forecasting models."""
    
    def __init__(self, target_column='total_quantity', date_column='date', 
                category_column='القسم', log_transform=False):
        """
        Initialize the TimeSeriesModels class.
        
        Args:
            target_column (str): Name of the target column to forecast
            date_column (str): Name of the date column
            category_column (str): Name of the category column
            log_transform (bool): Whether to apply log transformation to the target
        """
        self.target_column = target_column
        self.date_column = date_column
        self.category_column = category_column
        self.log_transform = log_transform
        self.models = {}
        self.forecasts = {}
        self.metrics = {}
        self.fit_info = {}
        
    def prepare_data(self, df, category=None, product_specification=None, resample='M'):
        """
        Prepare data for time series modeling.
        
        Args:
            df (pd.DataFrame): Input dataframe
            category (str): Filter data for this category, or None for all
            product_specification (str): Filter data for this product specification, or None for all
            resample (str): Frequency to resample data to ('D', 'W', 'M', 'Q', 'Y')
            
        Returns:
            pd.Series: Processed time series data with datetime index
        """
        logger.info(f"Preparing time series data for {category or 'all categories'}, "
                   f"{product_specification or 'all products'}")
        
        # Make a copy to avoid modifying the original
        df_copy = df.copy()
        
        # Ensure date column is datetime
        if not pd.api.types.is_datetime64_dtype(df_copy[self.date_column]):
            df_copy[self.date_column] = pd.to_datetime(df_copy[self.date_column])
        
        # Filter by category if specified
        if category is not None:
            df_copy = df_copy[df_copy[self.category_column] == category]
            
        # Filter by product specification if specified
        if product_specification is not None:
            if 'product_specification' not in df_copy.columns:
                logger.warning("product_specification column not found in dataframe")
            else:
                df_copy = df_copy[df_copy['product_specification'] == product_specification]
        
        # Check if we have data after filtering
        if len(df_copy) == 0:
            logger.warning(f"No data found for the specified filters: {category}, {product_specification}")
            return None
        
        # Apply log transformation if specified
        target_data = df_copy[self.target_column]
        if self.log_transform and (target_data > 0).all():
            target_data = np.log1p(target_data)
            logger.info(f"Applied log transformation to {self.target_column}")
        
        # Set date as index
        df_copy.set_index(self.date_column, inplace=True)
        
        # Resample to desired frequency
        if resample:
            # Group and resample
            resampled = df_copy[self.target_column].resample(resample).sum()
            logger.info(f"Resampled data to {resample} frequency, resulting in {len(resampled)} observations")
            return resampled
        
        # If no resampling, return the target column with datetime index
        return df_copy[self.target_column]
        
    def train_test_split(self, ts_data, test_size=0.2):
        """
        Split time series data into training and testing sets.
        
        Args:
            ts_data (pd.Series): Time series data with datetime index
            test_size (float): Proportion of data to use for testing
            
        Returns:
            tuple: (train_data, test_data)
        """
        if ts_data is None or len(ts_data) == 0:
            logger.warning("No data provided for train-test split")
            return None, None
            
        # Calculate split point
        split_point = int(len(ts_data) * (1 - test_size))
        
        # Split data
        train_data = ts_data.iloc[:split_point].copy()
        test_data = ts_data.iloc[split_point:].copy()
        
        logger.info(f"Split data into train ({len(train_data)} observations) and test ({len(test_data)} observations)")
        
        return train_data, test_data
        
    def train_arima(self, train_data, category=None, order=None, seasonal_order=None, enforce_stationarity=False):
        """
        Train an ARIMA model on the time series data.
        
        Args:
            train_data (pd.Series): Training data with datetime index
            category (str): Category name for this model
            order (tuple): ARIMA order (p, d, q)
            seasonal_order (tuple): Seasonal order (P, D, Q, s)
            enforce_stationarity (bool): Whether to enforce stationarity
            
        Returns:
            statsmodels.tsa.arima.model.ARIMAResults: Trained ARIMA model
        """
        model_key = f"arima_{category or 'all'}"
        
        try:
            # Auto-determine order if not provided
            if order is None:
                logger.info(f"Auto-selecting ARIMA parameters for {category or 'all'}")
                from pmdarima import auto_arima
                
                # Use auto_arima to find the best parameters
                automodel = auto_arima(
                    train_data,
                    start_p=0, start_q=0,
                    max_p=5, max_q=5, max_d=2,
                    m=12,  # Monthly seasonality
                    seasonal=True,
                    start_P=0, start_Q=0,
                    max_P=2, max_Q=2, max_D=1,
                    trace=False,
                    error_action='ignore',
                    suppress_warnings=True,
                    stepwise=True
                )
                
                # Extract the best parameters
                order = automodel.order
                seasonal_order = automodel.seasonal_order
                logger.info(f"Auto-selected ARIMA({order}) with seasonal{seasonal_order}")
            
            # Create and fit the model
            if seasonal_order:
                model = SARIMAX(
                    train_data,
                    order=order,
                    seasonal_order=seasonal_order,
                    enforce_stationarity=enforce_stationarity
                )
                logger.info(f"Training SARIMA{order}{seasonal_order} model for {category or 'all'}")
            else:
                model = ARIMA(
                    train_data,
                    order=order,
                    enforce_stationarity=enforce_stationarity
                )
                logger.info(f"Training ARIMA{order} model for {category or 'all'}")
                
            fit_model = model.fit()
            
            # Store model and parameters
            self.models[model_key] = fit_model
            self.fit_info[model_key] = {
                'order': order,
                'seasonal_order': seasonal_order,
                'enforce_stationarity': enforce_stationarity,
                'model_type': 'SARIMA' if seasonal_order else 'ARIMA',
                'target_column': self.target_column,
                'category': category,
                'log_transform': self.log_transform,
                'training_data_length': len(train_data),
                'training_data_start': train_data.index.min(),
                'training_data_end': train_data.index.max()
            }
            
            logger.info(f"Successfully trained {model_key} model")
            return fit_model
            
        except Exception as e:
            logger.error(f"Error training ARIMA model for {category or 'all'}: {e}")
            return None
            
    def train_exponential_smoothing(self, train_data, category=None, seasonal='add', 
                                   seasonal_periods=12, trend='add'):
        """
        Train an Exponential Smoothing model on the time series data.
        
        Args:
            train_data (pd.Series): Training data with datetime index
            category (str): Category name for this model
            seasonal (str): Type of seasonality ('add', 'mul', or None)
            seasonal_periods (int): Number of periods in a seasonal cycle
            trend (str): Type of trend ('add', 'mul', or None)
            
        Returns:
            statsmodels.tsa.holtwinters.ExponentialSmoothingResults: Trained ES model
        """
        model_key = f"exp_smoothing_{category or 'all'}"
        
        try:
            # Create and fit the model
            model = ExponentialSmoothing(
                train_data,
                seasonal=seasonal,
                seasonal_periods=seasonal_periods,
                trend=trend,
                initialization_method='estimated'
            )
            logger.info(f"Training Exponential Smoothing model (trend={trend}, seasonal={seasonal}) "
                      f"for {category or 'all'}")
                      
            fit_model = model.fit()
            
            # Store model and parameters
            self.models[model_key] = fit_model
            self.fit_info[model_key] = {
                'trend': trend,
                'seasonal': seasonal,
                'seasonal_periods': seasonal_periods,
                'model_type': 'ExponentialSmoothing',
                'target_column': self.target_column,
                'category': category,
                'log_transform': self.log_transform,
                'training_data_length': len(train_data),
                'training_data_start': train_data.index.min(),
                'training_data_end': train_data.index.max()
            }
            
            logger.info(f"Successfully trained {model_key} model")
            return fit_model
            
        except Exception as e:
            logger.error(f"Error training Exponential Smoothing model for {category or 'all'}: {e}")
            return None
            
    def train_prophet(self, train_data, category=None, yearly_seasonality=True, 
                     weekly_seasonality=False, daily_seasonality=False,
                     seasonality_mode='additive'):
        """
        Train a Prophet model on the time series data.
        
        Args:
            train_data (pd.Series): Training data with datetime index
            category (str): Category name for this model
            yearly_seasonality (bool/int): Whether to include yearly seasonality
            weekly_seasonality (bool/int): Whether to include weekly seasonality
            daily_seasonality (bool/int): Whether to include daily seasonality
            seasonality_mode (str): 'additive' or 'multiplicative'
            
        Returns:
            prophet.forecaster.Prophet: Trained Prophet model
        """
        model_key = f"prophet_{category or 'all'}"
        
        try:
            # Prepare data for Prophet (needs 'ds' and 'y' columns)
            prophet_df = pd.DataFrame({'ds': train_data.index, 'y': train_data.values})
            
            # Create and fit the model
            model = Prophet(
                yearly_seasonality=yearly_seasonality,
                weekly_seasonality=weekly_seasonality,
                daily_seasonality=daily_seasonality,
                seasonality_mode=seasonality_mode
            )
            
            # Add Egyptian holidays
            model.add_country_holidays(country_name='Egypt')
            
            logger.info(f"Training Prophet model for {category or 'all'}")
            fit_model = model.fit(prophet_df)
            
            # Store model and parameters
            self.models[model_key] = fit_model
            self.fit_info[model_key] = {
                'yearly_seasonality': yearly_seasonality,
                'weekly_seasonality': weekly_seasonality,
                'daily_seasonality': daily_seasonality,
                'seasonality_mode': seasonality_mode,
                'model_type': 'Prophet',
                'target_column': self.target_column,
                'category': category,
                'log_transform': self.log_transform,
                'training_data_length': len(train_data),
                'training_data_start': train_data.index.min(),
                'training_data_end': train_data.index.max()
            }
            
            logger.info(f"Successfully trained {model_key} model")
            return fit_model
            
        except Exception as e:
            logger.error(f"Error training Prophet model for {category or 'all'}: {e}")
            return None
    
    def forecast_arima(self, model_key, steps=12, test_data=None):
        """
        Generate forecasts using a trained ARIMA/SARIMA model.
        
        Args:
            model_key (str): Key for the trained model
            steps (int): Number of steps to forecast
            test_data (pd.Series): Test data for comparison, if available
            
        Returns:
            pd.Series: Forecast values with datetime index
        """
        if model_key not in self.models:
            logger.error(f"Model {model_key} not found")
            return None
            
        model = self.models[model_key]
        model_info = self.fit_info[model_key]
        
        try:
            # Generate forecast
            logger.info(f"Generating {steps}-step forecast with {model_key}")
            
            # For ARIMA/SARIMA models
            if model_info['model_type'] in ['ARIMA', 'SARIMA']:
                forecast = model.forecast(steps)
                
                # Create forecast index (continuing from the end of training data)
                last_date = model_info['training_data_end']
                
                # Determine frequency from the data
                if isinstance(last_date, pd.Timestamp):
                    # For monthly data
                    if last_date.day <= 28:  # Probably the start of a month
                        forecast_index = pd.date_range(start=last_date + pd.DateOffset(months=1), 
                                                    periods=steps, freq='MS')
                    else:
                        forecast_index = pd.date_range(start=last_date, periods=steps+1, freq='M')[1:]
                else:
                    # Fallback - assume monthly
                    forecast_index = pd.date_range(start=last_date, periods=steps+1, freq='M')[1:]
                
                # Create forecast series
                forecast_series = pd.Series(forecast, index=forecast_index)
                
                # Reverse log transformation if applied
                if model_info['log_transform']:
                    forecast_series = np.expm1(forecast_series)
                    logger.info("Applied reverse log transformation to forecast")
                
                # Store forecast
                self.forecasts[model_key] = forecast_series
                
                # Calculate metrics if test data is provided
                if test_data is not None:
                    # Align forecast with test periods
                    aligned_forecast = forecast_series.reindex(test_data.index, method='nearest')
                    
                    # Calculate metrics
                    metrics = calculate_forecast_metrics(test_data, aligned_forecast)
                    self.metrics[model_key] = metrics
                    logger.info(f"Metrics for {model_key}: RMSE={metrics['rmse']:.2f}, MAE={metrics['mae']:.2f}")
                
                return forecast_series
            else:
                logger.error(f"Model {model_key} is not an ARIMA/SARIMA model")
                return None
                
        except Exception as e:
            logger.error(f"Error generating forecast with {model_key}: {e}")
            return None
    
    def forecast_exponential_smoothing(self, model_key, steps=12, test_data=None):
        """
        Generate forecasts using a trained Exponential Smoothing model.
        
        Args:
            model_key (str): Key for the trained model
            steps (int): Number of steps to forecast
            test_data (pd.Series): Test data for comparison, if available
            
        Returns:
            pd.Series: Forecast values with datetime index
        """
        if model_key not in self.models:
            logger.error(f"Model {model_key} not found")
            return None
            
        model = self.models[model_key]
        model_info = self.fit_info[model_key]
        
        try:
            # Generate forecast
            logger.info(f"Generating {steps}-step forecast with {model_key}")
            
            # For Exponential Smoothing models
            if model_info['model_type'] == 'ExponentialSmoothing':
                forecast = model.forecast(steps)
                
                # Create forecast index (continuing from the end of training data)
                last_date = model_info['training_data_end']
                
                # Determine frequency from the data
                if isinstance(last_date, pd.Timestamp):
                    # For monthly data
                    if last_date.day <= 28:  # Probably the start of a month
                        forecast_index = pd.date_range(start=last_date + pd.DateOffset(months=1), 
                                                    periods=steps, freq='MS')
                    else:
                        forecast_index = pd.date_range(start=last_date, periods=steps+1, freq='M')[1:]
                else:
                    # Fallback - assume monthly
                    forecast_index = pd.date_range(start=last_date, periods=steps+1, freq='M')[1:]
                
                # Create forecast series
                forecast_series = pd.Series(forecast, index=forecast_index)
                
                # Reverse log transformation if applied
                if model_info['log_transform']:
                    forecast_series = np.expm1(forecast_series)
                    logger.info("Applied reverse log transformation to forecast")
                
                # Store forecast
                self.forecasts[model_key] = forecast_series
                
                # Calculate metrics if test data is provided
                if test_data is not None:
                    # Align forecast with test periods
                    aligned_forecast = forecast_series.reindex(test_data.index, method='nearest')
                    
                    # Calculate metrics
                    metrics = calculate_forecast_metrics(test_data, aligned_forecast)
                    self.metrics[model_key] = metrics
                    logger.info(f"Metrics for {model_key}: RMSE={metrics['rmse']:.2f}, MAE={metrics['mae']:.2f}")
                
                return forecast_series
            else:
                logger.error(f"Model {model_key} is not an Exponential Smoothing model")
                return None
                
        except Exception as e:
            logger.error(f"Error generating forecast with {model_key}: {e}")
            return None
    
    def forecast_prophet(self, model_key, steps=12, test_data=None, freq='M'):
        """
        Generate forecasts using a trained Prophet model.
        
        Args:
            model_key (str): Key for the trained model
            steps (int): Number of steps to forecast
            test_data (pd.Series): Test data for comparison, if available
            freq (str): Frequency of the forecast ('D', 'W', 'M', 'Q', 'Y')
            
        Returns:
            pd.Series: Forecast values with datetime index
        """
        if model_key not in self.models:
            logger.error(f"Model {model_key} not found")
            return None
            
        model = self.models[model_key]
        model_info = self.fit_info[model_key]
        
        try:
            # Generate forecast
            logger.info(f"Generating {steps}-step forecast with {model_key}")
            
            # For Prophet models
            if model_info['model_type'] == 'Prophet':
                # Create future dataframe for Prophet
                last_date = model_info['training_data_end']
                
                # Convert frequency to Prophet format
                freq_map = {'D': 'days', 'W': 'weeks', 'M': 'months', 'Q': 'quarters', 'Y': 'years'}
                prophet_freq = freq_map.get(freq, 'months')
                
                # Generate future dates
                future = model.make_future_dataframe(periods=steps, freq=freq)
                
                # Generate forecast
                forecast = model.predict(future)
                
                # Extract the forecast portion only
                test_size = len(future) - len(model_info['training_data_length'])
                forecast = forecast.iloc[-steps:].copy()
                
                # Create forecast series (Prophet uses 'ds' for dates and 'yhat' for predictions)
                forecast_series = pd.Series(forecast['yhat'].values, index=forecast['ds'])
                
                # Reverse log transformation if applied
                if model_info['log_transform']:
                    forecast_series = np.expm1(forecast_series)
                    logger.info("Applied reverse log transformation to forecast")
                
                # Store forecast
                self.forecasts[model_key] = forecast_series
                
                # Calculate metrics if test data is provided
                if test_data is not None:
                    # Align forecast with test periods
                    aligned_forecast = forecast_series.reindex(test_data.index, method='nearest')
                    
                    # Calculate metrics
                    metrics = calculate_forecast_metrics(test_data, aligned_forecast)
                    self.metrics[model_key] = metrics
                    logger.info(f"Metrics for {model_key}: RMSE={metrics['rmse']:.2f}, MAE={metrics['mae']:.2f}")
                
                return forecast_series
            else:
                logger.error(f"Model {model_key} is not a Prophet model")
                return None
                
        except Exception as e:
            logger.error(f"Error generating forecast with {model_key}: {e}")
            return None
            
    def train_models_for_category(self, df, category=None, product_specification=None, 
                                 test_size=0.2, forecast_horizon=12, models_to_train=None):
        """
        Train multiple models for a specific category and compare their performance.
        
        Args:
            df (pd.DataFrame): Input dataframe
            category (str): Category to train models for
            product_specification (str): Product specification to train models for
            test_size (float): Proportion of data to use for testing
            forecast_horizon (int): Number of periods to forecast
            models_to_train (list): List of model types to train ('arima', 'exp_smoothing', 'prophet')
            
        Returns:
            dict: Dictionary with model keys and their metrics
        """
        if models_to_train is None:
            models_to_train = ['arima', 'exp_smoothing', 'prophet']
            
        logger.info(f"Training models for {category or 'all'}, {product_specification or 'all products'}")
        
        # Prepare data
        ts_data = self.prepare_data(df, category, product_specification)
        if ts_data is None or len(ts_data) < 12:  # Need at least a year of data
            logger.warning(f"Insufficient data for {category}, {product_specification}")
            return {}
            
        # Split data
        train_data, test_data = self.train_test_split(ts_data, test_size)
        if train_data is None or len(train_data) < 12:
            logger.warning(f"Insufficient training data for {category}, {product_specification}")
            return {}
            
        trained_models = {}
        
        # Train ARIMA/SARIMA model
        if 'arima' in models_to_train:
            arima_model = self.train_arima(train_data, category)
            if arima_model:
                model_key = f"arima_{category or 'all'}"
                trained_models[model_key] = arima_model
                # Generate forecast
                self.forecast_arima(model_key, steps=forecast_horizon, test_data=test_data)
        
        # Train Exponential Smoothing model
        if 'exp_smoothing' in models_to_train:
            es_model = self.train_exponential_smoothing(train_data, category)
            if es_model:
                model_key = f"exp_smoothing_{category or 'all'}"
                trained_models[model_key] = es_model
                # Generate forecast
                self.forecast_exponential_smoothing(model_key, steps=forecast_horizon, test_data=test_data)
        
        # Train Prophet model
        if 'prophet' in models_to_train:
            prophet_model = self.train_prophet(train_data, category)
            if prophet_model:
                model_key = f"prophet_{category or 'all'}"
                trained_models[model_key] = prophet_model
                # Generate forecast
                self.forecast_prophet(model_key, steps=forecast_horizon, test_data=test_data)
        
        # Identify best model
        if self.metrics:
            best_model = min(self.metrics.items(), key=lambda x: x[1]['rmse'])
            logger.info(f"Best model for {category or 'all'}: {best_model[0]} with RMSE={best_model[1]['rmse']:.2f}")
        
        return trained_models
        
    def train_all_categories(self, df, categories=None, test_size=0.2, forecast_horizon=12):
        """
        Train models for all categories in the data.
        
        Args:
            df (pd.DataFrame): Input dataframe
            categories (list): List of categories to train models for, or None for all
            test_size (float): Proportion of data to use for testing
            forecast_horizon (int): Number of periods to forecast
            
        Returns:
            dict: Dictionary with category keys and their best model metrics
        """
        # If no categories specified, extract all categories from data
        if categories is None:
            categories = df[self.category_column].unique().tolist()
            
        logger.info(f"Training models for {len(categories)} categories")
        
        results = {}
        for category in categories:
            logger.info(f"Processing category: {category}")
            trained_models = self.train_models_for_category(
                df, category, test_size=test_size, forecast_horizon=forecast_horizon
            )
            
            # Extract metrics for this category
            category_metrics = {k: v for k, v in self.metrics.items() if k.endswith(f"_{category}")}
            
            if category_metrics:
                best_model = min(category_metrics.items(), key=lambda x: x[1]['rmse'])
                results[category] = {
                    'best_model': best_model[0],
                    'metrics': best_model[1]
                }
                logger.info(f"Best model for {category}: {best_model[0]} with RMSE={best_model[1]['rmse']:.2f}")
            
        return results
    
    def combine_forecasts(self, model_keys, weights=None, steps=12):
        """
        Combine forecasts from multiple models using weighted average.
        
        Args:
            model_keys (list): List of model keys to combine
            weights (list): List of weights for each model, or None for equal weights
            steps (int): Number of steps to forecast
            
        Returns:
            pd.Series: Combined forecast values with datetime index
        """
        # Filter to only include models that exist
        existing_keys = [key for key in model_keys if key in self.forecasts]
        
        if not existing_keys:
            logger.error("No valid models found for combining forecasts")
            return None
            
        logger.info(f"Combining forecasts from {len(existing_keys)} models")
        
        # Use equal weights if not specified
        if weights is None:
            weights = [1.0 / len(existing_keys)] * len(existing_keys)
        else:
            # Normalize weights
            total_weight = sum(weights)
            weights = [w / total_weight for w in weights]
            
        # Get the union of all forecast dates
        all_dates = pd.DatetimeIndex([])
        for key in existing_keys:
            all_dates = all_dates.union(self.forecasts[key].index)
        all_dates = all_dates.sort_values()
        
        # Limit to the requested number of steps
        all_dates = all_dates[:steps]
        
        # Initialize combined forecast
        combined_forecast = pd.Series(0.0, index=all_dates)
        
        # Add weighted forecasts
        for key, weight in zip(existing_keys, weights):
            # Reindex to align with the combined forecast dates
            aligned_forecast = self.forecasts[key].reindex(all_dates, method='nearest')
            combined_forecast += aligned_forecast * weight
            
        logger.info(f"Generated combined forecast for {len(combined_forecast)} periods")
        
        return combined_forecast
    
    def generate_future_forecast(self, model_key, future_periods=12, freq='M'):
        """
        Generate a forecast for future periods.
        
        Args:
            model_key (str): Key for the trained model
            future_periods (int): Number of future periods to forecast
            freq (str): Frequency of the forecast ('D', 'W', 'M', 'Q', 'Y')
            
        Returns:
            pd.Series: Forecast values with datetime index
        """
        if model_key not in self.models:
            logger.error(f"Model {model_key} not found")
            return None
            
        model = self.models[model_key]
        model_info = self.fit_info[model_key]
        
        try:
            # Get the end of the training data
            last_date = model_info['training_data_end']
            
            # Create forecast index for future periods
            if freq == 'M':
                forecast_index = pd.date_range(start=last_date, periods=future_periods+1, freq='M')[1:]
            elif freq == 'D':
                forecast_index = pd.date_range(start=last_date, periods=future_periods+1, freq='D')[1:]
            elif freq == 'W':
                forecast_index = pd.date_range(start=last_date, periods=future_periods+1, freq='W')[1:]
            elif freq == 'Q':
                forecast_index = pd.date_range(start=last_date, periods=future_periods+1, freq='Q')[1:]
            elif freq == 'Y':
                forecast_index = pd.date_range(start=last_date, periods=future_periods+1, freq='Y')[1:]
            else:
                logger.error(f"Unsupported frequency: {freq}")
                return None
                
            # Generate forecast based on model type
            model_type = model_info['model_type']
            
            if model_type in ['ARIMA', 'SARIMA']:
                forecast = model.forecast(future_periods)
            elif model_type == 'ExponentialSmoothing':
                forecast = model.forecast(future_periods)
            elif model_type == 'Prophet':
                # Create future dataframe for Prophet
                freq_map = {'D': 'days', 'W': 'weeks', 'M': 'months', 'Q': 'quarters', 'Y': 'years'}
                prophet_freq = freq_map.get(freq, 'months')
                
                future = model.make_future_dataframe(periods=future_periods, freq=freq)
                forecast_df = model.predict(future)
                
                # Extract the forecast portion only
                forecast_df = forecast_df.iloc[-future_periods:].copy()
                forecast = forecast_df['yhat'].values
            else:
                logger.error(f"Unsupported model type: {model_type}")
                return None
                
            # Create forecast series
            forecast_series = pd.Series(forecast, index=forecast_index)
            
            # Reverse log transformation if applied
            if model_info['log_transform']:
                forecast_series = np.expm1(forecast_series)
                logger.info("Applied reverse log transformation to forecast")
                
            # Ensure non-negative values for quantity/sales forecasts
            forecast_series = forecast_series.clip(lower=0)
            
            logger.info(f"Generated future forecast with {model_key} for {future_periods} periods")
            
            return forecast_series
            
        except Exception as e:
            logger.error(f"Error generating future forecast with {model_key}: {e}")
            return None
    
    def plot_forecast(self, model_key, train_data=None, test_data=None, figsize=(12, 6)):
        """
        Plot the forecast from a trained model against training and test data.
        
        Args:
            model_key (str): Key for the trained model
            train_data (pd.Series): Training data to plot
            test_data (pd.Series): Test data to plot
            figsize (tuple): Figure size
            
        Returns:
            matplotlib.figure.Figure: Figure object
        """
        if model_key not in self.forecasts:
            logger.error(f"Forecast for {model_key} not found")
            return None
            
        forecast = self.forecasts[model_key]
        model_info = self.fit_info[model_key]
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Plot training data if provided
        if train_data is not None:
            ax.plot(train_data.index, train_data.values, 'b-', label='Training Data')
            
        # Plot test data if provided
        if test_data is not None:
            ax.plot(test_data.index, test_data.values, 'g-', label='Test Data')
            
        # Plot forecast
        ax.plot(forecast.index, forecast.values, 'r--', label='Forecast')
        
        # Add confidence intervals if available
        if model_info['model_type'] == 'Prophet' and 'uncertainty' in model_info:
            lower = forecast - model_info['uncertainty']
            upper = forecast + model_info['uncertainty']
            ax.fill_between(forecast.index, lower, upper, color='r', alpha=0.2, label='95% Confidence Interval')
            
        # Customize plot
        ax.set_title(f"Forecast for {model_info['category'] or 'All Categories'} using {model_info['model_type']}")
        ax.set_xlabel('Date')
        ax.set_ylabel(model_info['target_column'])
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.legend()
        
        # Add metrics if available
        if model_key in self.metrics:
            metrics = self.metrics[model_key]
            metrics_text = f"RMSE: {metrics['rmse']:.2f}\nMAE: {metrics['mae']:.2f}\nMAPE: {metrics['mape']:.2f}%"
            ax.text(0.02, 0.95, metrics_text, transform=ax.transAxes, fontsize=10,
                   bbox=dict(facecolor='white', alpha=0.8))
                   
        fig.tight_layout()
        
        return fig
        
    def save_model(self, model_key, folder_path='models'):
        """
        Save a trained model to disk.
        
        Args:
            model_key (str): Key for the trained model
            folder_path (str): Path to save the model
            
        Returns:
            bool: True if successful, False otherwise
        """
        if model_key not in self.models:
            logger.error(f"Model {model_key} not found")
            return False
            
        # Create folder if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)
        
        try:
            model = self.models[model_key]
            model_info = self.fit_info[model_key]
            
            # Save model
            model_path = os.path.join(folder_path, f"{model_key}.pkl")
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
                
            # Save model info
            info_path = os.path.join(folder_path, f"{model_key}_info.pkl")
            with open(info_path, 'wb') as f:
                pickle.dump(model_info, f)
                
            logger.info(f"Model {model_key} saved to {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving model {model_key}: {e}")
            return False
            
    def load_model(self, model_key, folder_path='models'):
        """
        Load a trained model from disk.
        
        Args:
            model_key (str): Key for the trained model
            folder_path (str): Path to load the model from
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Load model
            model_path = os.path.join(folder_path, f"{model_key}.pkl")
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
                
            # Load model info
            info_path = os.path.join(folder_path, f"{model_key}_info.pkl")
            with open(info_path, 'rb') as f:
                model_info = pickle.load(f)
                
            # Store in class attributes
            self.models[model_key] = model
            self.fit_info[model_key] = model_info
            
            logger.info(f"Model {model_key} loaded from {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model {model_key}: {e}")
            return False


def calculate_forecast_metrics(actual, forecast):
    """
    Calculate forecast accuracy metrics.
    
    Args:
        actual (pd.Series): Actual values
        forecast (pd.Series): Forecast values
        
    Returns:
        dict: Dictionary with metrics
    """
    # Align series
    aligned_data = pd.DataFrame({
        'actual': actual,
        'forecast': forecast
    })
    
    # Drop rows with missing values
    aligned_data.dropna(inplace=True)
    
    if len(aligned_data) == 0:
        return {
            'rmse': float('nan'),
            'mae': float('nan'),
            'mape': float('nan'),
            'r2': float('nan')
        }
    
    # Extract aligned values
    actual_values = aligned_data['actual'].values
    forecast_values = aligned_data['forecast'].values
    
    # Calculate metrics
    mse = mean_squared_error(actual_values, forecast_values)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(actual_values, forecast_values)
    
    # Calculate MAPE, avoiding division by zero
    with np.errstate(divide='ignore', invalid='ignore'):
        mape = np.mean(np.abs((actual_values - forecast_values) / actual_values)) * 100
        
    # If MAPE is infinite or NaN, use an alternative
    if np.isinf(mape) or np.isnan(mape):
        # Use normalized MAE as an alternative
        data_range = actual_values.max() - actual_values.min()
        if data_range > 0:
            mape = (mae / data_range) * 100
        else:
            mape = float('nan')
    
    # Calculate R-squared
    r2 = r2_score(actual_values, forecast_values)
    
    return {
        'rmse': rmse,
        'mae': mae,
        'mape': mape,
        'r2': r2
    }


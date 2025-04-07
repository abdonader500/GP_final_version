import pandas as pd
import numpy as np
import logging
import pickle
import os
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ensemble_models')

class EnsembleForecaster:
    """Class for building ensemble forecasting models that combine time series and ML approaches."""
    
    def __init__(self, time_series_features=True, categorical_features=True, 
                external_features=True):
        """
        Initialize the ensemble forecaster.
        
        Args:
            time_series_features (bool): Whether to include time series features
            categorical_features (bool): Whether to include categorical features
            external_features (bool): Whether to include external features
        """
        self.time_series_features = time_series_features
        self.categorical_features = categorical_features
        self.external_features = external_features
        self.models = {}
        self.feature_importances = {}
        self.metrics = {}
        self.scaler = StandardScaler()
        self.best_model = None
        
    def prepare_features(self, df, target_col='total_quantity', 
                        category_col='القسم', date_col='date'):
        """
        Prepare features for ML models.
        
        Args:
            df (pd.DataFrame): Input dataframe
            target_col (str): Target column
            category_col (str): Category column
            date_col (str): Date column
            
        Returns:
            tuple: (X, y, feature_names)
        """
        logger.info("Preparing features for ensemble model")
        
        # Make a copy to avoid modifying the original
        df_copy = df.copy()
        
        # Ensure date column is datetime
        if not pd.api.types.is_datetime64_dtype(df_copy[date_col]):
            df_copy[date_col] = pd.to_datetime(df_copy[date_col])
            
        # Extract features
        feature_cols = []
        feature_sets = {}
        
        # Extract date features
        df_copy['year'] = df_copy[date_col].dt.year
        df_copy['month'] = df_copy[date_col].dt.month
        df_copy['quarter'] = df_copy[date_col].dt.quarter
        df_copy['is_ramadan'] = df_copy['is_ramadan'] if 'is_ramadan' in df_copy.columns else 0
        df_copy['is_summer'] = df_copy['month'].isin([6, 7, 8])
        df_copy['is_winter'] = df_copy['month'].isin([12, 1, 2])
        
        date_features = ['year', 'month', 'quarter', 'is_ramadan', 'is_summer', 'is_winter']
        feature_cols.extend(date_features)
        feature_sets['date'] = date_features
        
        # Cyclical encoding for month
        df_copy['month_sin'] = np.sin(2 * np.pi * df_copy['month'] / 12)
        df_copy['month_cos'] = np.cos(2 * np.pi * df_copy['month'] / 12)
        cyclical_features = ['month_sin', 'month_cos']
        feature_cols.extend(cyclical_features)
        feature_sets['cyclical'] = cyclical_features
        
        # Include time series features if requested
        if self.time_series_features:
            # Identify lag and rolling columns if they exist
            ts_features = [col for col in df_copy.columns if 
                          ('lag' in col or 'roll' in col) and 
                          not col.startswith(target_col)]
                          
            if ts_features:
                feature_cols.extend(ts_features)
                feature_sets['time_series'] = ts_features
                logger.info(f"Added {len(ts_features)} time series features")
            else:
                logger.warning("No time series features found. You may need to create them first.")
        
        # Include categorical features if requested
        if self.categorical_features:
            # One-hot encode categories
            if category_col in df_copy.columns:
                cat_dummies = pd.get_dummies(df_copy[category_col], prefix=category_col)
                df_copy = pd.concat([df_copy, cat_dummies], axis=1)
                
                cat_features = cat_dummies.columns.tolist()
                feature_cols.extend(cat_features)
                feature_sets['categorical'] = cat_features
                logger.info(f"Added {len(cat_features)} categorical features")
            
            # Process product specification if available
            if 'product_specification' in df_copy.columns:
                spec_dummies = pd.get_dummies(df_copy['product_specification'], prefix='spec')
                df_copy = pd.concat([df_copy, spec_dummies], axis=1)
                
                spec_features = spec_dummies.columns.tolist()
                feature_cols.extend(spec_features)
                feature_sets['specification'] = spec_features
                logger.info(f"Added {len(spec_features)} product specification features")
        
        # Include external features if requested
        if self.external_features:
            external_cols = [col for col in df_copy.columns if col in 
                            ['inflation_rate', 'consumer_confidence', 'import_trend']]
                            
            if external_cols:
                feature_cols.extend(external_cols)
                feature_sets['external'] = external_cols
                logger.info(f"Added {len(external_cols)} external features")
            else:
                logger.warning("No external features found. You may need to add them first.")
        
        # Ensure all feature columns exist
        feature_cols = [col for col in feature_cols if col in df_copy.columns]
        
        if not feature_cols:
            logger.error("No features found after processing")
            return None, None, None
            
        # Prepare feature matrix and target
        X = df_copy[feature_cols].copy()
        
        # Handle missing values
        X.fillna(method='bfill', inplace=True)
        X.fillna(method='ffill', inplace=True)
        X.fillna(0, inplace=True)
        
        # Extract target
        if target_col in df_copy.columns:
            y = df_copy[target_col].copy()
        else:
            logger.error(f"Target column {target_col} not found in dataframe")
            return None, None, None
            
        logger.info(f"Prepared {X.shape[1]} features and {len(y)} target values")
        
        return X, y, feature_cols, feature_sets
        
    def train_test_split(self, X, y, test_size=0.2, random_state=42, time_based=True, date_col=None):
        """
        Split data into training and testing sets.
        
        Args:
            X (pd.DataFrame): Feature matrix
            y (pd.Series): Target vector
            test_size (float): Proportion of data to use for testing
            random_state (int): Random seed for reproducibility
            time_based (bool): Whether to split based on time (last n% of data)
            date_col (pd.Series): Date column for time-based splitting
            
        Returns:
            tuple: (X_train, X_test, y_train, y_test)
        """
        if time_based and date_col is not None:
            # Sort data by date
            sorted_indices = date_col.argsort()
            X_sorted = X.iloc[sorted_indices]
            y_sorted = y.iloc[sorted_indices]
            
            # Split at the time point
            split_idx = int(len(X) * (1 - test_size))
            X_train = X_sorted.iloc[:split_idx]
            X_test = X_sorted.iloc[split_idx:]
            y_train = y_sorted.iloc[:split_idx]
            y_test = y_sorted.iloc[split_idx:]
            
            logger.info(f"Time-based split: train={len(X_train)}, test={len(X_test)}")
            
        else:
            # Random split
            from sklearn.model_selection import train_test_split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state)
                
            logger.info(f"Random split: train={len(X_train)}, test={len(X_test)}")
            
        return X_train, X_test, y_train, y_test
    
    def scale_features(self, X_train, X_test):
        """
        Scale features to zero mean and unit variance.
        
        Args:
            X_train (pd.DataFrame): Training features
            X_test (pd.DataFrame): Testing features
            
        Returns:
            tuple: (X_train_scaled, X_test_scaled)
        """
        # Fit scaler on training data
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        # Transform test data
        X_test_scaled = self.scaler.transform(X_test)
        
        logger.info(f"Scaled features with mean={self.scaler.mean_[:5]} and std={self.scaler.scale_[:5]}")
        
        return X_train_scaled, X_test_scaled
    
    def train_model(self, X_train, y_train, model_type='random_forest', **model_params):
        """
        Train a machine learning model.
        
        Args:
            X_train (np.ndarray): Training features
            y_train (np.ndarray): Training targets
            model_type (str): Type of model to train
            **model_params: Additional parameters for the model
            
        Returns:
            object: Trained model
        """
        logger.info(f"Training {model_type} model")
        
        # Create model based on type
        if model_type == 'random_forest':
            default_params = {
                'n_estimators': 100,
                'max_depth': None,
                'min_samples_split': 2,
                'min_samples_leaf': 1,
                'max_features': 'sqrt',
                'random_state': 42,
                'n_jobs': -1
            }
            # Update with user-provided parameters
            params = {**default_params, **model_params}
            model = RandomForestRegressor(**params)
            
        elif model_type == 'gradient_boosting':
            default_params = {
                'n_estimators': 100,
                'learning_rate': 0.1,
                'max_depth': 3,
                'min_samples_split': 2,
                'min_samples_leaf': 1,
                'max_features': 'sqrt',
                'random_state': 42
            }
            params = {**default_params, **model_params}
            model = GradientBoostingRegressor(**params)
            
        elif model_type == 'svr':
            default_params = {
                'kernel': 'rbf',
                'C': 1.0,
                'epsilon': 0.1,
                'gamma': 'scale'
            }
            params = {**default_params, **model_params}
            model = SVR(**params)
            
        elif model_type == 'linear':
            model = LinearRegression()
            
        elif model_type == 'ridge':
            default_params = {
                'alpha': 1.0,
                'random_state': 42
            }
            params = {**default_params, **model_params}
            model = Ridge(**params)
            
        elif model_type == 'lasso':
            default_params = {
                'alpha': 1.0,
                'random_state': 42
            }
            params = {**default_params, **model_params}
            model = Lasso(**params)
            
        else:
            logger.error(f"Unsupported model type: {model_type}")
            return None
            
        # Fit model
        model.fit(X_train, y_train)
        
        # Save model
        self.models[model_type] = model
        
        # Extract feature importances if available
        if hasattr(model, 'feature_importances_'):
            self.feature_importances[model_type] = model.feature_importances_
            logger.info(f"Extracted feature importances for {model_type}")
            
        return model
        
    def evaluate_model(self, model, X_test, y_test, model_type=None):
        """
        Evaluate a trained model.
        
        Args:
            model: Trained model
            X_test (np.ndarray): Test features
            y_test (np.ndarray): Test targets
            model_type (str): Type of model (for storing metrics)
            
        Returns:
            dict: Evaluation metrics
        """
        # Make predictions
        y_pred = model.predict(X_test)
        
        # Calculate metrics
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        # Calculate MAPE (Mean Absolute Percentage Error)
        with np.errstate(divide='ignore', invalid='ignore'):
            mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100
            
        # If MAPE is infinite or NaN, use an alternative
        if np.isinf(mape) or np.isnan(mape):
            # Use normalized MAE as an alternative
            data_range = y_test.max() - y_test.min()
            if data_range > 0:
                mape = (mae / data_range) * 100
            else:
                mape = np.nan
                
        metrics = {
            'rmse': rmse,
            'mae': mae,
            'mape': mape,
            'r2': r2
        }
        
        # Store metrics
        if model_type:
            self.metrics[model_type] = metrics
            
        logger.info(f"Model evaluation: RMSE={rmse:.2f}, MAE={mae:.2f}, MAPE={mape:.2f}%, R²={r2:.4f}")
        
        return metrics
        
    def train_and_evaluate(self, X, y, feature_names, model_types=None, 
                         test_size=0.2, date_col=None, scale_features=True):
        """
        Train and evaluate multiple models.
        
        Args:
            X (pd.DataFrame): Feature matrix
            y (pd.Series): Target vector
            feature_names (list): Names of features
            model_types (list): List of model types to train
            test_size (float): Proportion of data to use for testing
            date_col (pd.Series): Date column for time-based splitting
            scale_features (bool): Whether to scale features
            
        Returns:
            dict: Evaluation metrics for all models
        """
        if model_types is None:
            model_types = ['random_forest', 'gradient_boosting', 'linear', 'ridge']
            
        logger.info(f"Training and evaluating {len(model_types)} models")
        
        # Split data
        X_train, X_test, y_train, y_test = self.train_test_split(
            X, y, test_size=test_size, time_based=True, date_col=date_col)
            
        # Scale features if requested
        if scale_features:
            X_train_scaled, X_test_scaled = self.scale_features(X_train, X_test)
        else:
            X_train_scaled, X_test_scaled = X_train.values, X_test.values
            
        # Train and evaluate models
        results = {}
        for model_type in model_types:
            logger.info(f"Processing {model_type} model")
            
            # Train model
            model = self.train_model(X_train_scaled, y_train, model_type)
            
            if model is None:
                logger.warning(f"Failed to train {model_type} model. Skipping evaluation.")
                continue
                
            # Evaluate model
            metrics = self.evaluate_model(model, X_test_scaled, y_test, model_type)
            
            # Store results
            results[model_type] = metrics
            
            # Update feature importances if available
            if model_type in self.feature_importances and feature_names:
                importances = self.feature_importances[model_type]
                importance_df = pd.DataFrame({
                    'feature': feature_names[:len(importances)],
                    'importance': importances
                })
                importance_df = importance_df.sort_values('importance', ascending=False)
                self.feature_importances[model_type] = importance_df
                
                # Print top features
                top_features = importance_df.head(10)
                logger.info(f"Top features for {model_type}: {', '.join(top_features['feature'])}")
        
        # Identify best model
        if results:
            best_model_type = min(results.items(), key=lambda x: x[1]['rmse'])[0]
            self.best_model = best_model_type
            logger.info(f"Best model: {best_model_type} with RMSE={results[best_model_type]['rmse']:.2f}")
            
        return results
        
    def predict(self, X_new, model_type=None):
        """
        Make predictions with a trained model.
        
        Args:
            X_new (pd.DataFrame): New features
            model_type (str): Type of model to use for prediction, or None to use the best model
            
        Returns:
            np.ndarray: Predictions
        """
        # Determine which model to use
        if model_type is None:
            if self.best_model is None:
                if not self.models:
                    logger.error("No models available for prediction")
                    return None
                model_type = next(iter(self.models.keys()))
            else:
                model_type = self.best_model
                
        if model_type not in self.models:
            logger.error(f"Model {model_type} not found")
            return None
            
        model = self.models[model_type]
        
        # Scale features
        X_new_scaled = self.scaler.transform(X_new)
        
        # Make predictions
        predictions = model.predict(X_new_scaled)
        
        logger.info(f"Generated {len(predictions)} predictions using {model_type} model")
        
        return predictions
        
    def plot_feature_importance(self, model_type=None, top_n=20, figsize=(10, 8)):
        """
        Plot feature importances.
        
        Args:
            model_type (str): Type of model to plot feature importances for
            top_n (int): Number of top features to show
            figsize (tuple): Figure size
            
        Returns:
            matplotlib.figure.Figure: Figure object
        """
        import matplotlib.pyplot as plt
        
        # Determine which model to use
        if model_type is None:
            if self.best_model is None:
                if not self.feature_importances:
                    logger.error("No feature importances available")
                    return None
                model_type = next(iter(self.feature_importances.keys()))
            else:
                model_type = self.best_model
                
        if model_type not in self.feature_importances:
            logger.error(f"Feature importances for {model_type} not found")
            return None
            
        # Get feature importances
        importances = self.feature_importances[model_type]
        
        if isinstance(importances, pd.DataFrame):
            # Already processed
            importance_df = importances
        else:
            # Need to process
            if not hasattr(self, 'feature_names') or not self.feature_names:
                logger.error("Feature names not available")
                return None
                
            importance_df = pd.DataFrame({
                'feature': self.feature_names[:len(importances)],
                'importance': importances
            })
            importance_df = importance_df.sort_values('importance', ascending=False)
            
        # Plot
        fig, ax = plt.subplots(figsize=figsize)
        
        # Get top N features
        top_features = importance_df.head(top_n)
        
        # Create horizontal bar chart
        ax.barh(top_features['feature'], top_features['importance'])
        
        # Customize plot
        ax.set_title(f"Top {top_n} Feature Importances ({model_type})")
        ax.set_xlabel('Importance')
        ax.set_ylabel('Feature')
        ax.invert_yaxis()  # Display top features at the top
        
        fig.tight_layout()
        
        return fig
        
    def forecast_future(self, data, steps=12, freq='M', feature_engineer=None, 
                      category=None, model_type=None):
        """
        Generate future forecasts using machine learning models.
        
        Args:
            data (pd.DataFrame): Historical data
            steps (int): Number of steps to forecast
            freq (str): Frequency of the forecast ('M', 'W', 'D', etc.)
            feature_engineer: Feature engineering function to create new features
            category (str): Category to forecast for
            model_type (str): Type of model to use
            
        Returns:
            pd.Series: Forecast values with datetime index
        """
        logger.info(f"Generating {steps}-step forecast with ML model")
        
        # Determine which model to use
        if model_type is None:
            if self.best_model is None:
                if not self.models:
                    logger.error("No models available for forecasting")
                    return None
                model_type = next(iter(self.models.keys()))
            else:
                model_type = self.best_model
                
        if model_type not in self.models:
            logger.error(f"Model {model_type} not found")
            return None
            
        # Get the latest date in the data
        if 'date' in data.columns:
            last_date = data['date'].max()
        else:
            logger.error("Date column not found in data")
            return None
            
        # Create future dates
        if freq == 'M':
            future_dates = pd.date_range(start=last_date, periods=steps+1, freq='M')[1:]
        elif freq == 'W':
            future_dates = pd.date_range(start=last_date, periods=steps+1, freq='W')[1:]
        elif freq == 'D':
            future_dates = pd.date_range(start=last_date, periods=steps+1, freq='D')[1:]
        else:
            logger.error(f"Unsupported frequency: {freq}")
            return None
            
        # Create future dataframe
        future_df = pd.DataFrame({'date': future_dates})
        
        # Add category if specified
        if category is not None:
            future_df['القسم'] = category
            
        # Apply feature engineering if provided
        if feature_engineer is not None:
            try:
                future_df = feature_engineer(future_df)
                logger.info(f"Applied feature engineering to future data")
            except Exception as e:
                logger.error(f"Error applying feature engineering: {e}")
                return None
                
        # Extract features
        X_future = future_df[self.feature_names].values
        
        # Scale features
        X_future_scaled = self.scaler.transform(X_future)
        
        # Make predictions
        predictions = self.models[model_type].predict(X_future_scaled)
        
        # Create forecast series
        forecast = pd.Series(predictions, index=future_dates)
        
        # Ensure non-negative values
        forecast = forecast.clip(lower=0)
        
        logger.info(f"Generated {len(forecast)} forecasts using {model_type} model")
        
        return forecast
        
    def save_model(self, model_type, folder_path='models'):
        """
        Save a trained model to disk.
        
        Args:
            model_type (str): Type of model to save
            folder_path (str): Path to save the model
            
        Returns:
            bool: True if successful, False otherwise
        """
        if model_type not in self.models:
            logger.error(f"Model {model_type} not found")
            return False
            
        # Create folder if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)
        
        try:
            # Save model
            model_path = os.path.join(folder_path, f"ensemble_{model_type}.pkl")
            with open(model_path, 'wb') as f:
                pickle.dump(self.models[model_type], f)
                
            # Save feature importances if available
            if model_type in self.feature_importances:
                importances_path = os.path.join(folder_path, f"ensemble_{model_type}_importances.pkl")
                with open(importances_path, 'wb') as f:
                    pickle.dump(self.feature_importances[model_type], f)
                    
            # Save feature scaler
            scaler_path = os.path.join(folder_path, f"ensemble_scaler.pkl")
            with open(scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
                
            logger.info(f"Model {model_type} saved to {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving model {model_type}: {e}")
            return False
            
    def load_model(self, model_type, folder_path='models'):
        """
        Load a trained model from disk.
        
        Args:
            model_type (str): Type of model to load
            folder_path (str): Path to load the model from
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Load model
            model_path = os.path.join(folder_path, f"ensemble_{model_type}.pkl")
            with open(model_path, 'rb') as f:
                self.models[model_type] = pickle.load(f)
                
            # Load feature importances if available
            importances_path = os.path.join(folder_path, f"ensemble_{model_type}_importances.pkl")
            if os.path.exists(importances_path):
                with open(importances_path, 'rb') as f:
                    self.feature_importances[model_type] = pickle.load(f)
                    
            # Load feature scaler
            scaler_path = os.path.join(folder_path, f"ensemble_scaler.pkl")
            if os.path.exists(scaler_path):
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                    
            logger.info(f"Model {model_type} loaded from {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model {model_type}: {e}")
            return False
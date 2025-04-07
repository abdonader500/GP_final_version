import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import seaborn as sns
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, mean_absolute_percentage_error
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('model_evaluation')

class ModelEvaluator:
    """Class for evaluating and comparing time series forecasting models."""
    
    def __init__(self):
        """Initialize the model evaluator."""
        self.evaluation_results = {}
        self.comparison_results = {}
        
    def evaluate_forecast(self, actual, predicted, model_name="Model", category=None):
        """
        Evaluate a forecast against actual values.
        
        Args:
            actual (pd.Series): Actual values
            predicted (pd.Series): Predicted values
            model_name (str): Name of the model
            category (str): Category name
            
        Returns:
            dict: Evaluation metrics
        """
        # Align series
        aligned_data = pd.DataFrame({
            'actual': actual,
            'forecast': predicted
        })
        
        # Drop rows with missing values
        aligned_data = aligned_data.dropna()
        
        if len(aligned_data) == 0:
            logger.warning(f"No overlapping data points between actual and predicted values for {model_name}")
            return None
            
        # Extract aligned values
        actual_values = aligned_data['actual'].values
        forecast_values = aligned_data['forecast'].values
        
        # Calculate metrics
        rmse = np.sqrt(mean_squared_error(actual_values, forecast_values))
        mae = mean_absolute_error(actual_values, forecast_values)
        r2 = r2_score(actual_values, forecast_values)
        
        # Calculate MAPE, avoiding division by zero
        # Filter out zeros in actual values to avoid division by zero
        mask = actual_values != 0
        if np.sum(mask) > 0:
            mape = np.mean(np.abs((actual_values[mask] - forecast_values[mask]) / actual_values[mask])) * 100
        else:
            mape = np.nan
            
        # If MAPE is infinite or NaN, use an alternative
        if np.isinf(mape) or np.isnan(mape):
            # Use normalized MAE as an alternative
            data_range = np.max(actual_values) - np.min(actual_values)
            if data_range > 0:
                mape = (mae / data_range) * 100
            else:
                mape = np.nan
        
        # Calculate percentage of points where forecast is within X% of actual
        within_5pct = np.mean(np.abs((actual_values - forecast_values) / np.maximum(0.1, actual_values)) <= 0.05) * 100
        within_10pct = np.mean(np.abs((actual_values - forecast_values) / np.maximum(0.1, actual_values)) <= 0.10) * 100
        within_20pct = np.mean(np.abs((actual_values - forecast_values) / np.maximum(0.1, actual_values)) <= 0.20) * 100
        
        # Calculate directional accuracy (correct direction of change)
        actual_diff = np.diff(actual_values)
        forecast_diff = np.diff(forecast_values)
        dir_acc = np.mean((actual_diff * forecast_diff) > 0) * 100
        
        # Create metrics dictionary
        metrics = {
            'rmse': rmse,
            'mae': mae,
            'mape': mape,
            'r2': r2,
            'within_5pct': within_5pct,
            'within_10pct': within_10pct,
            'within_20pct': within_20pct,
            'dir_acc': dir_acc,
            'n_points': len(aligned_data)
        }
        
        # Log results
        logger.info(f"Evaluation metrics for {model_name} "
                   f"{'for category ' + category if category else ''}: "
                   f"RMSE={rmse:.2f}, MAE={mae:.2f}, MAPE={mape:.2f}%, R²={r2:.4f}")
        
        # Store results
        key = f"{model_name}_{category}" if category else model_name
        self.evaluation_results[key] = {
            'metrics': metrics,
            'actual': aligned_data['actual'],
            'forecast': aligned_data['forecast']
        }
        
        return metrics
        
    def compare_models(self, actuals, forecasts, names=None, category=None):
        """
        Compare multiple forecasting models.
        
        Args:
            actuals (pd.Series or dict): Actual values, either a single series or a dict of series by category
            forecasts (dict): Dictionary of forecast series by model name
            names (list): List of model names
            category (str): Category name
            
        Returns:
            pd.DataFrame: Comparison results
        """
        logger.info(f"Comparing {len(forecasts)} models "
                   f"{'for category ' + category if category else ''}")
        
        # Initialize results dictionary
        results = {}
        
        # Get model names
        if names is None:
            names = list(forecasts.keys())
            
        # Process each model
        for model_name in names:
            if model_name not in forecasts:
                logger.warning(f"Forecast for model {model_name} not found. Skipping.")
                continue
                
            forecast = forecasts[model_name]
            
            # Evaluate against actuals
            if isinstance(actuals, dict):
                # Multiple categories
                if category is None:
                    logger.warning("Category must be specified when actuals is a dictionary. Skipping.")
                    continue
                    
                if category not in actuals:
                    logger.warning(f"Actual values for category {category} not found. Skipping.")
                    continue
                    
                actual = actuals[category]
            else:
                # Single series
                actual = actuals
                
            # Evaluate forecast
            metrics = self.evaluate_forecast(
                actual, forecast, model_name=model_name, category=category)
                
            if metrics:
                results[model_name] = metrics
                
        if not results:
            logger.warning("No valid model evaluations to compare")
            return None
            
        # Create comparison dataframe
        comparison_df = pd.DataFrame({
            model: {
                'RMSE': metrics['rmse'],
                'MAE': metrics['mae'],
                'MAPE (%)': metrics['mape'],
                'R²': metrics['r2'],
                'Within 5%': metrics['within_5pct'],
                'Within 10%': metrics['within_10pct'],
                'Within 20%': metrics['within_20pct'],
                'Dir. Acc. (%)': metrics['dir_acc'],
                'Points': metrics['n_points']
            } for model, metrics in results.items()
        })
        
        # Transpose for better readability
        comparison_df = comparison_df.T
        
        # Sort by RMSE (lower is better)
        comparison_df = comparison_df.sort_values('RMSE')
        
        # Store comparison results
        key = category if category else 'all'
        self.comparison_results[key] = comparison_df
        
        return comparison_df
    
    def plot_forecast_comparison(self, model_names=None, category=None, start_date=None, 
                              end_date=None, figsize=(12, 8), include_metrics=True):
        """
        Plot a comparison of actual vs. forecast values for multiple models.
        
        Args:
            model_names (list): List of model names to include
            category (str): Category name
            start_date: Start date for the plot
            end_date: End date for the plot
            figsize (tuple): Figure size
            include_metrics (bool): Whether to include metrics in the plot
            
        Returns:
            matplotlib.figure.Figure: Figure object
        """
        # Create figure
        fig = plt.figure(figsize=figsize)
        
        # Create grid for main plot and metrics table
        if include_metrics:
            gs = GridSpec(2, 1, height_ratios=[3, 1])
            ax_main = fig.add_subplot(gs[0])
            ax_table = fig.add_subplot(gs[1])
        else:
            ax_main = fig.add_subplot(111)
            
        # Get model results to plot
        if model_names is None:
            # Get models from evaluation results
            keys = [k for k in self.evaluation_results.keys() 
                   if (category is None) or (f"_{category}" in k)]
            model_names = [k.split('_')[0] for k in keys]
            
        # Filter evaluation results by models and category
        filtered_results = {}
        for model in model_names:
            key = f"{model}_{category}" if category else model
            if key in self.evaluation_results:
                filtered_results[model] = self.evaluation_results[key]
                
        if not filtered_results:
            logger.warning("No evaluation results found for the specified models and category")
            return None
            
        # Plot actual values
        first_model = next(iter(filtered_results.values()))
        actual = first_model['actual']
        
        # Filter by date range if specified
        if start_date or end_date:
            mask = pd.Series(True, index=actual.index)
            if start_date:
                mask = mask & (actual.index >= pd.to_datetime(start_date))
            if end_date:
                mask = mask & (actual.index <= pd.to_datetime(end_date))
            actual = actual[mask]
            
        # Plot actual values
        ax_main.plot(actual.index, actual.values, 'k-', label='Actual', linewidth=2)
        
        # Plot forecast for each model
        colors = plt.cm.tab10.colors
        for i, (model, result) in enumerate(filtered_results.items()):
            forecast = result['forecast']
            
            # Filter by date range if specified
            if start_date or end_date:
                mask = pd.Series(True, index=forecast.index)
                if start_date:
                    mask = mask & (forecast.index >= pd.to_datetime(start_date))
                if end_date:
                    mask = mask & (forecast.index <= pd.to_datetime(end_date))
                forecast = forecast[mask]
                
            # Plot forecast
            ax_main.plot(forecast.index, forecast.values, '--', 
                       label=model, linewidth=1.5, color=colors[i % len(colors)])
                       
        # Customize main plot
        ax_main.set_title(f"Actual vs. Forecast {'for ' + category if category else ''}")
        ax_main.set_xlabel('Date')
        ax_main.set_ylabel('Value')
        ax_main.grid(True, linestyle='--', alpha=0.6)
        ax_main.legend()
        
        # Add metrics table if requested
        if include_metrics:
            # Get metrics for each model
            metrics_dict = {}
            for model, result in filtered_results.items():
                metrics = result['metrics']
                metrics_dict[model] = {
                    'RMSE': f"{metrics['rmse']:.2f}",
                    'MAE': f"{metrics['mae']:.2f}",
                    'MAPE (%)': f"{metrics['mape']:.2f}",
                    'R²': f"{metrics['r2']:.4f}"
                }
                
            # Create metrics dataframe
            metrics_df = pd.DataFrame(metrics_dict)
            
            # Create table
            ax_table.axis('tight')
            ax_table.axis('off')
            table = ax_table.table(cellText=metrics_df.values,
                                 rowLabels=metrics_df.index,
                                 colLabels=metrics_df.columns,
                                 cellLoc='center',
                                 loc='center')
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.scale(1, 1.5)
            
        fig.tight_layout()
        
        return fig
    
    def plot_forecast_errors(self, model_names=None, category=None, figsize=(15, 10)):
        """
        Plot forecast errors for multiple models.
        
        Args:
            model_names (list): List of model names to include
            category (str): Category name
            figsize (tuple): Figure size
            
        Returns:
            matplotlib.figure.Figure: Figure object
        """
        # Get model results to plot
        if model_names is None:
            # Get models from evaluation results
            keys = [k for k in self.evaluation_results.keys() 
                   if (category is None) or (f"_{category}" in k)]
            model_names = [k.split('_')[0] for k in keys]
            
        # Filter evaluation results by models and category
        filtered_results = {}
        for model in model_names:
            key = f"{model}_{category}" if category else model
            if key in self.evaluation_results:
                filtered_results[model] = self.evaluation_results[key]
                
        if not filtered_results:
            logger.warning("No evaluation results found for the specified models and category")
            return None
            
        # Create figure with 2x2 subplots
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        
        # 1. Error distribution histogram
        ax_hist = axes[0, 0]
        
        # 2. Error over time
        ax_time = axes[0, 1]
        
        # 3. Error vs. actual value
        ax_scatter = axes[1, 0]
        
        # 4. Q-Q plot of errors
        ax_qq = axes[1, 1]
        
        # Plot for each model
        colors = plt.cm.tab10.colors
        for i, (model, result) in enumerate(filtered_results.items()):
            # Calculate errors
            actual = result['actual']
            forecast = result['forecast']
            error = forecast - actual
            pct_error = (error / actual) * 100
            
            # 1. Error distribution histogram
            sns.histplot(error, kde=True, ax=ax_hist, color=colors[i % len(colors)], 
                        alpha=0.4, label=model)
            
            # 2. Error over time
            ax_time.plot(error.index, error.values, 'o-', color=colors[i % len(colors)], 
                       alpha=0.6, label=model)
            
            # 3. Error vs. actual value scatter plot
            ax_scatter.scatter(actual, error, color=colors[i % len(colors)], 
                             alpha=0.6, label=model)
            
            # 4. Q-Q plot
            from scipy import stats
            stats.probplot(error, dist="norm", plot=ax_qq)
            ax_qq.set_title(f"Q-Q Plot for {model}")
            
        # Customize plots
        ax_hist.set_title('Error Distribution')
        ax_hist.set_xlabel('Error')
        ax_hist.set_ylabel('Frequency')
        ax_hist.legend()
        
        ax_time.set_title('Error Over Time')
        ax_time.set_xlabel('Date')
        ax_time.set_ylabel('Error')
        ax_time.grid(True, linestyle='--', alpha=0.6)
        ax_time.legend()
        
        ax_scatter.set_title('Error vs. Actual Value')
        ax_scatter.set_xlabel('Actual Value')
        ax_scatter.set_ylabel('Error')
        ax_scatter.grid(True, linestyle='--', alpha=0.6)
        ax_scatter.axhline(y=0, color='r', linestyle='-', alpha=0.3)
        ax_scatter.legend()
        
        fig.suptitle(f"Forecast Error Analysis {'for ' + category if category else ''}", fontsize=16)
        fig.tight_layout()
        
        return fig
    
    def plot_rolling_metrics(self, model_names=None, category=None, window_size=3, figsize=(12, 10)):
        """
        Plot rolling metrics to evaluate how forecast performance changes over time.
        
        Args:
            model_names (list): List of model names to include
            category (str): Category name
            window_size (int): Window size for rolling metrics
            figsize (tuple): Figure size
            
        Returns:
            matplotlib.figure.Figure: Figure object
        """
        # Get model results to plot
        if model_names is None:
            # Get models from evaluation results
            keys = [k for k in self.evaluation_results.keys() 
                   if (category is None) or (f"_{category}" in k)]
            model_names = [k.split('_')[0] for k in keys]
            
        # Filter evaluation results by models and category
        filtered_results = {}
        for model in model_names:
            key = f"{model}_{category}" if category else model
            if key in self.evaluation_results:
                filtered_results[model] = self.evaluation_results[key]
                
        if not filtered_results:
            logger.warning("No evaluation results found for the specified models and category")
            return None
            
        # Create figure with 2x2 subplots
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        
        # 1. Rolling RMSE
        ax_rmse = axes[0, 0]
        
        # 2. Rolling MAE
        ax_mae = axes[0, 1]
        
        # 3. Rolling MAPE
        ax_mape = axes[1, 0]
        
        # 4. Rolling Directional Accuracy
        ax_dir = axes[1, 1]
        
        # Plot for each model
        colors = plt.cm.tab10.colors
        for i, (model, result) in enumerate(filtered_results.items()):
            # Get actual and forecast values
            actual = result['actual']
            forecast = result['forecast']
            
            # Calculate rolling metrics
            df = pd.DataFrame({'actual': actual, 'forecast': forecast})
            
            # Rolling RMSE
            df['se'] = (df['actual'] - df['forecast']) ** 2
            df['rmse'] = np.sqrt(df['se'].rolling(window=window_size).mean())
            
            # Rolling MAE
            df['ae'] = np.abs(df['actual'] - df['forecast'])
            df['mae'] = df['ae'].rolling(window=window_size).mean()
            
            # Rolling MAPE (handle zeros in actual values)
            df['ape'] = np.abs((df['actual'] - df['forecast']) / df['actual'].replace(0, np.nan)) * 100
            df['mape'] = df['ape'].rolling(window=window_size).mean()
            
            # Rolling Directional Accuracy
            df['actual_diff'] = df['actual'].diff()
            df['forecast_diff'] = df['forecast'].diff()
            df['correct_dir'] = ((df['actual_diff'] * df['forecast_diff']) > 0).astype(int)
            df['dir_acc'] = df['correct_dir'].rolling(window=window_size).mean() * 100
            
            # Plot rolling metrics
            ax_rmse.plot(df.index, df['rmse'], 'o-', color=colors[i % len(colors)], 
                       alpha=0.8, label=model)
            
            ax_mae.plot(df.index, df['mae'], 'o-', color=colors[i % len(colors)], 
                      alpha=0.8, label=model)
            
            ax_mape.plot(df.index, df['mape'], 'o-', color=colors[i % len(colors)], 
                       alpha=0.8, label=model)
            
            ax_dir.plot(df.index, df['dir_acc'], 'o-', color=colors[i % len(colors)], 
                      alpha=0.8, label=model)
            
        # Customize plots
        ax_rmse.set_title(f'Rolling RMSE (Window={window_size})')
        ax_rmse.set_xlabel('Date')
        ax_rmse.set_ylabel('RMSE')
        ax_rmse.grid(True, linestyle='--', alpha=0.6)
        ax_rmse.legend()
        
        ax_mae.set_title(f'Rolling MAE (Window={window_size})')
        ax_mae.set_xlabel('Date')
        ax_mae.set_ylabel('MAE')
        ax_mae.grid(True, linestyle='--', alpha=0.6)
        ax_mae.legend()
        
        ax_mape.set_title(f'Rolling MAPE (Window={window_size})')
        ax_mape.set_xlabel('Date')
        ax_mape.set_ylabel('MAPE (%)')
        ax_mape.grid(True, linestyle='--', alpha=0.6)
        ax_mape.legend()
        
        ax_dir.set_title(f'Rolling Directional Accuracy (Window={window_size})')
        ax_dir.set_xlabel('Date')
        ax_dir.set_ylabel('Directional Accuracy (%)')
        ax_dir.grid(True, linestyle='--', alpha=0.6)
        ax_dir.legend()
        
        fig.suptitle(f"Rolling Forecast Metrics {'for ' + category if category else ''}", fontsize=16)
        fig.tight_layout()
        
        return fig
    
    def seasonal_decomposition(self, data, model='multiplicative', period=12, figsize=(12, 10)):
        """
        Perform seasonal decomposition of time series data.
        
        Args:
            data (pd.Series): Time series data
            model (str): Decomposition model ('multiplicative' or 'additive')
            period (int): Period for seasonal decomposition
            figsize (tuple): Figure size
            
        Returns:
            tuple: (decomposition_result, figure)
        """
        from statsmodels.tsa.seasonal import seasonal_decompose
        
        # Ensure data is a pandas Series with a datetime index
        if not isinstance(data, pd.Series):
            logger.error("Data must be a pandas Series")
            return None, None
            
        if not pd.api.types.is_datetime64_any_dtype(data.index):
            logger.error("Data index must be a datetime")
            return None, None
            
        # Perform seasonal decomposition
        try:
            result = seasonal_decompose(data, model=model, period=period)
            
            # Create figure
            fig = plt.figure(figsize=figsize)
            
            # Plot components
            ax1 = plt.subplot(411)
            ax1.plot(result.observed)
            ax1.set_title('Observed')
            
            ax2 = plt.subplot(412)
            ax2.plot(result.trend)
            ax2.set_title('Trend')
            
            ax3 = plt.subplot(413)
            ax3.plot(result.seasonal)
            ax3.set_title('Seasonal')
            
            ax4 = plt.subplot(414)
            ax4.plot(result.resid)
            ax4.set_title('Residual')
            
            fig.tight_layout()
            
            return result, fig
            
        except Exception as e:
            logger.error(f"Error performing seasonal decomposition: {e}")
            return None, None
    
    def generate_evaluation_report(self, output_path=None):
        """
        Generate a comprehensive evaluation report.
        
        Args:
            output_path (str): Path to save the report
            
        Returns:
            str: Report content
        """
        # TODO: Implement report generation
        logger.warning("Report generation not yet implemented")
        return None
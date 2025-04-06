import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

class FeatureEngineer:
    def __init__(self):
        """Initialize the feature engineer."""
        self.preprocessor = None
        self.fitted = False
        self.categorical_features = None
        self.numerical_features = None
        
    def identify_features(self, df, 
                         categorical_features=None, 
                         numerical_features=None,
                         target_feature=None,
                         exclude_features=None):
        """
        Identify categorical and numerical features in the dataset.
        
        Args:
            df (pandas.DataFrame): Input data
            categorical_features (list): List of categorical feature names (if None, will be auto-detected)
            numerical_features (list): List of numerical feature names (if None, will be auto-detected)
            target_feature (str): Name of target feature to exclude from input features
            exclude_features (list): Additional features to exclude
            
        Returns:
            tuple: (categorical_features, numerical_features)
        """
        if exclude_features is None:
            exclude_features = []
            
        if target_feature:
            exclude_features.append(target_feature)
            
        # Always exclude these identification columns
        exclude_features.extend(['date', '_id', 'year', 'month'])
        
        # Auto-detect categorical features
        if categorical_features is None:
            categorical_features = []
            for col in df.columns:
                if col in exclude_features:
                    continue
                
                if df[col].dtype == 'object' or df[col].nunique() < 10:
                    categorical_features.append(col)
        
        # Auto-detect numerical features
        if numerical_features is None:
            numerical_features = []
            for col in df.columns:
                if col in exclude_features or col in categorical_features:
                    continue
                
                if pd.api.types.is_numeric_dtype(df[col]):
                    numerical_features.append(col)
        
        # Store feature lists
        self.categorical_features = categorical_features
        self.numerical_features = numerical_features
        
        print(f"🔍 Identified {len(categorical_features)} categorical features and {len(numerical_features)} numerical features")
        print(f"  • Categorical: {', '.join(categorical_features[:5])}{'...' if len(categorical_features) > 5 else ''}")
        print(f"  • Numerical: {', '.join(numerical_features[:5])}{'...' if len(numerical_features) > 5 else ''}")
        
        return categorical_features, numerical_features
    
    def create_preprocessor(self, categorical_features=None, numerical_features=None):
        """
        Create a scikit-learn preprocessor for transforming features.
        
        Args:
            categorical_features (list): List of categorical feature names
            numerical_features (list): List of numerical feature names
            
        Returns:
            sklearn.compose.ColumnTransformer: Preprocessor for transforming features
        """
        if categorical_features is None:
            categorical_features = self.categorical_features
            
        if numerical_features is None:
            numerical_features = self.numerical_features
            
        if not categorical_features and not numerical_features:
            print("⚠ No features identified. Please call identify_features first.")
            return None
            
        print("🔧 Creating feature preprocessor...")
        
        # Define preprocessing for categorical features
        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
            ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
        ])
        
        # Define preprocessing for numerical features
        numerical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ])
        
        # Combine preprocessing steps
        preprocessor = ColumnTransformer(
            transformers=[
                ('cat', categorical_transformer, categorical_features),
                ('num', numerical_transformer, numerical_features)
            ],
            remainder='drop'  # Drop any columns not specified in transformers
        )
        
        self.preprocessor = preprocessor
        print("✅ Feature preprocessor created")
        
        return preprocessor
    
    def fit_transform(self, df):
        """
        Fit the preprocessor to the data and transform it.
        
        Args:
            df (pandas.DataFrame): Input data
            
        Returns:
            numpy.ndarray: Transformed feature matrix
        """
        if self.preprocessor is None:
            self.create_preprocessor()
            
        if self.preprocessor is None:
            print("⚠ Preprocessor could not be created.")
            return None
            
        print("🧠 Fitting and transforming features...")
        
        try:
            # Extract only the columns we need
            all_features = self.categorical_features + self.numerical_features
            df_subset = df[all_features].copy()
            
            # Fit and transform
            X = self.preprocessor.fit_transform(df_subset)
            self.fitted = True
            
            print(f"✅ Features transformed. Output shape: {X.shape}")
            return X
            
        except Exception as e:
            print(f"❌ Error fitting/transforming features: {str(e)}")
            return None
            
    def transform(self, df):
        """
        Transform data using the fitted preprocessor.
        
        Args:
            df (pandas.DataFrame): Input data
            
        Returns:
            numpy.ndarray: Transformed feature matrix
        """
        if not self.fitted:
            print("⚠ Preprocessor not fitted. Please call fit_transform first.")
            return None
            
        print("🧩 Transforming features...")
        
        try:
            # Extract only the columns we need
            all_features = self.categorical_features + self.numerical_features
            df_subset = df[all_features].copy()
            
            # Transform
            X = self.preprocessor.transform(df_subset)
            
            print(f"✅ Features transformed. Output shape: {X.shape}")
            return X
            
        except Exception as e:
            print(f"❌ Error transforming features: {str(e)}")
            return None
            
    def create_lagged_features(self, df, target_col, lag_periods=[1, 2, 3, 6, 12], 
                              group_col=None):
        """
        Create lagged features for time series forecasting.
        
        Args:
            df (pandas.DataFrame): Input data with datetime index
            target_col (str): Column to create lags for
            lag_periods (list): List of periods to lag
            group_col (str): Column to group by before creating lags
            
        Returns:
            pandas.DataFrame: DataFrame with lagged features
        """
        print(f"⏰ Creating lagged features for {target_col}...")
        
        # Copy the input data
        result_df = df.copy()
        
        if group_col:
            # Process each group separately
            for group in result_df[group_col].unique():
                group_mask = result_df[group_col] == group
                
                for lag in lag_periods:
                    lag_col = f"{target_col}_lag_{lag}"
                    result_df.loc[group_mask, lag_col] = result_df.loc[group_mask, target_col].shift(lag)
        else:
            # Process the entire dataset
            for lag in lag_periods:
                lag_col = f"{target_col}_lag_{lag}"
                result_df[lag_col] = result_df[target_col].shift(lag)
                
        # Print statistics
        lag_cols = [f"{target_col}_lag_{lag}" for lag in lag_periods]
        non_null_counts = result_df[lag_cols].count()
        print(f"✅ Created {len(lag_cols)} lag features for {target_col}")
        print(f"  • First 3 lags have {non_null_counts[:3].values} non-null values")
        
        return result_df
        
    def create_rolling_features(self, df, target_col, windows=[3, 6, 12], 
                               functions=['mean', 'std', 'min', 'max'], 
                               group_col=None):
        """
        Create rolling window features for time series forecasting.
        
        Args:
            df (pandas.DataFrame): Input data with datetime index
            target_col (str): Column to create rolling features for
            windows (list): List of window sizes
            functions (list): List of functions to apply to rolling windows
            group_col (str): Column to group by before creating rolling features
            
        Returns:
            pandas.DataFrame: DataFrame with rolling features
        """
        print(f"🪟 Creating rolling window features for {target_col}...")
        
        # Copy the input data
        result_df = df.copy()
        
        # Define function mapping
        func_map = {
            'mean': lambda x: x.mean(),
            'std': lambda x: x.std(),
            'min': lambda x: x.min(),
            'max': lambda x: x.max(),
            'median': lambda x: x.median(),
            'sum': lambda x: x.sum(),
            'count': lambda x: x.count(),
            'var': lambda x: x.var()
        }
        
        # Validate functions
        valid_functions = [f for f in functions if f in func_map]
        if len(valid_functions) != len(functions):
            invalid = set(functions) - set(valid_functions)
            print(f"⚠ Ignoring invalid functions: {invalid}")
        
        if group_col:
            # Process each group separately
            for group in result_df[group_col].unique():
                group_mask = result_df[group_col] == group
                
                for window in windows:
                    for func in valid_functions:
                        col_name = f"{target_col}_roll_{window}_{func}"
                        
                        # Create rolling window
                        rolling = result_df.loc[group_mask, target_col].rolling(
                            window=window, min_periods=1)
                        
                        # Apply function
                        result_df.loc[group_mask, col_name] = func_map[func](rolling)
        else:
            # Process the entire dataset
            for window in windows:
                for func in valid_functions:
                    col_name = f"{target_col}_roll_{window}_{func}"
                    
                    # Create rolling window
                    rolling = result_df[target_col].rolling(window=window, min_periods=1)
                    
                    # Apply function
                    result_df[col_name] = func_map[func](rolling)
                    
        # Print statistics
        roll_cols = [f"{target_col}_roll_{windows[0]}_{func}" for func in valid_functions]
        non_null_counts = result_df[roll_cols].count()
        print(f"✅ Created {len(windows) * len(valid_functions)} rolling features for {target_col}")
        print(f"  • First window features have {non_null_counts.values} non-null values")
        
        return result_df
        
    def create_seasonal_features(self, df, date_col='date'):
        """
        Create seasonal features for time series forecasting.
        
        Args:
            df (pandas.DataFrame): Input data
            date_col (str): Column with date values
            
        Returns:
            pandas.DataFrame: DataFrame with seasonal features
        """
        print("🗓️ Creating seasonal features...")
        
        # Copy the input data
        result_df = df.copy()
        
        # Ensure date column is datetime
        if not pd.api.types.is_datetime64_dtype(result_df[date_col]):
            result_df[date_col] = pd.to_datetime(result_df[date_col])
            
        # Extract date components
        result_df['year'] = result_df[date_col].dt.year
        result_df['month'] = result_df[date_col].dt.month
        result_df['quarter'] = result_df[date_col].dt.quarter
        result_df['day_of_week'] = result_df[date_col].dt.dayofweek
        result_df['day_of_month'] = result_df[date_col].dt.day
        result_df['week_of_year'] = result_df[date_col].dt.isocalendar().week
            
        # Cyclical encoding for month, day of week, and day of month
        result_df['month_sin'] = np.sin(2 * np.pi * result_df['month'] / 12)
        result_df['month_cos'] = np.cos(2 * np.pi * result_df['month'] / 12)
        
        result_df['day_of_week_sin'] = np.sin(2 * np.pi * result_df['day_of_week'] / 7)
        result_df['day_of_week_cos'] = np.cos(2 * np.pi * result_df['day_of_week'] / 7)
        
        result_df['day_of_month_sin'] = np.sin(2 * np.pi * result_df['day_of_month'] / 31)
        result_df['day_of_month_cos'] = np.cos(2 * np.pi * result_df['day_of_month'] / 31)
        
        # Add holiday flags (Example for Egypt)
        # Ramadan (approximate - should be replaced with actual dates)
        ramadan_periods = [
            ('2021-04-13', '2021-05-12'),
            ('2022-04-02', '2022-05-01'),
            ('2023-03-23', '2023-04-21'),
            ('2024-03-11', '2024-04-09'),
            ('2025-03-01', '2025-03-30')
        ]
        
        result_df['is_ramadan'] = 0
        for start, end in ramadan_periods:
            mask = (result_df[date_col] >= start) & (result_df[date_col] <= end)
            result_df.loc[mask, 'is_ramadan'] = 1
            
        # Eid al-Fitr (1 day after Ramadan)
        result_df['is_eid_al_fitr'] = 0
        for _, end in ramadan_periods:
            eid_start = pd.to_datetime(end) + pd.Timedelta(days=1)
            eid_end = eid_start + pd.Timedelta(days=3)  # 3-day celebration
            mask = (result_df[date_col] >= eid_start) & (result_df[date_col] <= eid_end)
            result_df.loc[mask, 'is_eid_al_fitr'] = 1
            
        # Eid al-Adha (approximate - should be replaced with actual dates)
        adha_periods = [
            ('2021-07-20', '2021-07-23'),
            ('2022-07-09', '2022-07-12'),
            ('2023-06-28', '2023-07-01'),
            ('2024-06-16', '2024-06-19'),
            ('2025-06-06', '2025-06-09')
        ]
        
        result_df['is_eid_al_adha'] = 0
        for start, end in adha_periods:
            mask = (result_df[date_col] >= start) & (result_df[date_col] <= end)
            result_df.loc[mask, 'is_eid_al_adha'] = 1
            
        # School seasons (approximate for Egypt)
        school_periods = [
            ('2021-01-01', '2021-06-24'), ('2021-09-10', '2021-12-31'),
            ('2022-01-01', '2022-06-23'), ('2022-09-15', '2022-12-31'),
            ('2023-01-01', '2023-06-22'), ('2023-09-12', '2023-12-31'),
            ('2024-01-01', '2024-06-20'), ('2024-09-17', '2024-12-31'),
            ('2025-01-01', '2025-06-26'), ('2025-09-16', '2025-12-31')
        ]
        
        result_df['is_school_season'] = 0
        for start, end in school_periods:
            mask = (result_df[date_col] >= start) & (result_df[date_col] <= end)
            result_df.loc[mask, 'is_school_season'] = 1
            
        # Summer/winter season indicators
        result_df['is_summer'] = result_df['month'].isin([6, 7, 8])
        result_df['is_winter'] = result_df['month'].isin([12, 1, 2])
        
        print(f"✅ Created {result_df.shape[1] - df.shape[1]} seasonal features")
        
        return result_df
        
    def create_price_features(self, df, price_col=None, category_col='القسم'):
        """
        Create price-related features.
        
        Args:
            df (pandas.DataFrame): Input data
            price_col (str): Column with price values
            category_col (str): Column with category values
            
        Returns:
            pandas.DataFrame: DataFrame with price features
        """
        if price_col is None or price_col not in df.columns:
            print("⚠ No valid price column provided. Skipping price features.")
            return df
            
        print(f"💰 Creating price-related features from {price_col}...")
        
        # Copy the input data
        result_df = df.copy()
        
        # Calculate price relative to category average
        category_avg_prices = df.groupby(category_col)[price_col].transform('mean')
        result_df[f'{price_col}_rel_to_cat_avg'] = df[price_col] / category_avg_prices
        
        # Calculate price changes month-over-month for each category
        for category in df[category_col].unique():
            mask = df[category_col] == category
            result_df.loc[mask, f'{price_col}_pct_change'] = df.loc[mask, price_col].pct_change()
            
        # Calculate price features
        # Log price (useful for skewed price distributions)
        result_df[f'{price_col}_log'] = np.log1p(df[price_col])
        
        # Price bins (quintiles within each category)
        for category in df[category_col].unique():
            mask = df[category_col] == category
            result_df.loc[mask, f'{price_col}_quintile'] = pd.qcut(
                df.loc[mask, price_col], 
                q=5, 
                labels=False, 
                duplicates='drop'
            )
            
        print(f"✅ Created {result_df.shape[1] - df.shape[1]} price-related features")
        
        return result_df
        
    def create_interaction_features(self, df, numerical_cols=None, categorical_cols=None):
        """
        Create interaction features between numerical and categorical variables.
        
        Args:
            df (pandas.DataFrame): Input data
            numerical_cols (list): List of numerical column names
            categorical_cols (list): List of categorical column names
            
        Returns:
            pandas.DataFrame: DataFrame with interaction features
        """
        if numerical_cols is None:
            numerical_cols = self.numerical_features
            
        if categorical_cols is None:
            categorical_cols = self.categorical_features
            
        if not numerical_cols or not categorical_cols:
            print("⚠ No columns provided for interactions. Skipping interaction features.")
            return df
            
        print("🔄 Creating interaction features...")
        
        # Copy the input data
        result_df = df.copy()
        
        # Limit to at most 3 numerical and 3 categorical features to avoid explosion
        num_cols = numerical_cols[:3]
        cat_cols = categorical_cols[:3]
        
        # Create interaction terms
        for num_col in num_cols:
            for cat_col in cat_cols:
                # Skip if either column is not in the dataframe
                if num_col not in df.columns or cat_col not in df.columns:
                    continue
                    
                # Create a feature for each category
                for category in df[cat_col].unique():
                    # Skip if the category is null
                    if pd.isna(category):
                        continue
                        
                    # Create indicator for this category
                    indicator = (df[cat_col] == category).astype(int)
                    
                    # Interaction term
                    result_df[f'{num_col}_x_{cat_col}_{category}'] = df[num_col] * indicator
        
        # Print statistics
        print(f"✅ Created {result_df.shape[1] - df.shape[1]} interaction features")
        
        return result_df
        
    def add_external_data(self, df, date_col='date', category_col='القسم'):
        """
        Add external data to the dataset.
        
        Args:
            df (pandas.DataFrame): Input data
            date_col (str): Column with date values
            category_col (str): Column with category values
            
        Returns:
            pandas.DataFrame: DataFrame with external features
        """
        print("🌍 Adding external data features...")
        
        # Copy the input data
        result_df = df.copy()
        
        # Add Egyptian economic indicators (simplified example)
        # In a real implementation, this would load from an external data source
        
        # Monthly inflation rates (examples)
        inflation_data = {
            '2021-01-01': 4.3, '2021-02-01': 4.5, '2021-03-01': 4.5, '2021-04-01': 4.4,
            '2021-05-01': 4.8, '2021-06-01': 4.9, '2021-07-01': 5.4, '2021-08-01': 5.7,
            '2021-09-01': 6.6, '2021-10-01': 6.3, '2021-11-01': 5.6, '2021-12-01': 5.9,
            '2022-01-01': 7.3, '2022-02-01': 8.8, '2022-03-01': 10.5, '2022-04-01': 13.1,
            '2022-05-01': 13.5, '2022-06-01': 13.2, '2022-07-01': 13.6, '2022-08-01': 14.6,
            '2022-09-01': 15.1, '2022-10-01': 16.2, '2022-11-01': 18.7, '2022-12-01': 21.3,
            '2023-01-01': 25.8, '2023-02-01': 31.9, '2023-03-01': 32.7, '2023-04-01': 30.6,
            '2023-05-01': 29.7, '2023-06-01': 29.2, '2023-07-01': 36.5, '2023-08-01': 37.4,
            '2023-09-01': 38.0, '2023-10-01': 35.8, '2023-11-01': 34.6, '2023-12-01': 33.7,
            '2024-01-01': 29.8, '2024-02-01': 35.7, '2024-03-01': 33.4, '2024-04-01': 32.5,
            '2024-05-01': 30.2, '2024-06-01': 29.6, '2024-07-01': 28.3, '2024-08-01': 26.4,
            '2024-09-01': 24.7, '2024-10-01': 23.5
        }
        
        # Consumer confidence index (examples)
        confidence_data = {
            '2021-01-01': 85, '2021-04-01': 83, '2021-07-01': 87, '2021-10-01': 84,
            '2022-01-01': 80, '2022-04-01': 75, '2022-07-01': 72, '2022-10-01': 68,
            '2023-01-01': 65, '2023-04-01': 62, '2023-07-01': 60, '2023-10-01': 63,
            '2024-01-01': 67, '2024-04-01': 70, '2024-07-01': 72, '2024-10-01': 76
        }
        
        # Convert date to period
        result_df['year_month'] = pd.to_datetime(result_df[date_col]).dt.to_period('M').astype(str)
        
        # Add inflation data
        inflation_series = pd.Series(inflation_data)
        inflation_series.index = pd.to_datetime(inflation_series.index).to_period('M').astype(str)
        
        # Use forward fill for any missing months
        all_months = pd.date_range(min(pd.to_datetime(inflation_series.index)), 
                                  max(pd.to_datetime(inflation_series.index)), 
                                  freq='M')
        all_months = all_months.to_period('M').astype(str)
        
        complete_inflation = pd.Series(index=all_months, dtype=float)
        for month in inflation_series.index:
            complete_inflation[month] = inflation_series[month]
        
        complete_inflation = complete_inflation.fillna(method='ffill')
        
        # Map to dataframe
        result_df['inflation_rate'] = result_df['year_month'].map(complete_inflation)
        
        # Add consumer confidence data (quarterly, need to fill monthly)
        confidence_series = pd.Series(confidence_data)
        confidence_series.index = pd.to_datetime(confidence_series.index).to_period('M').astype(str)
        
        all_quarters = pd.date_range(min(pd.to_datetime(confidence_series.index)), 
                                     max(pd.to_datetime(confidence_series.index)), 
                                     freq='Q')
        all_quarters = all_quarters.to_period('M').astype(str)
        
        complete_confidence = pd.Series(index=all_quarters, dtype=float)
        for quarter in confidence_series.index:
            complete_confidence[quarter] = confidence_series[quarter]
            
        complete_confidence = complete_confidence.fillna(method='ffill')
        
        # Expand quarterly data to monthly
        monthly_confidence = {}
        for quarter in complete_confidence.index:
            quarter_date = pd.to_datetime(quarter)
            for i in range(3):
                month_date = quarter_date + pd.DateOffset(months=i)
                month_key = month_date.to_period('M').astype(str)
                monthly_confidence[month_key] = complete_confidence[quarter]
                
        # Map to dataframe
        result_df['consumer_confidence'] = result_df['year_month'].map(pd.Series(monthly_confidence))
        
        # Add category-specific external data
        # Example: clothing import data for clothing categories
        clothing_categories = ['حريمى', 'رجالى', 'اطفال']
        for category in clothing_categories:
            if category in result_df[category_col].unique():
                # Example simplified trend data
                result_df.loc[result_df[category_col] == category, 'import_trend'] = \
                    (result_df['year_month'].astype(str) > '2022-06') * 0.8 + 1.0
        
        # Drop temporary columns
        result_df.drop('year_month', axis=1, inplace=True)
        
        print(f"✅ Added {result_df.shape[1] - df.shape[1]} external data features")
        
        return result_df
            
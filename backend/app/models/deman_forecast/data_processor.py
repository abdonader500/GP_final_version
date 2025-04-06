import pandas as pd
import numpy as np
from datetime import datetime
from app.models.database import fetch_data

class DemandDataProcessor:
    def __init__(self):
        """Initialize the demand data processor."""
        self.raw_data = None
        self.processed_data = None
        self.train_data = None
        self.test_data = None
        self.categories = None
        self.specifications = {}

    def fetch_historical_data(self, collection="category_monthly_demand", query=None, 
                              start_year=None, end_year=None, categories=None):
        """
        Fetch historical demand data from MongoDB.
        
        Args:
            collection (str): MongoDB collection name
            query (dict): Additional query parameters
            start_year (int): Filter data starting from this year
            end_year (int): Filter data until this year
            categories (list): List of categories to include
            
        Returns:
            pandas.DataFrame: Processed historical data
        """
        print(f"📊 Fetching historical data from {collection}...")
        
        # Build the query
        if query is None:
            query = {}
            
        if start_year is not None:
            query["year"] = {"$gte": start_year}
            
        if end_year is not None:
            if "year" not in query:
                query["year"] = {}
            query["year"]["$lte"] = end_year
            
        if categories is not None and len(categories) > 0:
            query["القسم"] = {"$in": categories}
            
        # Fetch data
        data = fetch_data(collection, query=query, projection={"_id": 0})
        
        if not data:
            print("⚠ No data found with the specified filters")
            return None
            
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Convert types 
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["month"] = pd.to_numeric(df["month"], errors="coerce")
        df["total_quantity"] = pd.to_numeric(df["total_quantity"], errors="coerce")
        df["total_money_sold"] = pd.to_numeric(df["total_money_sold"], errors="coerce")
        
        # Filter out rows with missing values
        df.dropna(subset=["year", "month", "total_quantity", "total_money_sold"], inplace=True)
        
        # Create date column
        df["date"] = pd.to_datetime(df.apply(
            lambda x: f"{int(x['year'])}-{int(x['month'])}-01", axis=1
        ))
        
        # Sort by date
        df.sort_values(by="date", inplace=True)
        
        # Store unique categories
        self.categories = df["القسم"].unique().tolist()
        
        # Store raw data
        self.raw_data = df
        
        print(f"✅ Successfully fetched {len(df)} records")
        return df
        
    def fetch_item_specification_data(self, collection="item_specification_monthly_demand", 
                                     query=None, start_year=None, end_year=None, 
                                     categories=None, specifications=None):
        """
        Fetch historical item-level demand data from MongoDB.
        
        Args:
            collection (str): MongoDB collection name
            query (dict): Additional query parameters
            start_year (int): Filter data starting from this year
            end_year (int): Filter data until this year
            categories (list): List of categories to include
            specifications (list): List of product specifications to include
            
        Returns:
            pandas.DataFrame: Processed historical data at item level
        """
        print(f"📊 Fetching item-level historical data from {collection}...")
        
        # Build the query
        if query is None:
            query = {}
            
        if start_year is not None:
            query["year"] = {"$gte": start_year}
            
        if end_year is not None:
            if "year" not in query:
                query["year"] = {}
            query["year"]["$lte"] = end_year
            
        if categories is not None and len(categories) > 0:
            query["القسم"] = {"$in": categories}
            
        if specifications is not None and len(specifications) > 0:
            query["product_specification"] = {"$in": specifications}
            
        # Fetch data
        data = fetch_data(collection, query=query, projection={"_id": 0})
        
        if not data:
            print("⚠ No item-level data found with the specified filters")
            return None
            
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Convert types
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["month"] = pd.to_numeric(df["month"], errors="coerce")
        df["total_quantity"] = pd.to_numeric(df["total_quantity"], errors="coerce")
        df["total_money_sold"] = pd.to_numeric(df["total_money_sold"], errors="coerce")
        
        # Filter out rows with missing values
        df.dropna(subset=["year", "month", "total_quantity", "total_money_sold"], inplace=True)
        
        # Create date column
        df["date"] = pd.to_datetime(df.apply(
            lambda x: f"{int(x['year'])}-{int(x['month'])}-01", axis=1
        ))
        
        # Sort by date
        df.sort_values(by="date", inplace=True)
        
        # Store unique specifications for each category
        for category in df["القسم"].unique():
            self.specifications[category] = df[df["القسم"] == category]["product_specification"].unique().tolist()
            
        print(f"✅ Successfully fetched {len(df)} item-level records")
        return df
        
    def preprocess_data(self, df=None, remove_outliers=True, fill_missing=True,
                       target_variable="total_quantity"):
        """
        Preprocess the demand data.
        
        Args:
            df (pandas.DataFrame): Input dataframe, uses self.raw_data if None
            remove_outliers (bool): Whether to remove outliers
            fill_missing (bool): Whether to fill missing values
            target_variable (str): Target variable for forecasting
            
        Returns:
            pandas.DataFrame: Preprocessed data
        """
        if df is None:
            if self.raw_data is None:
                print("⚠ No data to preprocess. Please fetch data first.")
                return None
            df = self.raw_data.copy()
            
        print(f"🔍 Preprocessing data for {target_variable}...")
        
        # Ensure correct column names
        required_columns = ["القسم", "year", "month", "date", target_variable]
        for col in required_columns:
            if col not in df.columns:
                print(f"⚠ Missing required column: {col}")
                return None
        
        # Remove outliers using IQR method
        if remove_outliers:
            print("📊 Removing outliers using IQR method...")
            for category in df["القسم"].unique():
                category_data = df[df["القسم"] == category]
                
                Q1 = category_data[target_variable].quantile(0.25)
                Q3 = category_data[target_variable].quantile(0.75)
                IQR = Q3 - Q1
                
                # Define bounds with a more conservative multiplier (2.0)
                lower_bound = Q1 - 2.0 * IQR
                upper_bound = Q3 + 2.0 * IQR
                
                # Create a mask for this category's outliers
                outlier_mask = (df["القسم"] == category) & \
                               ((df[target_variable] < lower_bound) | 
                                (df[target_variable] > upper_bound))
                
                # Count outliers
                outlier_count = outlier_mask.sum()
                if outlier_count > 0:
                    print(f"  • Removed {outlier_count} outliers from {category}")
                    
                # Mark outliers as NaN
                df.loc[outlier_mask, target_variable] = np.nan
        
        # Fill missing values
        if fill_missing:
            print("📊 Filling missing values...")
            for category in df["القسم"].unique():
                # Create a mask for this category's missing values
                missing_mask = (df["القسم"] == category) & (df[target_variable].isna())
                missing_count = missing_mask.sum()
                
                if missing_count > 0:
                    # Interpolate missing values for this category
                    category_data = df[df["القسم"] == category].copy()
                    category_data.set_index("date", inplace=True)
                    category_data[target_variable] = category_data[target_variable].interpolate(method='time')
                    
                    # Update the original dataframe
                    df.loc[missing_mask, target_variable] = category_data.loc[df[missing_mask]["date"], target_variable].values
                    print(f"  • Filled {missing_count} missing values in {category}")
        
        # Store processed data
        self.processed_data = df
        
        print(f"✅ Data preprocessing complete. Final shape: {df.shape}")
        return df
        
    def split_train_test(self, df=None, test_size=0.2, by_date=True, test_start_date=None):
        """
        Split the data into training and testing sets.
        
        Args:
            df (pandas.DataFrame): Input dataframe, uses self.processed_data if None
            test_size (float): Proportion of data to use for testing
            by_date (bool): Whether to split by date
            test_start_date (str): Start date for test data (format: 'YYYY-MM-DD')
            
        Returns:
            tuple: (train_df, test_df)
        """
        if df is None:
            if self.processed_data is None:
                print("⚠ No processed data available. Please preprocess data first.")
                return None, None
            df = self.processed_data.copy()
            
        print("🔪 Splitting data into training and testing sets...")
        
        if by_date:
            if test_start_date:
                test_date = pd.to_datetime(test_start_date)
            else:
                # Use the last test_size proportion of dates
                unique_dates = df["date"].sort_values().unique()
                cutoff_idx = int(len(unique_dates) * (1 - test_size))
                test_date = unique_dates[cutoff_idx]
                
            print(f"  • Test data starts from: {test_date.strftime('%Y-%m-%d')}")
            
            train_df = df[df["date"] < test_date].copy()
            test_df = df[df["date"] >= test_date].copy()
        else:
            # Random split
            from sklearn.model_selection import train_test_split
            
            # Split indices to maintain category distribution
            train_indices, test_indices = train_test_split(
                np.arange(len(df)), test_size=test_size, random_state=42,
                stratify=df["القسم"] if len(df["القسم"].unique()) < 10 else None
            )
            
            train_df = df.iloc[train_indices].copy()
            test_df = df.iloc[test_indices].copy()
            
        # Store the splits
        self.train_data = train_df
        self.test_data = test_df
        
        print(f"✅ Train data: {train_df.shape}, Test data: {test_df.shape}")
        return train_df, test_df
        
    def create_time_series_features(self, df=None, add_lag_features=True, 
                                   lag_periods=[1, 3, 6, 12], add_rolling_features=True,
                                   rolling_windows=[3, 6, 12], add_seasonal_features=True):
        """
        Create time series features for forecasting.
        
        Args:
            df (pandas.DataFrame): Input dataframe, uses self.processed_data if None
            add_lag_features (bool): Whether to add lag features
            lag_periods (list): List of lag periods in months
            add_rolling_features (bool): Whether to add rolling window features
            rolling_windows (list): List of rolling window sizes in months
            add_seasonal_features (bool): Whether to add seasonal features
            
        Returns:
            pandas.DataFrame: Dataframe with time series features
        """
        if df is None:
            if self.processed_data is None:
                print("⚠ No processed data available. Please preprocess data first.")
                return None
            df = self.processed_data.copy()
            
        print("🔨 Creating time series features...")
        
        # Make a copy to avoid modifying the original
        result_df = df.copy()
        
        # Extract date components
        result_df["year_num"] = result_df["date"].dt.year
        result_df["month_num"] = result_df["date"].dt.month
        result_df["quarter"] = result_df["date"].dt.quarter
        
        if add_seasonal_features:
            print("  • Adding seasonal features...")
            # Month of year (cyclical encoding)
            result_df["month_sin"] = np.sin(2 * np.pi * result_df["month_num"] / 12)
            result_df["month_cos"] = np.cos(2 * np.pi * result_df["month_num"] / 12)
            
            # Quarter (one-hot encoding would be used in the feature transformation)
            # Adding a flag for Ramadan month (approximate)
            # Note: This should be replaced with actual dates for each year
            ramadan_months = {
                2021: 4,  # April
                2022: 4,  # April
                2023: 3,  # March
                2024: 3,  # March
                2025: 2,   # February
            }
            result_df["is_ramadan"] = result_df.apply(
                lambda x: 1 if x["year_num"] in ramadan_months and 
                                x["month_num"] == ramadan_months[x["year_num"]] else 0,
                axis=1
            )
            
            # Add flags for high-sales seasons (customize based on your business)
            # Example: Eid al-Fitr (1 month after Ramadan)
            result_df["is_eid_al_fitr"] = result_df.apply(
                lambda x: 1 if x["year_num"] in ramadan_months and 
                                x["month_num"] == (ramadan_months[x["year_num"]] + 1) % 12 else 0,
                axis=1
            )
            
            # Winter/summer seasons (Northern Hemisphere)
            result_df["is_winter"] = result_df["month_num"].isin([12, 1, 2])
            result_df["is_summer"] = result_df["month_num"].isin([6, 7, 8])
            
            # School season (customize based on local school calendar)
            result_df["is_school_season"] = result_df["month_num"].isin([9, 10, 11, 12, 1, 2, 3, 4, 5])
            
        # Process each category separately for time series features
        categories = result_df["القسم"].unique()
        
        if add_lag_features or add_rolling_features:
            print("  • Adding time series features by category...")
            
            # Create a list to store processed dataframes for each category
            category_dfs = []
            
            for category in categories:
                category_data = result_df[result_df["القسم"] == category].copy()
                category_data.sort_values(by="date", inplace=True)
                
                # Reset index for shift operations
                category_data.reset_index(drop=True, inplace=True)
                
                if add_lag_features:
                    # Add lag features for each target variable
                    for target in ["total_quantity", "total_money_sold"]:
                        for lag in lag_periods:
                            lag_col = f"{target}_lag_{lag}"
                            category_data[lag_col] = category_data[target].shift(lag)
                
                if add_rolling_features:
                    # Add rolling window statistics
                    for target in ["total_quantity", "total_money_sold"]:
                        for window in rolling_windows:
                            # Rolling average
                            category_data[f"{target}_roll_mean_{window}"] = category_data[target].rolling(
                                window=window, min_periods=1).mean()
                            
                            # Rolling standard deviation
                            category_data[f"{target}_roll_std_{window}"] = category_data[target].rolling(
                                window=window, min_periods=2).std()
                            
                            # Rolling min and max
                            category_data[f"{target}_roll_min_{window}"] = category_data[target].rolling(
                                window=window, min_periods=1).min()
                            category_data[f"{target}_roll_max_{window}"] = category_data[target].rolling(
                                window=window, min_periods=1).max()
                
                # Add back to the list
                category_dfs.append(category_data)
            
            # Combine all category dataframes
            result_df = pd.concat(category_dfs, ignore_index=True)
        
        # Resort by date within each category
        result_df.sort_values(by=["القسم", "date"], inplace=True)
        
        print(f"✅ Created time series features. Final shape: {result_df.shape}")
        return result_df
    
    def identify_top_specifications(self, df=None, category=None, top_n=10, 
                                  metric="total_quantity"):
        """
        Identify top product specifications within a category based on a metric.
        
        Args:
            df (pandas.DataFrame): Input dataframe
            category (str): Category to analyze, or None to analyze all categories
            top_n (int): Number of top specifications to return
            metric (str): Metric to use for ranking ('total_quantity' or 'total_money_sold')
            
        Returns:
            dict: Dictionary of top specifications by category
        """
        if df is None:
            if self.processed_data is None:
                print("⚠ No processed data available.")
                return None
            df = self.processed_data.copy()
            
        # Ensure required columns exist
        required_cols = ["القسم", "product_specification", metric]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"⚠ Missing columns: {missing_cols}")
            return None
            
        print(f"🔍 Identifying top {top_n} specifications by {metric}...")
        
        # Filter by category if specified
        if category:
            df = df[df["القسم"] == category]
            
        # Group by category and specification to sum the metric
        grouped = df.groupby(["القسم", "product_specification"])[metric].sum().reset_index()
        
        # Get top specifications for each category
        top_specs = {}
        
        for cat in grouped["القسم"].unique():
            cat_data = grouped[grouped["القسم"] == cat]
            top_for_category = cat_data.sort_values(by=metric, ascending=False).head(top_n)
            top_specs[cat] = top_for_category["product_specification"].tolist()
            
            print(f"  • {cat}: Top specification is {top_for_category.iloc[0]['product_specification']} with {int(top_for_category.iloc[0][metric])} {metric}")
            
        return top_specs
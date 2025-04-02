import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.models.database import fetch_data, insert_data
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
import tensorflow as tf
import joblib
import os

def predict_demand_2025_ai():
    try:
        print("📊 Starting AI-based demand prediction for 2025...")
        
        # Fetch historical category demand data
        print("📦 Fetching historical daily sales data...")
        sales_data = fetch_data("classified_sales", projection={"_id": 0})
        
        if not sales_data:
            print("⚠ No records found in classified_sales")
            return

        # Convert to DataFrame and prepare data
        df = pd.DataFrame(sales_data)
        df["الكمية"] = pd.to_numeric(df["الكمية"], errors="coerce")
        df["الصافي"] = pd.to_numeric(df["الصافي"], errors="coerce")
        df["التاريخ"] = pd.to_datetime(df["التاريخ"], format="%d/%m/%Y")
        df.dropna(subset=["الكمية", "الصافي", "التاريخ", "القسم", "product_specification"], inplace=True)
        
        # Add day, month, year columns for time features
        df['day'] = df['التاريخ'].dt.day
        df['month'] = df['التاريخ'].dt.month
        df['year'] = df['التاريخ'].dt.year
        df['day_of_week'] = df['التاريخ'].dt.dayofweek
        
        # Filter for relevant time period (e.g., last 2-3 years)
        current_year = datetime.now().year
        df = df[df['year'] >= (current_year - 3)]
        
        # Group by category, specification, and date to get daily totals
        print("📊 Aggregating daily sales data by category and product specification...")
        daily_sales = df.groupby(['القسم', 'product_specification', 'التاريخ']).agg({
            'الكمية': 'sum',
            'الصافي': 'sum'
        }).reset_index()
        
        # Rename columns to be more descriptive
        daily_sales = daily_sales.rename(columns={
            'الكمية': 'quantity',
            'الصافي': 'net_sales'
        })
        
        # Create a complete date range from min to max date in the data
        min_date = daily_sales['التاريخ'].min()
        max_date = daily_sales['التاريخ'].max()
        all_dates = pd.date_range(start=min_date, end=max_date, freq='D')
        
        # Get unique categories and specifications
        categories = daily_sales['القسم'].unique()
        
        # Store predictions
        all_category_predictions = []
        all_item_predictions = []
        all_item_daily_predictions = []
        
        # Path to save models
        model_dir = os.path.join('models', 'demand_forecast')
        os.makedirs(model_dir, exist_ok=True)
        
        # Define future dates for prediction (2025)
        future_start = datetime(2025, 1, 1)
        future_end = datetime(2025, 12, 31)
        future_dates = pd.date_range(start=future_start, end=future_end, freq='D')
        
        # PART 1: Category-level forecasting
        # ----------------------------------------
        print("🔍 Starting category-level forecasting...")
        
        # Group by category and date for category-level forecasting
        category_daily_sales = df.groupby(['القسم', 'التاريخ']).agg({
            'الكمية': 'sum',
            'الصافي': 'sum'
        }).reset_index()
        
        # Rename columns to be more descriptive
        category_daily_sales = category_daily_sales.rename(columns={
            'الكمية': 'quantity',
            'الصافي': 'net_sales'
        })
        
        # For each category, fit a model and generate predictions
        for category in categories:
            print(f"🔍 Processing category: {category}")
            
            # Filter data for this category
            cat_data = category_daily_sales[category_daily_sales['القسم'] == category].copy()
            
            # If not enough data, skip this category
            if len(cat_data) < 30:  # Require at least 30 data points
                print(f"⚠ Not enough data for category {category}, skipping...")
                continue
                
            # Create a complete time series with all dates
            cat_ts = pd.DataFrame(index=all_dates)
            cat_ts.index.name = 'date'
            
            # Merge with actual sales data
            cat_ts = cat_ts.merge(
                cat_data, 
                left_index=True, 
                right_on='التاريخ', 
                how='left'
            )
            
            # Fill missing dates with zeros or interpolate
            cat_ts['quantity'] = cat_ts['quantity'].fillna(0)
            cat_ts['net_sales'] = cat_ts['net_sales'].fillna(0)
            
            # Extract features for the model
            cat_ts['day'] = cat_ts.index.day
            cat_ts['month'] = cat_ts.index.month
            cat_ts['year'] = cat_ts.index.year
            cat_ts['day_of_week'] = cat_ts.index.dayofweek
            
            # Add lag features (past 7 days and past 30 days average)
            cat_ts['quantity_lag7'] = cat_ts['quantity'].rolling(window=7).mean()
            cat_ts['quantity_lag30'] = cat_ts['quantity'].rolling(window=30).mean()
            cat_ts['net_sales_lag7'] = cat_ts['net_sales'].rolling(window=7).mean()
            cat_ts['net_sales_lag30'] = cat_ts['net_sales'].rolling(window=30).mean()
            
            # Fill NAs created by lag features
            cat_ts = cat_ts.fillna(0)
            
            # Create sequences for LSTM model - predict next 7 days based on past 30 days
            seq_length = 30
            X, y_quantity, y_sales = [], [], []
            
            for i in range(len(cat_ts) - seq_length - 7):
                # Features: past 30 days data
                X.append(cat_ts.iloc[i:i+seq_length][['quantity', 'net_sales', 'day', 'month', 'year', 
                                                      'day_of_week', 'quantity_lag7', 'quantity_lag30', 
                                                      'net_sales_lag7', 'net_sales_lag30']].values)
                # Target: next 7 days quantity
                y_quantity.append(cat_ts.iloc[i+seq_length:i+seq_length+7]['quantity'].values)
                # Target: next 7 days sales
                y_sales.append(cat_ts.iloc[i+seq_length:i+seq_length+7]['net_sales'].values)
            
            # Skip if not enough sequence data
            if len(X) < 10:
                print(f"⚠ Not enough sequence data for category {category}, skipping...")
                continue
                
            # Convert to numpy arrays
            X = np.array(X)
            y_quantity = np.array(y_quantity)
            y_sales = np.array(y_sales)
            
            # Scale the data
            scaler_X = MinMaxScaler()
            # Reshape for scaling (combine batch and time dimensions)
            X_reshaped = X.reshape(-1, X.shape[-1])
            X_scaled = scaler_X.fit_transform(X_reshaped)
            # Reshape back
            X_scaled = X_scaled.reshape(X.shape)
            
            scaler_y_quantity = MinMaxScaler()
            y_quantity_reshaped = y_quantity.reshape(-1, 1)
            y_quantity_scaled = scaler_y_quantity.fit_transform(y_quantity_reshaped)
            y_quantity_scaled = y_quantity_scaled.reshape(y_quantity.shape)
            
            scaler_y_sales = MinMaxScaler()
            y_sales_reshaped = y_sales.reshape(-1, 1)
            y_sales_scaled = scaler_y_sales.fit_transform(y_sales_reshaped)
            y_sales_scaled = y_sales_scaled.reshape(y_sales.shape)
            
            # Save scalers
            joblib.dump(scaler_X, os.path.join(model_dir, f'{category}_scaler_X.pkl'))
            joblib.dump(scaler_y_quantity, os.path.join(model_dir, f'{category}_scaler_y_quantity.pkl'))
            joblib.dump(scaler_y_sales, os.path.join(model_dir, f'{category}_scaler_y_sales.pkl'))
            
            # Split data into train and test sets (80/20)
            split_idx = int(len(X_scaled) * 0.8)
            X_train, X_test = X_scaled[:split_idx], X_scaled[split_idx:]
            y_quantity_train, y_quantity_test = y_quantity_scaled[:split_idx], y_quantity_scaled[split_idx:]
            y_sales_train, y_sales_test = y_sales_scaled[:split_idx], y_sales_scaled[split_idx:]
            
            # Build quantity prediction model (LSTM for time series forecasting)
            print(f"🧠 Building quantity prediction model for {category}...")
            model_quantity = Sequential([
                LSTM(64, return_sequences=True, input_shape=(seq_length, X.shape[-1])),
                Dropout(0.2),
                LSTM(32),
                Dropout(0.2),
                Dense(y_quantity.shape[1])  # Output 7 days of predictions
            ])
            
            model_quantity.compile(optimizer='adam', loss='mse')
            
            # Train the model with early stopping
            model_quantity.fit(
                X_train, y_quantity_train,
                epochs=100,
                batch_size=32,
                validation_data=(X_test, y_quantity_test),
                verbose=0,
                callbacks=[
                    # Add early stopping to prevent overfitting
                    tf.keras.callbacks.EarlyStopping(
                        monitor='val_loss',
                        patience=10,
                        restore_best_weights=True
                    )
                ]
            )
            
            # Save the model
            model_quantity.save(os.path.join(model_dir, f'{category}_quantity_model.h5'))
            
            # Build sales prediction model
            print(f"🧠 Building sales prediction model for {category}...")
            model_sales = Sequential([
                LSTM(64, return_sequences=True, input_shape=(seq_length, X.shape[-1])),
                Dropout(0.2),
                LSTM(32),
                Dropout(0.2),
                Dense(y_sales.shape[1])  # Output 7 days of predictions
            ])
            
            model_sales.compile(optimizer='adam', loss='mse')
            
            # Train the model with early stopping
            model_sales.fit(
                X_train, y_sales_train,
                epochs=100,
                batch_size=32,
                validation_data=(X_test, y_sales_test),
                verbose=0,
                callbacks=[
                    # Add early stopping to prevent overfitting
                    tf.keras.callbacks.EarlyStopping(
                        monitor='val_loss',
                        patience=10,
                        restore_best_weights=True
                    )
                ]
            )
            
            # Save the model
            model_sales.save(os.path.join(model_dir, f'{category}_sales_model.h5'))
            
            # Generate predictions for 2025
            print(f"🔮 Generating 2025 predictions for item {category} - {spec}...")
            
            # Prepare future features
            item_future_df = pd.DataFrame(index=future_dates)
            item_future_df.index.name = 'date'
            item_future_df['day'] = item_future_df.index.day
            item_future_df['month'] = item_future_df.index.month
            item_future_df['year'] = item_future_df.index.year
            item_future_df['day_of_week'] = item_future_df.index.dayofweek
            
            # Initialize quantity and sales columns
            item_future_df['quantity'] = 0
            item_future_df['net_sales'] = 0
            
            # Get the latest actual data to start predictions
            last_actual_data = item_ts.iloc[-seq_length:][['quantity', 'net_sales', 'day', 'month', 'year', 
                                                          'day_of_week', 'quantity_lag7', 'quantity_lag30', 
                                                          'net_sales_lag7', 'net_sales_lag30']].values
            
            # Initial input
            current_input = last_actual_data.copy()
            
            # Predict the entire year in 7-day chunks
            for i in range(0, len(item_future_df), 7):
                end_idx = min(i + 7, len(item_future_df))
                days_to_predict = end_idx - i
                
                # Scale the input
                current_input_reshaped = current_input.reshape(-1, current_input.shape[-1])
                current_input_scaled = item_scaler_X.transform(current_input_reshaped)
                current_input_scaled = current_input_scaled.reshape(1, seq_length, current_input.shape[-1])
                
                # Predict quantity
                pred_quantity_scaled = item_model_quantity.predict(current_input_scaled, verbose=0)
                pred_quantity_reshaped = pred_quantity_scaled.reshape(-1, 1)
                pred_quantity = item_scaler_y_quantity.inverse_transform(pred_quantity_reshaped)
                pred_quantity = pred_quantity.reshape(-1)[:days_to_predict]
                
                # Predict sales
                pred_sales_scaled = item_model_sales.predict(current_input_scaled, verbose=0)
                pred_sales_reshaped = pred_sales_scaled.reshape(-1, 1)
                pred_sales = item_scaler_y_sales.inverse_transform(pred_sales_reshaped)
                pred_sales = pred_sales.reshape(-1)[:days_to_predict]
                
                # Ensure predictions are positive
                pred_quantity = np.maximum(0, pred_quantity)
                pred_sales = np.maximum(0, pred_sales)
                
                # Store predictions
                item_future_df.iloc[i:end_idx, item_future_df.columns.get_loc('quantity')] = pred_quantity
                item_future_df.iloc[i:end_idx, item_future_df.columns.get_loc('net_sales')] = pred_sales
                
                if i + 7 < len(item_future_df):
                    # Update lag features for next prediction
                    item_future_df['quantity_lag7'] = item_future_df['quantity'].rolling(window=7).mean()
                    item_future_df['quantity_lag30'] = item_future_df['quantity'].rolling(window=30).mean()
                    item_future_df['net_sales_lag7'] = item_future_df['net_sales'].rolling(window=7).mean()
                    item_future_df['net_sales_lag30'] = item_future_df['net_sales'].rolling(window=30).mean()
                    item_future_df = item_future_df.fillna(0)
                    
                    # Update input for next prediction (sliding window)
                    next_seq = item_future_df.iloc[i:i+days_to_predict][
                        ['quantity', 'net_sales', 'day', 'month', 'year', 'day_of_week', 
                         'quantity_lag7', 'quantity_lag30', 'net_sales_lag7', 'net_sales_lag30']
                    ].values
                    
                    # Combine with previous input to maintain sequence length
                    current_input = np.vstack([current_input[days_to_predict:], next_seq])
            
            # Aggregate daily predictions to monthly for comparison with existing system
            item_monthly_predictions = item_future_df.resample('M').agg({
                'quantity': 'sum',
                'net_sales': 'sum'
            }).reset_index()
            
            # Format the data for database storage - monthly
            for _, row in item_monthly_predictions.iterrows():
                month_num = row['date'].month
                all_item_predictions.append({
                    'القسم': category,
                    'product_specification': spec,
                    'month': month_num,
                    'year': 2025,
                    'predicted_quantity': float(row['quantity']),
                    'predicted_money_sold': float(row['net_sales'])
                })
            
            # Also store daily predictions for more granular forecasting
            item_daily_records = []
            
            for _, row in item_future_df.reset_index().iterrows():
                item_daily_records.append({
                    'القسم': category,
                    'product_specification': spec,
                    'date': row['date'].strftime('%Y-%m-%d'),
                    'day': int(row['day']),
                    'month': int(row['month']),
                    'year': int(row['year']),
                    'day_of_week': int(row['day_of_week']),
                    'predicted_quantity': float(row['quantity']),
                    'predicted_money_sold': float(row['net_sales'])
                })
            
            # Add to the main daily records array
            print(f"💾 Storing daily predictions for item {category} - {spec}...")
            insert_data("predicted_daily_demand_2025", item_daily_records)(f"🔮 Generating 2025 predictions for category {category}...")
            
            # Prepare future features
            future_df = pd.DataFrame(index=future_dates)
            future_df.index.name = 'date'
            future_df['day'] = future_df.index.day
            future_df['month'] = future_df.index.month
            future_df['year'] = future_df.index.year
            future_df['day_of_week'] = future_df.index.dayofweek
            
            # Initialize quantity and sales columns
            future_df['quantity'] = 0
            future_df['net_sales'] = 0
            
            # We'll predict in sliding windows of 7 days
            predictions_quantity = []
            predictions_sales = []
            
            # Get the latest actual data to start predictions
            last_actual_data = cat_ts.iloc[-seq_length:][['quantity', 'net_sales', 'day', 'month', 'year', 
                                                         'day_of_week', 'quantity_lag7', 'quantity_lag30', 
                                                         'net_sales_lag7', 'net_sales_lag30']].values
            
            # Initial input
            current_input = last_actual_data.copy()
            
            # Predict the entire year in 7-day chunks
            for i in range(0, len(future_df), 7):
                end_idx = min(i + 7, len(future_df))
                days_to_predict = end_idx - i
                
                # Scale the input
                current_input_reshaped = current_input.reshape(-1, current_input.shape[-1])
                current_input_scaled = scaler_X.transform(current_input_reshaped)
                current_input_scaled = current_input_scaled.reshape(1, seq_length, current_input.shape[-1])
                
                # Predict quantity
                pred_quantity_scaled = model_quantity.predict(current_input_scaled, verbose=0)
                pred_quantity_reshaped = pred_quantity_scaled.reshape(-1, 1)
                pred_quantity = scaler_y_quantity.inverse_transform(pred_quantity_reshaped)
                pred_quantity = pred_quantity.reshape(-1)[:days_to_predict]
                
                # Predict sales
                pred_sales_scaled = model_sales.predict(current_input_scaled, verbose=0)
                pred_sales_reshaped = pred_sales_scaled.reshape(-1, 1)
                pred_sales = scaler_y_sales.inverse_transform(pred_sales_reshaped)
                pred_sales = pred_sales.reshape(-1)[:days_to_predict]
                
                # Ensure predictions are positive
                pred_quantity = np.maximum(0, pred_quantity)
                pred_sales = np.maximum(0, pred_sales)
                
                # Store predictions
                future_df.iloc[i:end_idx, future_df.columns.get_loc('quantity')] = pred_quantity
                future_df.iloc[i:end_idx, future_df.columns.get_loc('net_sales')] = pred_sales
                
                if i + 7 < len(future_df):
                    # Update lag features for next prediction
                    future_df['quantity_lag7'] = future_df['quantity'].rolling(window=7).mean()
                    future_df['quantity_lag30'] = future_df['quantity'].rolling(window=30).mean()
                    future_df['net_sales_lag7'] = future_df['net_sales'].rolling(window=7).mean()
                    future_df['net_sales_lag30'] = future_df['net_sales'].rolling(window=30).mean()
                    future_df = future_df.fillna(0)
                    
                    # Update input for next prediction (sliding window)
                    next_seq = future_df.iloc[i:i+days_to_predict][
                        ['quantity', 'net_sales', 'day', 'month', 'year', 'day_of_week', 
                         'quantity_lag7', 'quantity_lag30', 'net_sales_lag7', 'net_sales_lag30']
                    ].values
                    
                    # Combine with previous input to maintain sequence length
                    current_input = np.vstack([current_input[days_to_predict:], next_seq])
            
            # Aggregate daily predictions to monthly for comparison with existing system
            monthly_predictions = future_df.resample('M').agg({
                'quantity': 'sum',
                'net_sales': 'sum'
            }).reset_index()
            
            # Format the data for database storage
            for _, row in monthly_predictions.iterrows():
                month_num = row['date'].month
                all_category_predictions.append({
                    'القسم': category,
                    'month': month_num,
                    'year': 2025,
                    'predicted_quantity': float(row['quantity']),
                    'predicted_money_sold': float(row['net_sales'])
                })
            
            # Also store daily predictions for more granular forecasting
            daily_records = []
            
            for _, row in future_df.reset_index().iterrows():
                daily_records.append({
                    'القسم': category,
                    'product_specification': 'all',  # Indicating category-level prediction
                    'date': row['date'].strftime('%Y-%m-%d'),
                    'day': int(row['day']),
                    'month': int(row['month']),
                    'year': int(row['year']),
                    'day_of_week': int(row['day_of_week']),
                    'predicted_quantity': float(row['quantity']),
                    'predicted_money_sold': float(row['net_sales'])
                })
            
            # Store daily predictions
            print(f"💾 Storing daily predictions for category {category}...")
            insert_data("predicted_daily_demand_2025", daily_records)
        
        # PART 2: Item-level forecasting (product specification)
        # -----------------------------------------------------
        print("🔍 Starting item-level forecasting...")
        
        # Get unique category-specification combinations
        category_specs = daily_sales.groupby(['القسم', 'product_specification']).size().reset_index()[['القسم', 'product_specification']]
        
        # For each category-specification combination, fit a model and generate predictions
        for idx, row in category_specs.iterrows():
            category = row['القسم']
            spec = row['product_specification']
            
            print(f"🔍 Processing item: {category} - {spec}")
            
            # Filter data for this category and specification
            item_data = daily_sales[(daily_sales['القسم'] == category) & 
                                    (daily_sales['product_specification'] == spec)].copy()
            
            # If not enough data, skip this item
            if len(item_data) < 20:  # Require at least 20 data points for items
                print(f"⚠ Not enough data for item {category} - {spec}, using simple average...")
                
                # Use simple average if not enough data for ML
                avg_quantity = item_data['quantity'].mean()
                avg_sales = item_data['net_sales'].mean()
                
                # If we have monthly patterns, use them
                monthly_avgs = item_data.groupby(item_data['التاريخ'].dt.month).agg({
                    'quantity': 'mean',
                    'net_sales': 'mean'
                })
                
                # Generate simple predictions for each month
                for month in range(1, 13):
                    if month in monthly_avgs.index:
                        month_avg_quantity = monthly_avgs.loc[month, 'quantity']
                        month_avg_sales = monthly_avgs.loc[month, 'net_sales']
                    else:
                        month_avg_quantity = avg_quantity
                        month_avg_sales = avg_sales
                    
                    # Calculate days in this month in 2025
                    if month == 2:
                        # Check if 2025 is a leap year
                        days_in_month = 29 if (2025 % 4 == 0 and 2025 % 100 != 0) or (2025 % 400 == 0) else 28
                    elif month in [4, 6, 9, 11]:
                        days_in_month = 30
                    else:
                        days_in_month = 31
                    
                    # Add to monthly predictions
                    all_item_predictions.append({
                        'القسم': category,
                        'product_specification': spec,
                        'month': month,
                        'year': 2025,
                        'predicted_quantity': float(month_avg_quantity * days_in_month),
                        'predicted_money_sold': float(month_avg_sales * days_in_month)
                    })
                    
                    # Generate daily predictions too
                    for day in range(1, days_in_month + 1):
                        # Create date object
                        date_obj = datetime(2025, month, day)
                        
                        all_item_daily_predictions.append({
                            'القسم': category,
                            'product_specification': spec,
                            'date': date_obj.strftime('%Y-%m-%d'),
                            'day': day,
                            'month': month,
                            'year': 2025,
                            'day_of_week': date_obj.weekday(),
                            'predicted_quantity': float(month_avg_quantity),
                            'predicted_money_sold': float(month_avg_sales)
                        })
                
                continue
                
            # Create a complete time series with all dates
            item_ts = pd.DataFrame(index=all_dates)
            item_ts.index.name = 'date'
            
            # Merge with actual sales data
            item_ts = item_ts.merge(
                item_data, 
                left_index=True, 
                right_on='التاريخ', 
                how='left'
            )
            
            # Fill missing dates with zeros or interpolate
            item_ts['quantity'] = item_ts['quantity'].fillna(0)
            item_ts['net_sales'] = item_ts['net_sales'].fillna(0)
            
            # Extract features for the model
            item_ts['day'] = item_ts.index.day
            item_ts['month'] = item_ts.index.month
            item_ts['year'] = item_ts.index.year
            item_ts['day_of_week'] = item_ts.index.dayofweek
            
            # Add lag features (past 7 days and past 30 days average)
            item_ts['quantity_lag7'] = item_ts['quantity'].rolling(window=7).mean()
            item_ts['quantity_lag30'] = item_ts['quantity'].rolling(window=30).mean()
            item_ts['net_sales_lag7'] = item_ts['net_sales'].rolling(window=7).mean()
            item_ts['net_sales_lag30'] = item_ts['net_sales'].rolling(window=30).mean()
            
            # Fill NAs created by lag features
            item_ts = item_ts.fillna(0)
            
            # Create sequences for LSTM model - predict next 7 days based on past 30 days
            seq_length = 30
            X, y_quantity, y_sales = [], [], []
            
            for i in range(len(item_ts) - seq_length - 7):
                # Features: past 30 days data
                X.append(item_ts.iloc[i:i+seq_length][['quantity', 'net_sales', 'day', 'month', 'year', 
                                                       'day_of_week', 'quantity_lag7', 'quantity_lag30', 
                                                       'net_sales_lag7', 'net_sales_lag30']].values)
                # Target: next 7 days quantity
                y_quantity.append(item_ts.iloc[i+seq_length:i+seq_length+7]['quantity'].values)
                # Target: next 7 days sales
                y_sales.append(item_ts.iloc[i+seq_length:i+seq_length+7]['net_sales'].values)
            
            # Skip if not enough sequence data
            if len(X) < 10:
                print(f"⚠ Not enough sequence data for item {category} - {spec}, using simple approach...")
                
                # Use simple average if not enough data for ML
                avg_quantity = item_data['quantity'].mean()
                avg_sales = item_data['net_sales'].mean()
                
                # Group by month to capture seasonality
                monthly_avgs = item_data.groupby(item_data['التاريخ'].dt.month).agg({
                    'quantity': 'mean',
                    'net_sales': 'mean'
                })
                
                # Generate simple predictions for each month
                for month in range(1, 13):
                    if month in monthly_avgs.index:
                        month_avg_quantity = monthly_avgs.loc[month, 'quantity']
                        month_avg_sales = monthly_avgs.loc[month, 'net_sales']
                    else:
                        month_avg_quantity = avg_quantity
                        month_avg_sales = avg_sales
                    
                    # Calculate days in this month in 2025
                    if month == 2:
                        # Check if 2025 is a leap year
                        days_in_month = 29 if (2025 % 4 == 0 and 2025 % 100 != 0) or (2025 % 400 == 0) else 28
                    elif month in [4, 6, 9, 11]:
                        days_in_month = 30
                    else:
                        days_in_month = 31
                    
                    # Add to monthly predictions
                    all_item_predictions.append({
                        'القسم': category,
                        'product_specification': spec,
                        'month': month,
                        'year': 2025,
                        'predicted_quantity': float(month_avg_quantity * days_in_month),
                        'predicted_money_sold': float(month_avg_sales * days_in_month)
                    })
                
                continue
            
            # Convert to numpy arrays
            X = np.array(X)
            y_quantity = np.array(y_quantity)
            y_sales = np.array(y_sales)
            
            # Scale the data
            item_scaler_X = MinMaxScaler()
            # Reshape for scaling (combine batch and time dimensions)
            X_reshaped = X.reshape(-1, X.shape[-1])
            X_scaled = item_scaler_X.fit_transform(X_reshaped)
            # Reshape back
            X_scaled = X_scaled.reshape(X.shape)
            
            item_scaler_y_quantity = MinMaxScaler()
            y_quantity_reshaped = y_quantity.reshape(-1, 1)
            y_quantity_scaled = item_scaler_y_quantity.fit_transform(y_quantity_reshaped)
            y_quantity_scaled = y_quantity_scaled.reshape(y_quantity.shape)
            
            item_scaler_y_sales = MinMaxScaler()
            y_sales_reshaped = y_sales.reshape(-1, 1)
            y_sales_scaled = item_scaler_y_sales.fit_transform(y_sales_reshaped)
            y_sales_scaled = y_sales_scaled.reshape(y_sales.shape)
            
            # Save scalers
            safe_spec = spec.replace('/', '_').replace('\\', '_').replace(' ', '_')
            joblib.dump(item_scaler_X, os.path.join(model_dir, f'{category}_{safe_spec}_scaler_X.pkl'))
            joblib.dump(item_scaler_y_quantity, os.path.join(model_dir, f'{category}_{safe_spec}_scaler_y_quantity.pkl'))
            joblib.dump(item_scaler_y_sales, os.path.join(model_dir, f'{category}_{safe_spec}_scaler_y_sales.pkl'))
            
            # Split data into train and test sets (80/20)
            split_idx = int(len(X_scaled) * 0.8)
            X_train, X_test = X_scaled[:split_idx], X_scaled[split_idx:]
            y_quantity_train, y_quantity_test = y_quantity_scaled[:split_idx], y_quantity_scaled[split_idx:]
            y_sales_train, y_sales_test = y_sales_scaled[:split_idx], y_sales_scaled[split_idx:]
            
            # Build quantity prediction model (LSTM for time series forecasting)
            print(f"🧠 Building quantity prediction model for item {category} - {spec}...")
            item_model_quantity = Sequential([
                LSTM(32, return_sequences=True, input_shape=(seq_length, X.shape[-1])),
                Dropout(0.2),
                LSTM(16),
                Dropout(0.2),
                Dense(y_quantity.shape[1])  # Output 7 days of predictions
            ])
            
            item_model_quantity.compile(optimizer='adam', loss='mse')
            
            # Train the model with early stopping
            item_model_quantity.fit(
                X_train, y_quantity_train,
                epochs=100,
                batch_size=16,
                validation_data=(X_test, y_quantity_test),
                verbose=0,
                callbacks=[
                    tf.keras.callbacks.EarlyStopping(
                        monitor='val_loss',
                        patience=10,
                        restore_best_weights=True
                    )
                ]
            )
            
            # Save the model
            item_model_quantity.save(os.path.join(model_dir, f'{category}_{safe_spec}_quantity_model.h5'))
            
            # Build sales prediction model
            print(f"🧠 Building sales prediction model for item {category} - {spec}...")
            item_model_sales = Sequential([
                LSTM(32, return_sequences=True, input_shape=(seq_length, X.shape[-1])),
                Dropout(0.2),
                LSTM(16),
                Dropout(0.2),
                Dense(y_sales.shape[1])  # Output 7 days of predictions
            ])
            
            item_model_sales.compile(optimizer='adam', loss='mse')
            
            # Train the model with early stopping
            item_model_sales.fit(
                X_train, y_sales_train,
                epochs=100,
                batch_size=16,
                validation_data=(X_test, y_sales_test),
                verbose=0,
                callbacks=[
                    tf.keras.callbacks.EarlyStopping(
                        monitor='val_loss',
                        patience=10,
                        restore_best_weights=True
                    )
                ]
            )
            
            # Save the model
            item_model_sales.save(os.path.join(model_dir, f'{category}_{safe_spec}_sales_model.h5'))
            
            # Generate predictions for 2025
            # Generate predictions for 2025
            print(f"🔮 Generating 2025 predictions for item {category} - {spec}...")
            
            # Prepare future features
            item_future_df = pd.DataFrame(index=future_dates)
            item_future_df.index.name = 'date'
            item_future_df['day'] = item_future_df.index.day
            item_future_df['month'] = item_future_df.index.month
            item_future_df['year'] = item_future_df.index.year
            item_future_df['day_of_week'] = item_future_df.index.dayofweek
            
            # Initialize quantity and sales columns
            item_future_df['quantity'] = 0
            item_future_df['net_sales'] = 0
            
            # Get the latest actual data to start predictions
            last_actual_data = item_ts.iloc[-seq_length:][['quantity', 'net_sales', 'day', 'month', 'year', 
                                                          'day_of_week', 'quantity_lag7', 'quantity_lag30', 
                                                          'net_sales_lag7', 'net_sales_lag30']].values
            
            # Initial input
            current_input = last_actual_data.copy()
            
            # Predict the entire year in 7-day chunks
            for i in range(0, len(item_future_df), 7):
                end_idx = min(i + 7, len(item_future_df))
                days_to_predict = end_idx - i
                
                # Scale the input
                current_input_reshaped = current_input.reshape(-1, current_input.shape[-1])
                current_input_scaled = item_scaler_X.transform(current_input_reshaped)
                current_input_scaled = current_input_scaled.reshape(1, seq_length, current_input.shape[-1])
                
                # Predict quantity
                pred_quantity_scaled = item_model_quantity.predict(current_input_scaled, verbose=0)
                pred_quantity_reshaped = pred_quantity_scaled.reshape(-1, 1)
                pred_quantity = item_scaler_y_quantity.inverse_transform(pred_quantity_reshaped)
                pred_quantity = pred_quantity.reshape(-1)[:days_to_predict]
                
                # Predict sales
                pred_sales_scaled = item_model_sales.predict(current_input_scaled, verbose=0)
                pred_sales_reshaped = pred_sales_scaled.reshape(-1, 1)
                pred_sales = item_scaler_y_sales.inverse_transform(pred_sales_reshaped)
                pred_sales = pred_sales.reshape(-1)[:days_to_predict]
                
                # Ensure predictions are positive
                pred_quantity = np.maximum(0, pred_quantity)
                pred_sales = np.maximum(0, pred_sales)
                
                # Store predictions
                item_future_df.iloc[i:end_idx, item_future_df.columns.get_loc('quantity')] = pred_quantity
                item_future_df.iloc[i:end_idx, item_future_df.columns.get_loc('net_sales')] = pred_sales
                
                if i + 7 < len(item_future_df):
                    # Update lag features for next prediction
                    item_future_df['quantity_lag7'] = item_future_df['quantity'].rolling(window=7).mean()
                    item_future_df['quantity_lag30'] = item_future_df['quantity'].rolling(window=30).mean()
                    item_future_df['net_sales_lag7'] = item_future_df['net_sales'].rolling(window=7).mean()
                    item_future_df['net_sales_lag30'] = item_future_df['net_sales'].rolling(window=30).mean()
                    item_future_df = item_future_df.fillna(0)
                    
                    # Update input for next prediction (sliding window)
                    next_seq = item_future_df.iloc[i:i+days_to_predict][
                        ['quantity', 'net_sales', 'day', 'month', 'year', 'day_of_week', 
                         'quantity_lag7', 'quantity_lag30', 'net_sales_lag7', 'net_sales_lag30']
                    ].values
                    
                    # Combine with previous input to maintain sequence length
                    current_input = np.vstack([current_input[days_to_predict:], next_seq])
            
            # Aggregate daily predictions to monthly for comparison
            item_monthly_predictions = item_future_df.resample('M').agg({
                'quantity': 'sum',
                'net_sales': 'sum'
            }).reset_index()
            
            # Format the data for database storage - monthly
            for _, row in item_monthly_predictions.iterrows():
                month_num = row['date'].month
                all_item_predictions.append({
                    'القسم': category,
                    'product_specification': spec,
                    'month': month_num,
                    'year': 2025,
                    'predicted_quantity': float(row['quantity']),
                    'predicted_money_sold': float(row['net_sales'])
                })
            
            # Store daily predictions for more granular analysis
            daily_records = []
            for _, row in item_future_df.reset_index().iterrows():
                daily_records.append({
                    'القسم': category,
                    'product_specification': spec,
                    'date': row['date'].strftime('%Y-%m-%d'),
                    'day': int(row['day']),
                    'month': int(row['month']),
                    'year': int(row['year']),
                    'day_of_week': int(row['day_of_week']),
                    'predicted_quantity': float(row['quantity']),
                    'predicted_money_sold': float(row['net_sales'])
                })
            
            # Store daily predictions
            print(f"💾 Storing daily predictions for item {category} - {spec}...")
            if daily_records:
                insert_data("predicted_daily_demand_2025", daily_records)
        
        # Store final predictions in database collections
        print("📊 Storing final predictions in database...")
        
        # Insert category-level predictions
        if all_category_predictions:
            print(f"💾 Storing category predictions: {len(all_category_predictions)} records")
            insert_data("predicted_demand_2025", all_category_predictions)
        
        # Insert item-level predictions
        if all_item_predictions:
            print(f"💾 Storing item predictions: {len(all_item_predictions)} records")
            insert_data("predicted_item_demand_2025", all_item_predictions)
        
        print("✅ AI-based demand prediction for 2025 completed successfully!")
        
        return {
            "category_predictions": len(all_category_predictions),
            "item_predictions": len(all_item_predictions)
        }
    
    except Exception as e:
        print(f"❌ Error in AI-based demand prediction: {str(e)}")
        # Log the full traceback for debugging
        import traceback
        traceback.print_exc()
        return {
            "error": str(e)
        }

if __name__ == "__main__":
    predict_demand_2025_ai()
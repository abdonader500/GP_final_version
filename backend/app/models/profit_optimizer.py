import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from app.models.database import fetch_data, get_collection, init_db
import arabic_reshaper
from bidi.algorithm import get_display

# 🔍 **Find Arabic-Compatible Font**
def get_arabic_font():
    """Finds an available Arabic font in the system and returns the FontProperties object."""
    available_fonts = fm.findSystemFonts(fontext="ttf")
    arabic_fonts = ["Arial", "Times New Roman", "Amiri", "Noto Naskh Arabic", "Noto Kufi Arabic", "Geeza Pro"]
    for font_path in available_fonts:
        for arabic_font in arabic_fonts:
            if arabic_font in font_path:
                return fm.FontProperties(fname=font_path)
    print("⚠ Warning: No Arabic font found. Using default font.")
    return None

arabic_font = get_arabic_font()
# **Inflation Adjustment Setup**
# Define inflation rates based on data for Egypt (General Inflation % from year to year)
INFLATION_RATES = {
    2021: 0.138,  # 13.8% from 2021 to 2022
    2022: 0.325,  # 32.5% from 2022 to 2023
    2023: 0.295   # 29.5% from 2023 to 2024 (example; replace with actual rate)
}
BASE_YEAR = 2024  # Base year for price adjustment

# Function to adjust prices for inflation
def adjust_for_inflation(price, year):
    if year == BASE_YEAR:
        return price
    cumulative_factor = 1.0
    for y in range(year, BASE_YEAR):
        cumulative_factor *= (1 + INFLATION_RATES.get(y, 0))
    return price * cumulative_factor

def extract_product_specification(product_name):
    """
    Extract product specification from product name by matching predefined keywords.
    Allows partial matches (e.g., "بلوزة" from "بلوزة123").
    """
    if not isinstance(product_name, str) or not product_name.strip():
        return "غير محدد"
    specifications = {
        "تيشرت", "بنطلون", "حذاء", "قميص", "جاكيت", "بلوزة", "كوتشي", "جزمة", "سوت", "طقم",
        "بوكسر", "سويتان", "سليب", "صندل", "حزام", "بوط", "لكلوك", "اسكتشر", "شنطة", "جيب",
        "شبشب", "بلارينا", "كاجول", "كاجوال", "كروس", "سواريه", "بالطو", "كيلوت", "فستان",
        "بانشو", "شراب", "توينز", "صابوه", "هاي كول", "بدلة", "برنس", "اسدال", "بودي", "بدي",
        "سويت شرت", "عباية", "شورت", "بيجامة", "سالوبت", "فاشون", "سويتر", "سوتيان", "صابو",
        "كارديجان", "بلوفر", "سبور", "توب", "هاف", "بوك", "بنتاكور", "ترينج", "بليزر", "كولون",
        "سويت شيرت", "بوكلت", "هاف كول", "كاب", "جاكت", "فست", "جلابية", "ليجن", "تريكو", "تيشيرت",
        "شروال", "جينز", "طرحة", "تونيك", "شيميز", "شميز", "دريس", "بندانة", "دريل", "شال", "بكيني",
        "كاردن", "بيجاما", "فانلة", "مايوه", "برا", "اندر", "بيجامه", "كمبين", "سويتيان"
    }
    product_name = product_name.strip()
    for spec in specifications:
        if spec in product_name:
            return spec
    return "غير محدد"

def train_profit_models():
    """Train RandomForest model to determine optimal profit percentage per category, specification, and price level."""
    try:
        print("🔍 Initializing database connection...")
        init_db()

        print("🔍 Fetching classified sales data for training...")
        classified_sales = fetch_data("classified_sales", projection={
            "_id": 0, "القسم": 1, "اسم الصنف": 1, "سعر الجملة": 1, "price_level": 1, "نسبة الربح": 1, 
            "الكمية": 1, "التاريخ": 1  # Added date to extract year
        })

        if not classified_sales:
            print(" No classified sales data found! Training aborted.")
            return {}

        # Create DataFrame and clean data
        sales_df = pd.DataFrame(classified_sales)
        sales_df["سعر الجملة"] = pd.to_numeric(sales_df["سعر الجملة"], errors="coerce")
        sales_df["نسبة الربح"] = pd.to_numeric(sales_df["نسبة الربح"], errors="coerce")
        sales_df["الكمية"] = pd.to_numeric(sales_df["الكمية"], errors="coerce")
        sales_df.dropna(subset=["سعر الجملة", "نسبة الربح", "الكمية", "التاريخ"], inplace=True)

        # Extract Year and Adjust for Inflation
        sales_df["Year"] = sales_df["التاريخ"].str.split("/").str[-1].astype(int)  # Assuming "DD/MM/YYYY" format
        sales_df["adjusted_price"] = sales_df.apply(
            lambda row: adjust_for_inflation(row["سعر الجملة"], row["Year"]), axis=1
        )

        # Extract product specification
        sales_df["product_specification"] = sales_df["اسم الصنف"].apply(extract_product_specification)
        undefined_count = (sales_df["product_specification"] == "غير محدد").sum()
        total_count = len(sales_df)
        undefined_percentage = (undefined_count / total_count) * 100
        print(f"🔍 Proportion of 'غير محدد' specifications: {undefined_percentage:.2f}% ({undefined_count}/{total_count} records)")

        print(f"Total training samples available: {sales_df.shape[0]}")

        if sales_df.empty:
            print(" No valid numeric classified sales data found! Training aborted.")
            return {}

        # Compute Sales Rate
        total_sales = sales_df["الكمية"].sum()
        sales_rate_df = sales_df.groupby(["القسم", "product_specification", "price_level"])["الكمية"].sum().reset_index()
        sales_rate_df["sales_rate"] = sales_rate_df["الكمية"] / total_sales

        # Compute mean adjusted price per group for prediction
        mean_adjusted_price = sales_df.groupby(["القسم", "product_specification", "price_level"])["adjusted_price"].mean().reset_index()

        # Encoding categorical variables
        category_encoder = LabelEncoder()
        spec_encoder = LabelEncoder()
        price_level_encoder = LabelEncoder()

        sales_df["category_encoded"] = category_encoder.fit_transform(sales_df["القسم"])
        sales_df["spec_encoded"] = spec_encoder.fit_transform(sales_df["product_specification"])
        sales_df["price_level_encoded"] = price_level_encoder.fit_transform(sales_df["price_level"])

        print(f"Unique categories: {len(category_encoder.classes_)}")
        print(f"Unique specifications: {len(spec_encoder.classes_)}")
        print(f"Unique price levels: {len(price_level_encoder.classes_)}")

        # Feature Engineering with Adjusted Price
        X = sales_df[["category_encoded", "spec_encoded", "price_level_encoded", "adjusted_price"]]
        y = sales_df["نسبة الربح"]

        # Simple train/test split for the model
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        print("Training RandomForest model for profit prediction...")
        model = RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)
        print(" Model training complete")

        # Predict Optimal Profit
        category_predictions = {}
        for category_idx, category in enumerate(category_encoder.classes_):
            category_predictions[category] = {}
            for spec_idx, spec in enumerate(spec_encoder.classes_):
                category_predictions[category][spec] = {"low": None, "moderate": None, "high": None}
                for price_level in ["low", "moderate", "high"]:
                    level_idx = price_level_encoder.transform([price_level])[0]
                    # Get mean adjusted price for this group
                    try:
                        mean_price = mean_adjusted_price[
                            (mean_adjusted_price["القسم"] == category) & 
                            (mean_adjusted_price["product_specification"] == spec) & 
                            (mean_adjusted_price["price_level"] == price_level)
                        ]["adjusted_price"].values[0]
                    except IndexError:
                        mean_price = sales_df["adjusted_price"].mean()
                    
                    input_features = pd.DataFrame(
                        [[category_idx, spec_idx, level_idx, mean_price]],
                        columns=["category_encoded", "spec_encoded", "price_level_encoded", "adjusted_price"]
                    )
                    try:
                        optimal_profit_percentage = model.predict(input_features)[0]
                        sales_rate = sales_rate_df[
                            (sales_rate_df["القسم"] == category) & 
                            (sales_rate_df["product_specification"] == spec) & 
                            (sales_rate_df["price_level"] == price_level)
                        ]["sales_rate"].values[0] if not sales_rate_df.empty else 1
                        adjusted_profit = optimal_profit_percentage * (1 + sales_rate)
                        category_predictions[category][spec][price_level] = round(float(adjusted_profit), 2)
                    except IndexError:
                        continue

        # Store valid models in MongoDB
        models_collection = get_collection("profit_models")
        models_collection.delete_many({})
        valid_mongo_data = [
            {
                "category": category,
                "product_specification": spec,
                "low": levels["low"],
                "moderate": levels["moderate"],
                "high": levels["high"]
            }
            for category, specs in category_predictions.items()
            for spec, levels in specs.items()
            if all(value is not None for value in [levels["low"], levels["moderate"], levels["high"]])
        ]
        models_collection.insert_many(valid_mongo_data)
        print(f" {len(valid_mongo_data)} Profit models stored successfully in MongoDB.")

        # Generate Charts - Simple versions
        plot_feature_importance(model, ["القسم", "المواصفات", "مستوى السعر", "سعر الجملة"])

        return valid_mongo_data

    except Exception as e:
        print(f"Error in train_profit_models: {e}")
        return {}

def plot_feature_importance(model, feature_names):
    """
    Plot feature importance from the trained RandomForest model.
    """
    importances = model.feature_importances_
    sorted_indices = np.argsort(importances)[::-1]
    reshaped_feature_names = [get_display(arabic_reshaper.reshape(name)) for name in feature_names]
    sorted_feature_names = [reshaped_feature_names[i] for i in sorted_indices]
    
    plt.figure(figsize=(10, 6))
    bars = plt.barh(range(len(importances)), importances[sorted_indices], align='center', color='skyblue')
    plt.yticks(range(len(importances)), sorted_feature_names, fontproperties=arabic_font, fontsize=12)
    plt.xlabel(get_display(arabic_reshaper.reshape("الأهمية (Normalized)")), fontproperties=arabic_font, fontsize=12)
    plt.title(get_display(arabic_reshaper.reshape("أهم العوامل المؤثرة على نسبة الربح")), fontproperties=arabic_font, fontsize=14)
    for bar, importance in zip(bars, importances[sorted_indices]):
        plt.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2, f'{importance:.3f}', 
                 ha='left', va='center', fontproperties=arabic_font, fontsize=10)
    plt.grid(True, axis='x', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig("feature_importance.png", dpi=300, bbox_inches='tight')
    plt.close()

def classify_price_level(purchase_price, price_ranges, return_interpolation=False):
    # Extract threshold values, ensuring they're properly ordered
    low_threshold = float(price_ranges.get("low", 0))
    moderate_threshold = float(price_ranges.get("moderate", 0))
    high_threshold = float(price_ranges.get("high", float('inf')))
    
    # Determine the base price level
    if purchase_price <= low_threshold:
        price_level = "low"
    elif purchase_price <= moderate_threshold:
        price_level = "moderate"
    else:
        price_level = "high"
    
    if not return_interpolation:
        return price_level
    
    # Initialize interpolation data
    interpolation_data = {
        "base_level": price_level,
        "adjacent_level": None,
        "interpolation_factor": 0,
        "interpolated_profit": None
    }
    
    # Calculate linear interpolation for prices between thresholds
    if low_threshold < purchase_price <= moderate_threshold:
        # Between low and moderate thresholds
        interpolation_data["base_level"] = "low"
        interpolation_data["adjacent_level"] = "moderate"
        
        # Calculate how far between thresholds (as a percentage)
        range_width = moderate_threshold - low_threshold
        position_in_range = purchase_price - low_threshold
        interpolation_data["interpolation_factor"] = position_in_range / range_width
        
    elif moderate_threshold < purchase_price <= high_threshold:
        # Between moderate and high thresholds
        interpolation_data["base_level"] = "moderate"
        interpolation_data["adjacent_level"] = "high"
        
        # Calculate how far between thresholds (as a percentage)
        range_width = high_threshold - moderate_threshold
        position_in_range = purchase_price - moderate_threshold
        interpolation_data["interpolation_factor"] = position_in_range / range_width
    
    return price_level, interpolation_data

def load_profit_model(category, product_specification, price_level, interpolation_data=None):
    models_collection = get_collection("profit_models")
    model = models_collection.find_one({
        "category": category,
        "product_specification": product_specification
    })
    
    # If no exact match, try with "غير محدد" specification
    if not model:
        model = models_collection.find_one({
            "category": category,
            "product_specification": "غير محدد"
        })
    
    # If still no match, try to find any model for this category
    if not model:
        model = models_collection.find_one({
            "category": category
        })
    
    # If no model found, return default values
    if not model:
        default_profits = {"low": 20.0, "moderate": 35.0, "high": 50.0}
        return default_profits.get(price_level, 30.0)
    
    # If we have interpolation data, apply linear scaling between price levels
    if interpolation_data and interpolation_data["adjacent_level"]:
        base_level = interpolation_data["base_level"]
        adjacent_level = interpolation_data["adjacent_level"]
        
        # Get profit percentages for both levels
        base_profit = float(model.get(base_level, 0.0))
        adjacent_profit = float(model.get(adjacent_level, 0.0))
        
        # If either profit is zero, use defaults
        if base_profit == 0.0 or adjacent_profit == 0.0:
            default_profits = {"low": 20.0, "moderate": 35.0, "high": 50.0}
            base_profit = base_profit or default_profits.get(base_level, 30.0)
            adjacent_profit = adjacent_profit or default_profits.get(adjacent_level, 30.0)
        
        # Calculate the interpolated profit using linear scaling
        factor = interpolation_data["interpolation_factor"]
        
        # Formula: base_profit + (adjacent_profit - base_profit) * factor
        interpolated_profit = base_profit + (adjacent_profit - base_profit) * factor
        
        # Return the linearly scaled profit percentage
        return round(interpolated_profit, 2)
    
    # If no interpolation needed, return the profit for the exact price level
    if price_level in ["low", "moderate", "high"]:
        profit = float(model.get(price_level, 0.0))
        if profit > 0.0:
            return profit
    
    # Fallback to reasonable defaults if no valid profit found
    default_profits = {"low": 20.0, "moderate": 35.0, "high": 50.0}
    return default_profits.get(price_level, 30.0)

if __name__ == "__main__":
    train_profit_models()
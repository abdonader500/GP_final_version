import pandas as pd
from app.models.database import fetch_data, get_collection, init_db

init_db()

def remove_outliers(df, column):
    """
    Remove outliers using the IQR (Interquartile Range) method.
    """
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - (1.2 * IQR)
    upper_bound = Q3 + (1.2 * IQR)
    
    filtered_df = df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]
    
    return filtered_df

def extract_product_specification(product_name):
    """
    Extract product specification from product name by matching predefined keywords.
    Allows partial matches (e.g., "بلوزة" from "بلوزة123").
    """
    if not isinstance(product_name, str) or not product_name.strip():
        return "غير محدد"

    # Convert to set for O(1) lookup
    specifications = {
        "تيشرت", "بنطلون", "حذاء", "قميص", "جاكيت", "بلوزة", "كوتشي", "جزمة", "سوت", "طقم",
        "بوكسر", "سويتان", "سليب", "صندل", "حزام", "بوط", "لكلوك", "اسكتشر", "شنطة", "جيب",
        "شبشب", "بلارينا", "كاجول", "كاجوال", "كروس", "سواريه", "بالطو", "كيلوت", "فستان",
        "بانشو", "شراب", "توينز", "صابوه", "هاي كول", "بدلة", "برنس", "اسدال", "بودي", "بدي",
        "سويت شرت", "عباية", "شورت", "بيجامة", "سالوبت", "فاشون", "سويتر", "سوتيان", "صابو",
        "كارديجان", "بلوفر", "سبور", "توب", "هاف", "بوك", "بنتاكور", "ترينج", "كولون",
        "سويت شيرت", "بوكلت", "هاف كول", "كاب", "جاكت", "فست", "جلابية", "ليجن", "تريكو", "تيشيرت",
        "شروال", "جينز", "طرحة", "تونيك", "شيميز", "شميز", "دريس", "بندانة", "دريل", "شال", "بكيني",
        "كاردن", "بيجاما", "فانلة", "مايوه", "برا", "اندر", "بيجامه", "كمبين", "سويتيان"
    }

    product_name = product_name.strip()
    for spec in specifications:
        if spec in product_name:
            return spec
    return "غير محدد"  # Default if no match is found

def classify_price_levels():
    """Fetch purchase data (2021-2023), remove outliers, classify categories and specifications, and store price ranges in MongoDB."""
    
    print("🔍 Fetching purchase data from 2021-2023...")
    purchases_data = fetch_data("purchases", projection={"_id": 0, "القسم": 1, "سعر الجملة": 1, "التاريخ": 1, "اسم الصنف": 1})

    if not purchases_data:
        print("⚠ No purchase data found for the specified period.")
        return

    df = pd.DataFrame(purchases_data)
    df["سعر الجملة"] = pd.to_numeric(df["سعر الجملة"], errors="coerce")
    df.dropna(subset=["سعر الجملة", "التاريخ"], inplace=True)

    if df.empty:
        print("⚠ No valid purchase data available.")
        return

    df["Year"] = df["التاريخ"].str.split("/").str[-1]
    df["Year"] = df["Year"].astype(str)

    # Extract product specification and count "غير محدد"
    df["product_specification"] = df["اسم الصنف"].apply(extract_product_specification)
    undefined_count = (df["product_specification"] == "غير محدد").sum()
    total_count = len(df)
    undefined_percentage = (undefined_count / total_count) * 100
    print(f"🔍 Proportion of 'غير محدد' specifications in purchases: {undefined_percentage:.2f}% ({undefined_count}/{total_count} records)")

    price_ranges_by_year = {}

    # Classify prices within each category and specification separately per year
    for (category, year, spec), category_data in df.groupby(["القسم", "Year", "product_specification"]):
        print(f"🔍 Processing category: {category}, spec: {spec} for year {year}")

        # Remove outliers before calculating price levels
        category_data = remove_outliers(category_data, "سعر الجملة")

        # Count the number of records in this group
        record_count = len(category_data)

        # Compute tertiles for price level classification (three levels: low, moderate, high)
        if len(category_data) > 0:  # Ensure there are records after outlier removal
            q1 = category_data["سعر الجملة"].quantile(0.33).item()  # Convert to Python scalar
            q2 = category_data["سعر الجملة"].quantile(0.67).item()  # Convert to Python scalar
            max_price = category_data["سعر الجملة"].max().item()    # Convert to Python scalar
            
            price_ranges_by_year.setdefault(category, {}).setdefault(year, {}).setdefault(spec, {}).update({
                "low": q1,
                "moderate": q2,
                "high": max_price
            })

            print(f" {category} ({spec}, {year}): Low < {q1:.2f}, Moderate < {q2:.2f}, High <= {max_price:.2f} [Count: {record_count}]")

    # Store price ranges in MongoDB
    price_ranges_collection = get_collection("price_ranges")
    price_ranges_collection.delete_many({})

    price_ranges_records = [
        {
            "category": category,
            "year": year,
            "product_specification": spec,
            "low": float(thresholds["low"]),  # Ensure native float
            "moderate": float(thresholds["moderate"]),  # Ensure native float
            "high": float(thresholds["high"])  # Ensure native float
        }
        for category, years in price_ranges_by_year.items()
        for year, specs in years.items()
        for spec, thresholds in specs.items()
    ]

    if price_ranges_records:  # Only insert if there are records
        price_ranges_collection.insert_many(price_ranges_records)
        print(f"Price ranges stored in MongoDB with specifications ({len(price_ranges_records)} records).")
    else:
        print("⚠ No price range records to store in MongoDB.")

    classify_sales()

def classify_sales():
    """Fetch sales data and classify them based on stored price ranges per year and specification."""
    
    print("🔍 Fetching sales data for classification...")
    # Include الصافي in the projection since it exists in the sales table
    sales_data = fetch_data("sales", projection={"_id": 0, "القسم": 1, "سعر الجملة": 1, "التاريخ": 1, "اسم الصنف": 1, "نسبة الربح": 1, "الكمية": 1, "الصافي": 1})

    if not sales_data:
        print("⚠ No sales data found.")
        return

    sales_df = pd.DataFrame(sales_data)
    sales_df["سعر الجملة"] = pd.to_numeric(sales_df["سعر الجملة"], errors="coerce")
    sales_df["نسبة الربح"] = pd.to_numeric(sales_df["نسبة الربح"], errors="coerce")
    sales_df["الكمية"] = pd.to_numeric(sales_df["الكمية"], errors="coerce")
    sales_df["الصافي"] = pd.to_numeric(sales_df["الصافي"], errors="coerce")
    sales_df.dropna(subset=["سعر الجملة", "التاريخ", "نسبة الربح", "الكمية", "الصافي"], inplace=True)

    if sales_df.empty:
        print("⚠ No valid sales data available.")
        return

    sales_df["Year"] = sales_df["التاريخ"].str.split("/").str[-1]
    sales_df["Year"] = sales_df["Year"].astype(str)

    # Extract product specification and count "غير محدد"
    sales_df["product_specification"] = sales_df["اسم الصنف"].apply(extract_product_specification)
    undefined_count = (sales_df["product_specification"] == "غير محدد").sum()
    total_count = len(sales_df)
    undefined_percentage = (undefined_count / total_count) * 100
    print(f"🔍 Proportion of 'غير محدد' specifications in sales: {undefined_percentage:.2f}% ({undefined_count}/{total_count} records)")

    # Retrieve stored price ranges from MongoDB
    price_ranges_collection = get_collection("price_ranges")
    price_ranges = list(price_ranges_collection.find({}, {"_id": 0}))

    if not price_ranges:
        print("⚠ No price ranges found in MongoDB. Ensure purchase classification is completed first.")
        return

    # Convert price_ranges into a dictionary for quick lookup
    price_ranges_dict = {
        (record["category"], record["year"], record["product_specification"]): record
        for record in price_ranges
    }

    classified_sales_data = []

    for (category, year, spec), category_data in sales_df.groupby(["القسم", "Year", "product_specification"]):
        print(f"🔍 Processing category: {category}, spec: {spec} for year {year}")

        # Count the number of records in this group
        record_count = len(category_data)

        if (category, year, spec) not in price_ranges_dict:
            print(f"⚠ No price thresholds found for category: {category}, spec: {spec}, year {year}. Skipping classification.")
            continue

        thresholds = price_ranges_dict[(category, year, spec)]

        def categorize_sales_price(price):
            if price < thresholds["low"]:
                return "low"
            elif price < thresholds["moderate"]:
                return "moderate"
            else:
                return "high"

        category_data["price_level"] = category_data["سعر الجملة"].apply(categorize_sales_price)
        # Include all relevant fields in the classified data, including الصافي
        classified_sales_data.extend(category_data[['القسم', 'سعر الجملة', 'التاريخ', 'اسم الصنف', 'product_specification', 'price_level', 'نسبة الربح', 'الكمية', 'الصافي']].to_dict(orient="records"))

        print(f"Classified sales data for {category} ({spec}, {year}) [Count: {record_count}]")

    # Store classified sales data in MongoDB
    sales_classified_collection = get_collection("classified_sales")
    sales_classified_collection.delete_many({})
    if classified_sales_data:  # Only insert if there are records
        sales_classified_collection.insert_many(classified_sales_data)
        print(f"Sales-based price classification completed & stored in MongoDB with specifications ({len(classified_sales_data)} records).")
    else:
        print("No classified sales data to store in MongoDB.")

if __name__ == "__main__":
    classify_price_levels()
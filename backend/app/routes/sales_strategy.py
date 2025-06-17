from flask import Blueprint, request, jsonify, Response
import json
import pandas as pd
import numpy as np
from datetime import datetime
from app.models.database import fetch_data, get_collection, init_db
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import arabic_reshaper
from bidi.algorithm import get_display
import io
import base64

# Create blueprint
sales_strategy_bp = Blueprint('sales_strategy', __name__)

# Helper function to find Arabic-compatible font
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

# Helper function to reshape Arabic text for charts
def prepare_arabic_text(text):
    """Prepare Arabic text for proper display in matplotlib charts."""
    if not text:
        return text
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

@sales_strategy_bp.route('/generate', methods=['POST'])
def generate_sales_strategy():
    try:
        # Initialize database connection
        init_db()
        
        # Get request data
        data = request.get_json()
        category = data.get('category')
        inflation_factor = data.get('inflation_factor', 30)  # Default 30% if not provided
        analysis_notes = data.get('analysis_notes')
        
        if not category:
            return jsonify({"error": "Category is required"}), 400
            
        print(f"Generating sales strategy for category: {category}")
        print(f"Inflation factor: {inflation_factor}%")
        if analysis_notes:
            print(f"Analysis notes: {analysis_notes}")
        
        # Fetch item specification monthly demand data
        print("Fetching item specification monthly demand data...")
        
        query = {
            "القسم": category
        }
        item_data = fetch_data("item_specification_monthly_demand", query=query, projection={"_id": 0})
        
        if not item_data:
            return jsonify({
                "error": f"No data found for category: {category}",
                "message": "لا توجد بيانات كافية لهذا القسم. يرجى اختيار قسم آخر."
            }), 404
            
        # Convert to DataFrame
        df = pd.DataFrame(item_data)
        
        # Process data with enhanced analysis
        strategy_data = process_sales_data(df, category, inflation_factor, analysis_notes)
        
        return jsonify(strategy_data), 200
        
    except Exception as e:
        print(f" Error generating sales strategy: {str(e)}")
        return jsonify({"error": str(e)}), 500

def process_sales_data(df, category, inflation_factor=30, analysis_notes=None):
    """Process sales data to generate comprehensive sales strategy with enhanced analysis."""
    
    # Ensure numeric values
    df["total_quantity"] = pd.to_numeric(df["total_quantity"], errors="coerce")
    df["total_money_sold"] = pd.to_numeric(df["total_money_sold"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["month"] = pd.to_numeric(df["month"], errors="coerce")
    
    # Filter out any invalid data
    df = df.dropna(subset=["total_quantity", "total_money_sold", "year", "month"])
    
    # Define month names
    month_names = [
        'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
        'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
    ]
    
    # Create a mapping from month number to name
    month_name_map = {i+1: name for i, name in enumerate(month_names)}
    
    # 1. Monthly Analysis
    # Aggregate data by month (across all years)
    monthly_agg = df.groupby("month").agg({
        "total_quantity": "sum",
        "total_money_sold": "sum"
    }).reset_index()
    
    # Sort by month
    monthly_agg = monthly_agg.sort_values("month")
    
    # Add month names
    monthly_agg["month_name"] = monthly_agg["month"].map(month_name_map)
    
    # Calculate average unit price
    monthly_agg["avg_price"] = monthly_agg["total_money_sold"] / monthly_agg["total_quantity"]
    monthly_agg["avg_price"] = monthly_agg["avg_price"].fillna(0).round(2)
    
    # 2. Find peak months (top 3 by quantity)
    peak_months = monthly_agg.sort_values("total_quantity", ascending=False).head(3)
    peak_month_names = peak_months["month_name"].tolist()
    
    # 3. Year-over-year performance analysis
    
    # Aggregate by year and calculate growth rate
    yearly_agg = df.groupby("year").agg({
        "total_quantity": "sum",
        "total_money_sold": "sum"
    }).reset_index()
    
    # Add average price per year
    yearly_agg["avg_price"] = yearly_agg["total_money_sold"] / yearly_agg["total_quantity"]
    yearly_agg["avg_price"] = yearly_agg["avg_price"].fillna(0).round(2)
    
    # Calculate growth rates
    yearly_agg["quantity_growth"] = yearly_agg["total_quantity"].pct_change() * 100
    yearly_agg["revenue_growth"] = yearly_agg["total_money_sold"].pct_change() * 100
    yearly_agg["price_growth"] = yearly_agg["avg_price"].pct_change() * 100
    
    # Format yearly performance data for frontend
    yearly_performance = []
    for _, row in yearly_agg.iterrows():
        performance = {
            "year": int(row["year"]),
            "totalQuantity": int(row["total_quantity"]),
            "totalRevenue": int(row["total_money_sold"]),
            "avgPrice": float(row["avg_price"]),
        }
        
        # Add growth rates if available
        if not pd.isna(row["quantity_growth"]):
            performance["quantityGrowth"] = float(round(row["quantity_growth"], 1))
        if not pd.isna(row["revenue_growth"]):
            performance["revenueGrowth"] = float(round(row["revenue_growth"], 1))
        if not pd.isna(row["price_growth"]):
            performance["priceGrowth"] = float(round(row["price_growth"], 1))
            
        yearly_performance.append(performance)
    
    # Sort by year
    yearly_performance = sorted(yearly_performance, key=lambda x: x["year"])
    
    # 4. Detect inflation impact
    # Check if prices are increasing while quantities are decreasing
    inflation_impact = detect_inflation_impact(yearly_performance)
    
    # 5. Seasonal Analysis
    # Define seasons
    winter_months = [12, 1, 2]
    spring_months = [3, 4, 5]
    summer_months = [6, 7, 8]
    fall_months = [9, 10, 11]
    
    # Function to assign season
    def get_season(month):
        if month in winter_months:
            return "الشتاء"
        elif month in spring_months:
            return "الربيع"
        elif month in summer_months:
            return "الصيف"
        else:
            return "الخريف"
    
    # Add season to monthly data
    monthly_agg["season"] = monthly_agg["month"].apply(get_season)
    
    # Aggregate by season
    seasonal_agg = monthly_agg.groupby("season").agg({
        "total_quantity": "sum",
        "total_money_sold": "sum"
    }).reset_index()
    
    # Find strongest and weakest seasons
    strongest_season = seasonal_agg.loc[seasonal_agg["total_quantity"].idxmax(), "season"]
    weakest_season = seasonal_agg.loc[seasonal_agg["total_quantity"].idxmin(), "season"]
    
    # 6. Analyze year-over-year trends by month
    # This is key for seasonal analysis across years
    monthly_yearly_agg = df.groupby(["year", "month"]).agg({
        "total_quantity": "sum",
        "total_money_sold": "sum"
    }).reset_index()
    
    # Add month names and seasons
    monthly_yearly_agg["month_name"] = monthly_yearly_agg["month"].map(month_name_map)
    monthly_yearly_agg["season"] = monthly_yearly_agg["month"].apply(get_season)
    
    # Get the most recent years (up to 3) for trend analysis
    recent_years = sorted(monthly_yearly_agg["year"].unique(), reverse=True)[:3]
    
    # Monthly trends by year
    monthly_trends = {}
    for month in range(1, 13):
        month_data = monthly_yearly_agg[monthly_yearly_agg["month"] == month]
        month_data = month_data[month_data["year"].isin(recent_years)].sort_values("year")
        
        # Skip if less than 2 years of data
        if len(month_data) < 2:
            continue
            
        # Calculate year-over-year growth
        first_year = month_data.iloc[0]["year"]
        last_year = month_data.iloc[-1]["year"]
        first_qty = month_data.iloc[0]["total_quantity"]
        last_qty = month_data.iloc[-1]["total_quantity"]
        
        # Calculate average annual growth rate
        if len(month_data) > 1 and first_qty > 0:
            years_diff = last_year - first_year
            if years_diff > 0:
                compound_growth = ((last_qty / first_qty) ** (1 / years_diff)) - 1
                growth_percent = compound_growth * 100
            else:
                growth_percent = ((last_qty - first_qty) / first_qty) * 100
        else:
            growth_percent = 0
            
        monthly_trends[month_name_map[month]] = {
            "growthRate": round(growth_percent, 1),
            "lastYear": int(last_year),
            "lastQuantity": int(last_qty),
            "trend": "upward" if growth_percent > 5 else "downward" if growth_percent < -5 else "stable"
        }
    
    # 7. Seasonal events analysis
    # Define important seasonal events
    seasonal_events = [
        {
            "name": "رمضان",
            "months": [8, 9, 10],  # Approximate Hijri months in Gregorian calendar
            "description": "شهر رمضان المبارك",
            "strategicImportance": "مرتفعة" if strongest_season in ["الصيف", "الخريف"] else "متوسطة",
            "salesPattern": "ارتفاع" if strongest_season in ["الصيف", "الخريف"] else "معتدل",
        },
        {
            "name": "عيد الفطر",
            "months": [9, 10],
            "description": "عيد الفطر المبارك",
            "strategicImportance": "مرتفعة جداً" if "سبتمبر" in peak_month_names or "أكتوبر" in peak_month_names else "مرتفعة",
            "salesPattern": "ارتفاع حاد" if "سبتمبر" in peak_month_names or "أكتوبر" in peak_month_names else "ارتفاع",
        },
        {
            "name": "عيد الأضحى",
            "months": [11, 12],
            "description": "عيد الأضحى المبارك",
            "strategicImportance": "مرتفعة جداً" if "نوفمبر" in peak_month_names or "ديسمبر" in peak_month_names else "مرتفعة",
            "salesPattern": "ارتفاع حاد" if "نوفمبر" in peak_month_names or "ديسمبر" in peak_month_names else "ارتفاع",
        },
        {
            "name": "العودة للمدارس",
            "months": [8, 9],  # August/September
            "description": "موسم العودة للمدارس",
            "strategicImportance": "مرتفعة جداً" if category.lower() in ["مدارس", "اطفال"] or "سبتمبر" in peak_month_names else "متوسطة",
            "salesPattern": "ارتفاع حاد" if category.lower() in ["مدارس", "اطفال"] or "سبتمبر" in peak_month_names else "معتدل",
        },
        {
            "name": "الصيف",
            "months": [6, 7, 8],  # June, July, August
            "description": "موسم الصيف",
            "strategicImportance": "مرتفعة" if strongest_season == "الصيف" else "متوسطة",
            "salesPattern": "ارتفاع" if strongest_season == "الصيف" else "معتدل",
        },
        {
            "name": "الشتاء",
            "months": [12, 1, 2],  # December, January, February
            "description": "موسم الشتاء",
            "strategicImportance": "مرتفعة" if strongest_season == "الشتاء" else "متوسطة",
            "salesPattern": "ارتفاع" if strongest_season == "الشتاء" else "معتدل",
        }
    ]
    
    # Enrich with strategies for each event
    for event in seasonal_events:
        event["strategies"] = generate_event_strategies(event, category, inflation_impact)
    
    # 8. Product Analysis
    # Aggregate by product specification
    product_agg = df.groupby("product_specification").agg({
        "total_quantity": "sum",
        "total_money_sold": "sum"
    }).reset_index()
    
    # Sort by quantity
    product_agg = product_agg.sort_values("total_quantity", ascending=False)
    
    # Calculate percentage of total
    total_quantity = product_agg["total_quantity"].sum()
    product_agg["percentage"] = (product_agg["total_quantity"] / total_quantity * 100).round(1)
    
    # Get top 5 products
    top_products = product_agg.head(5)
    
    # If there are less than 5 products, add "Other" category to make it 5
    if len(top_products) < 5:
        top_products = top_products
    else:
        # For more than 5, combine the rest into "Other"
        other_quantity = product_agg.iloc[5:]["total_quantity"].sum()
        other_percentage = (other_quantity / total_quantity * 100).round(1)
        
        if other_quantity > 0:
            other_row = pd.DataFrame({
                "product_specification": ["أخرى"],
                "total_quantity": [other_quantity],
                "total_money_sold": [product_agg.iloc[5:]["total_money_sold"].sum()],
                "percentage": [other_percentage]
            })
            top_products = pd.concat([top_products, other_row]).reset_index(drop=True)
    
    # 9. Generate Pricing Recommendations
    pricing_recommendations = generate_pricing_recommendations(
        monthly_agg, seasonal_agg, strongest_season, weakest_season, inflation_impact, inflation_factor
    )
    
    # 10. Generate Marketing Campaign Recommendations
    marketing_campaigns = generate_marketing_campaigns(
        peak_month_names, strongest_season, weakest_season, top_products, 
        seasonal_events, inflation_impact
    )
    
    # 11. Generate Business Recommendations
    business_recommendations = generate_business_recommendations(
        category, strongest_season, weakest_season, yearly_performance,
        inflation_impact, seasonal_events, top_products
    )
    
    # 12. Prepare chart data
    monthly_chart_data = prepare_monthly_chart_data(monthly_agg)
    seasonal_chart_data = prepare_seasonal_chart_data(seasonal_agg)
    
    # 13. Calculate annual totals for next year (2025) with inflation factor
    # For simplicity, use the average of the last 3 years with growth adjustments
    recent_years = sorted(yearly_agg["year"].unique(), reverse=True)[:3]
    recent_data = yearly_agg[yearly_agg["year"].isin(recent_years)]
    
    # Calculate base values from historical data
    avg_annual_quantity_base = recent_data["total_quantity"].mean()
    avg_annual_revenue_base = recent_data["total_money_sold"].mean()
    
    # Apply inflation factor for price adjustment
    inflation_multiplier = 1 + (inflation_factor / 100)
    
    # Estimate quantity impact from price elasticity
    # Assumption: -0.5 price elasticity (10% price increase → 5% quantity decrease)
    elasticity = -0.5
    quantity_multiplier = 1 + (elasticity * (inflation_factor / 100))
    
    # Calculate forecasted values with inflation impact
    avg_annual_quantity = int(avg_annual_quantity_base * quantity_multiplier)
    avg_annual_revenue = int(avg_annual_revenue_base * inflation_multiplier * quantity_multiplier)
    
    # 14. Format the monthly data
    monthly_data = []
    for _, row in monthly_agg.iterrows():
        monthly_data.append({
            "month": row["month_name"],
            "quantity": int(row["total_quantity"]),
            "revenue": int(row["total_money_sold"]),
            "avgPrice": float(row["avg_price"])
        })
    
    # Format the top products data
    top_products_data = []
    for _, row in top_products.iterrows():
        top_products_data.append({
            "name": row["product_specification"],
            "percentage": float(row["percentage"])
        })
    
    # Prepare final response
    response_data = {
        "category": category,
        "monthlyData": monthly_data,
        "peakMonths": peak_month_names,
        "strongestSeason": strongest_season,
        "weakestSeason": weakest_season,
        "yearlyPerformance": yearly_performance,
        "inflationImpact": inflation_impact,
        "seasonStats": {
            "winter": {
                "totalQuantity": int(seasonal_agg[seasonal_agg["season"] == "الشتاء"]["total_quantity"].iloc[0]),
                "totalRevenue": int(seasonal_agg[seasonal_agg["season"] == "الشتاء"]["total_money_sold"].iloc[0])
            },
            "spring": {
                "totalQuantity": int(seasonal_agg[seasonal_agg["season"] == "الربيع"]["total_quantity"].iloc[0]),
                "totalRevenue": int(seasonal_agg[seasonal_agg["season"] == "الربيع"]["total_money_sold"].iloc[0])
            },
            "summer": {
                "totalQuantity": int(seasonal_agg[seasonal_agg["season"] == "الصيف"]["total_quantity"].iloc[0]),
                "totalRevenue": int(seasonal_agg[seasonal_agg["season"] == "الصيف"]["total_money_sold"].iloc[0])
            },
            "fall": {
                "totalQuantity": int(seasonal_agg[seasonal_agg["season"] == "الخريف"]["total_quantity"].iloc[0]),
                "totalRevenue": int(seasonal_agg[seasonal_agg["season"] == "الخريف"]["total_money_sold"].iloc[0])
            }
        },
        "annualQuantity": avg_annual_quantity,
        "annualRevenue": avg_annual_revenue,
        "inflationFactor": inflation_factor,
        "monthlyTrends": monthly_trends,
        "seasonalEvents": seasonal_events,
        "topProducts": top_products_data,
        "pricingRecommendations": pricing_recommendations,
        "marketingCampaigns": marketing_campaigns,
        "businessRecommendations": business_recommendations,
        "analysisNotes": analysis_notes,
        "charts": {
            "monthly": monthly_chart_data,
            "seasonal": seasonal_chart_data,
            "products": top_products["percentage"].tolist()
        }
    }
    
    return response_data

def detect_inflation_impact(yearly_performance):
    """Detect if inflation is impacting sales by comparing price increases with quantity decreases."""
    if len(yearly_performance) < 2:
        return {"detected": False}
    
    # Sort by year to ensure correct order
    sorted_performance = sorted(yearly_performance, key=lambda x: x["year"])
    
    # Check the most recent years
    latest = sorted_performance[-1]
    previous = sorted_performance[-2]
    
    # Check if price increased while quantity decreased
    price_increase = latest.get("priceGrowth", 0) > 5  # More than 5% price increase
    quantity_decrease = latest.get("quantityGrowth", 0) < -2  # More than 2% quantity decrease
    
    if price_increase and quantity_decrease:
        return {
            "detected": True,
            "year": latest["year"],
            "avgPriceIncrease": abs(latest.get("priceGrowth", 0)),
            "quantityDecrease": abs(latest.get("quantityGrowth", 0)),
            "severity": "high" if latest.get("quantityGrowth", 0) < -10 else "medium"
        }
    
    return {"detected": False}

def generate_event_strategies(event, category, inflation_impact):
    """Generate tailored strategies for seasonal events."""
    strategies = []
    
    # Basic strategies by event type
    if event["name"] == "رمضان":
        strategies.append("تقديم عروض خاصة خلال ساعات المساء والليل")
        strategies.append("تصميم حملات تسويقية تناسب أجواء شهر رمضان")
        if category in ["حريمي", "رجالي", "اطفال"]:
            strategies.append("تقديم تشكيلة ملابس خاصة بشهر رمضان والعيد")
    
    elif event["name"] in ["عيد الفطر", "عيد الأضحى"]:
        strategies.append("زيادة المخزون قبل العيد بثلاثة أسابيع على الأقل")
        strategies.append("تقديم خدمات تغليف هدايا مجانية")
        strategies.append("إعداد عروض خاصة للعائلات والمشتريات المتعددة")
    
    elif event["name"] == "العودة للمدارس":
        if category in ["مدارس", "اطفال"]:
            strategies.append("توفير تشكيلة كاملة من ملابس المدارس")
            strategies.append("عروض خاصة للمشتريات بكميات كبيرة")
            strategies.append("الشراكة مع المدارس المحلية لتوفير احتياجاتهم")
        else:
            strategies.append("استهداف العائلات أثناء فترة التسوق للعودة للمدارس")
    
    elif event["name"] == "الصيف":
        if category in ["احذية حريمي", "احذية رجالي", "احذية اطفال"]:
            strategies.append("تقديم تشكيلة متنوعة من الأحذية الصيفية")
        if category in ["حريمي", "رجالي", "اطفال"]:
            strategies.append("التركيز على الملابس الخفيفة والألوان الفاتحة")
    
    elif event["name"] == "الشتاء":
        if category in ["حريمي", "رجالي", "اطفال"]:
            strategies.append("توفير تشكيلة متنوعة من الملابس الشتوية")
            strategies.append("عروض على المعاطف والملابس الثقيلة")
    
    # Add strategies based on importance and sales pattern
    if event["strategicImportance"] == "مرتفعة" or event["strategicImportance"] == "مرتفعة جداً":
        strategies.append("زيادة المخزون قبل الموسم بفترة كافية")
        strategies.append("تخصيص ميزانية تسويقية أعلى للموسم")
    
    if event["salesPattern"] == "ارتفاع حاد":
        strategies.append("تدريب الفريق على التعامل مع فترات الذروة")
        strategies.append("تجهيز خطة بديلة في حالة نفاد المخزون")
    
    # Add inflation-specific strategies if detected
    if inflation_impact and inflation_impact["detected"]:
        strategies.append("تقديم خيارات منتجات بفئات سعرية متنوعة")
        strategies.append("الحفاظ على توازن السعر والجودة لتبرير الأسعار")
    
    return strategies

def generate_pricing_recommendations(monthly_data, seasonal_data, strongest_season, weakest_season, inflation_impact, inflation_factor):
    """Generate pricing recommendations based on seasonal data and inflation impact."""
    
    recommendations = []
    
    # Base recommendation on season strength
    if strongest_season:
        recommendations.append({
            "season": strongest_season,
            "adjustment": "+15%",
            "reason": "طلب مرتفع خلال هذا الموسم"
        })
    
    if weakest_season:
        recommendations.append({
            "season": weakest_season,
            "adjustment": "-10%",
            "reason": "تحفيز المبيعات في فترة الطلب المنخفض"
        })
    
    # Add recommendations for other seasons
    other_seasons = [s for s in ["الشتاء", "الربيع", "الصيف", "الخريف"] 
                     if s not in [strongest_season, weakest_season]]
    
    for season in other_seasons:
        if season == "الصيف":
            recommendations.append({
                "season": season,
                "adjustment": "-5%",
                "reason": "تخفيضات موسمية لتنشيط المبيعات"
            })
        else:
            recommendations.append({
                "season": season,
                "adjustment": "+5%",
                "reason": "طلب متوسط"
            })
    
    # Special case for back-to-school season
    if "الخريف" not in [strongest_season, weakest_season]:
        # Replace the standard fall recommendation
        for i, rec in enumerate(recommendations):
            if rec["season"] == "الخريف":
                recommendations[i] = {
                    "season": "الخريف",
                    "adjustment": "+10%",
                    "reason": "موسم العودة للمدارس"
                }
    
    # Add inflation-based recommendation
    if inflation_impact and inflation_impact["detected"]:
        # Calculate recommended price adjustment based on inflation
        severity = inflation_impact.get("severity", "medium")
        if severity == "high":
            # High impact - suggest more careful price increase
            inflation_adjustment = f"+{round(inflation_factor * 0.7)}%"
        else:
            # Medium impact - suggest moderate price increase
            inflation_adjustment = f"+{round(inflation_factor * 0.8)}%"
            
        recommendations.append({
            "season": "عام - تعديل للتضخم",
            "adjustment": inflation_adjustment,
            "reason": "تعديل لمواجهة التضخم مع الحفاظ على حجم المبيعات"
        })
        
        # Add special promotions recommendation
        recommendations.append({
            "season": "فترات الركود",
            "adjustment": "خصومات استراتيجية",
            "reason": "مواجهة تأثير التضخم على الطلب"
        })
    
    return recommendations

def generate_marketing_campaigns(peak_months, strongest_season, weakest_season, top_products, seasonal_events, inflation_impact):
    """Generate marketing campaign recommendations."""
    
    # Convert season to month mapping
    season_to_month = {
        "الشتاء": "ديسمبر",  # Winter peak month
        "الربيع": "مارس",     # Spring peak month
        "الصيف": "يوليو",     # Summer peak month
        "الخريف": "سبتمبر"    # Fall peak month
    }
    
    # Basic campaigns
    campaigns = [
        {
            "name": f"حملة {strongest_season}",
            "timing": season_to_month.get(strongest_season, peak_months[0] if peak_months else "ديسمبر"),
            "focus": "التركيز على المنتجات الأكثر مبيعًا في الموسم",
            "budget": "مرتفع"
        },
        {
            "name": "حملة منتصف العام",
            "timing": "يونيو",
            "focus": "تخفيضات كبيرة لتحريك المخزون",
            "budget": "متوسط"
        },
        {
            "name": "حملة البلاك فرايداي",
            "timing": "نوفمبر",
            "focus": "عروض محدودة بوقت على المنتجات الأكثر طلبًا",
            "budget": "مرتفع جدًا"
        }
    ]
    
    # Add weakest season campaign
    campaigns.append({
        "name": f"حملة تنشيط {weakest_season}",
        "timing": season_to_month.get(weakest_season, "ديسمبر"),
        "focus": "عروض خاصة لتعزيز المبيعات في الموسم الضعيف",
        "budget": "متوسط"
    })
    
    # Add seasonal event campaigns
    for event in seasonal_events:
        if event["strategicImportance"] == "مرتفعة" or event["strategicImportance"] == "مرتفعة جداً":
            # Only add high-importance events that aren't already covered
            if not any(c["name"].find(event["name"]) >= 0 for c in campaigns):
                event_campaign = {
                    "name": f"حملة {event['name']}",
                    "timing": ", ".join([str(m) for m in event["months"]]),
                    "focus": f"الترويج خلال موسم {event['name']}",
                    "budget": "مرتفع" if event["strategicImportance"] == "مرتفعة جداً" else "متوسط"
                }
                campaigns.append(event_campaign)
    
    # Add product-specific campaign if we have top products
    if len(top_products) > 0:
        top_product_name = top_products.iloc[0]["product_specification"]
        campaigns.append({
            "name": f"حملة ترويج {top_product_name}",
            "timing": peak_months[0] if peak_months else "ديسمبر",
            "focus": f"التركيز على تسويق وترويج {top_product_name}",
            "budget": "متوسط"
        })
    
    # Add inflation-specific campaign if detected
    if inflation_impact and inflation_impact["detected"]:
        inflation_campaign = {
            "name": "حملة القيمة المضافة",
            "timing": "مستمرة",
            "focus": "التركيز على القيمة المضافة للعملاء لتبرير الأسعار في ظل التضخم",
            "budget": "متوسط"
        }
        campaigns.append(inflation_campaign)
    
    return campaigns

def generate_business_recommendations(category, strongest_season, weakest_season, yearly_performance, 
                                     inflation_impact, seasonal_events, top_products):
    """Generate business recommendations based on performance analysis."""
    
    business_recommendations = []
    
    # Check for declining quantity trend
    has_declining_trend = False
    has_increasing_price_trend = False
    
    if len(yearly_performance) >= 2:
        recent_years = sorted(yearly_performance, key=lambda x: x["year"])[-2:]
        latest = recent_years[-1]
        
        if "quantityGrowth" in latest and latest["quantityGrowth"] < 0:
            has_declining_trend = True
        
        if "priceGrowth" in latest and latest["priceGrowth"] > 5:
            has_increasing_price_trend = True
    
    # Recommendations for quantity decline
    if has_declining_trend:
        business_recommendations.append({
            "title": "استراتيجية لمواجهة انخفاض كميات المبيعات",
            "type": "warning",
            "icon": "TrendingDown",
            "recommendations": [
                "تطوير حملات ترويجية لزيادة حجم الطلب",
                "تقديم خصومات على الكميات الكبيرة",
                "إعادة تقييم جودة المنتجات ومقارنتها بالمنافسين",
                "استطلاع آراء العملاء لفهم أسباب انخفاض الطلب",
                "تحسين تجربة العملاء وخدمة ما بعد البيع"
            ]
        })
    
    # Check for inflation impact
    if inflation_impact and inflation_impact["detected"]:
        business_recommendations.append({
            "title": "استراتيجية لمواجهة تأثير التضخم",
            "type": "alert",
            "icon": "CompareArrows",
            "recommendations": [
                "تطوير خيارات منتجات بأسعار متنوعة لمختلف فئات العملاء",
                "تقديم قيمة إضافية للعملاء لتبرير الزيادة في الأسعار",
                "تحسين كفاءة سلسلة التوريد لتقليل التكاليف",
                "عروض ترويجية استراتيجية للمحافظة على الكميات",
                "تطوير برامج ولاء لتشجيع العملاء على الشراء المتكرر"
            ]
        })
    
    # Recommendations for peak seasons
    if strongest_season:
        business_recommendations.append({
            "title": f"استراتيجية لموسم {strongest_season}",
            "type": "success",
            "icon": "Timeline",
            "recommendations": [
                "زيادة مستويات المخزون قبل الموسم بفترة كافية",
                "تطوير حملات تسويقية مخصصة للموسم",
                "تدريب فريق المبيعات على التعامل مع الضغط المتزايد",
                "تجهيز العروض الترويجية المناسبة لهذا الموسم",
                "تخصيص مساحة عرض أكبر للمنتجات الأكثر مبيعاً"
            ]
        })
    
    # Recommendations for weak seasons
    if weakest_season:
        business_recommendations.append({
            "title": f"استراتيجية لموسم {weakest_season}",
            "type": "info",
            "icon": "Analytics",
            "recommendations": [
                "تطوير عروض وخصومات لتحفيز الطلب",
                "تنويع التشكيلات المعروضة لجذب اهتمام العملاء",
                "تخفيض مستويات المخزون وتجنب التكدس",
                "الاستفادة من هذه الفترة للتخطيط الاستراتيجي",
                "تطوير منتجات جديدة استعداداً للمواسم القادمة"
            ]
        })
    
    # Special recommendations for specific categories
    if "مدارس" in category.lower() or "اطفال" in category.lower():
        school_season_found = False
        for event in seasonal_events:
            if event["name"] == "العودة للمدارس":
                school_season_found = True
                break
        
        if school_season_found:
            business_recommendations.append({
                "title": "استراتيجية خاصة لموسم العودة للمدارس",
                "type": "primary",
                "icon": "EventNote",
                "recommendations": [
                    "البدء بالإعداد والتسويق قبل بداية العام الدراسي بشهرين",
                    "تقديم عروض للمشتريات الجماعية للمدارس والعائلات",
                    "توفير خدمات إضافية مثل التوصيل للمدارس أو الطباعة المجانية للأسماء",
                    "تطوير مجموعات متكاملة من مستلزمات المدارس",
                    "إقامة شراكات مع المدارس المحلية للحصول على حصة أكبر من السوق"
                ]
            })
    
    # Add general recommendations based on top products
    if top_products is not None and len(top_products) > 0:
        business_recommendations.append({
            "title": "استراتيجية تطوير المنتجات الرئيسية",
            "type": "secondary",
            "icon": "Inventory",
            "recommendations": [
                f"التركيز على تشكيلة واسعة من {top_products.iloc[0]['product_specification']}",
                "تطوير عروض خاصة للمنتجات الأكثر مبيعاً",
                "قياس رضا العملاء عن المنتجات الرئيسية بشكل مستمر",
                "البحث عن منتجات متكاملة للبيع المتقاطع",
                "الاستثمار في تحسين جودة المنتجات الأكثر مبيعاً"
            ]
        })
    
    # If we have both declining trend and inflation impact, add a combination strategy
    if has_declining_trend and inflation_impact and inflation_impact["detected"]:
        business_recommendations.append({
            "title": "استراتيجية متكاملة لمواجهة التضخم وانخفاض المبيعات",
            "type": "critical",
            "icon": "TrendingUp",
            "recommendations": [
                "إعادة هيكلة تشكيلة المنتجات لتقديم خيارات متعددة الأسعار",
                "تركيز الاستثمار في المنتجات ذات هامش الربح الأعلى",
                "تبسيط سلسلة التوريد لتقليل التكاليف التشغيلية",
                "تطوير استراتيجية تواصل لشرح القيمة المضافة للعملاء",
                "اعتماد نظام مراقبة دقيق لسلوك المستهلك واتجاهات السوق"
            ]
        })
    
    return business_recommendations

def prepare_monthly_chart_data(monthly_data):
    """Prepare monthly data for charts."""
    # This would typically generate actual chart images or chart data
    # For this implementation, we'll just return the processed data for the frontend to render
    
    return {
        "labels": monthly_data["month_name"].tolist(),
        "quantity": monthly_data["total_quantity"].tolist(),
        "revenue": monthly_data["total_money_sold"].tolist()
    }

def prepare_seasonal_chart_data(seasonal_data):
    """Prepare seasonal data for charts."""
    # Similar to monthly chart data, prepare the seasonal data
    
    return {
        "labels": seasonal_data["season"].tolist(),
        "quantity": seasonal_data["total_quantity"].tolist(),
        "revenue": seasonal_data["total_money_sold"].tolist()
    }

@sales_strategy_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get available categories from the database."""
    try:
        init_db()
        
        # Get distinct categories from item_specification_monthly_demand
        collection = get_collection("item_specification_monthly_demand")
        categories = collection.distinct("القسم")
        
        return jsonify(categories), 200
        
    except Exception as e:
        print(f" Error getting categories: {str(e)}")
        return jsonify({"error": str(e)}), 500

@sales_strategy_bp.route('/products-by-category/<category>', methods=['GET'])
def get_products_by_category(category):
    """Get product specifications for a given category."""
    try:
        init_db()
        
        if not category:
            return jsonify({"error": "Category is required"}), 400
        
        # Get distinct product specifications for the category
        collection = get_collection("item_specification_monthly_demand")
        products = collection.distinct("product_specification", {"القسم": category})
        
        return jsonify(products), 200
        
    except Exception as e:
        print(f" Error getting products for category {category}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@sales_strategy_bp.route('/compare-years/<category>', methods=['GET'])
def compare_years(category):
    """Compare yearly performance for a specific category."""
    try:
        init_db()
        
        if not category:
            return jsonify({"error": "Category is required"}), 400
        
        # Fetch data for the category
        collection = get_collection("item_specification_monthly_demand")
        data = list(collection.find({"القسم": category}, {"_id": 0}))
        
        if not data:
            return jsonify({"error": f"No data found for category: {category}"}), 404
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Ensure numeric values
        df["total_quantity"] = pd.to_numeric(df["total_quantity"], errors="coerce")
        df["total_money_sold"] = pd.to_numeric(df["total_money_sold"], errors="coerce")
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["month"] = pd.to_numeric(df["month"], errors="coerce")
        
        # Group by year
        yearly_agg = df.groupby("year").agg({
            "total_quantity": "sum",
            "total_money_sold": "sum"
        }).reset_index()
        
        # Calculate average price
        yearly_agg["avg_price"] = yearly_agg["total_money_sold"] / yearly_agg["total_quantity"]
        yearly_agg["avg_price"] = yearly_agg["avg_price"].fillna(0).round(2)
        
        # Calculate growth rates
        yearly_agg["quantity_growth"] = yearly_agg["total_quantity"].pct_change() * 100
        yearly_agg["revenue_growth"] = yearly_agg["total_money_sold"].pct_change() * 100
        yearly_agg["price_growth"] = yearly_agg["avg_price"].pct_change() * 100
        
        # Format for response
        yearly_comparison = []
        for _, row in yearly_agg.iterrows():
            comparison = {
                "year": int(row["year"]),
                "totalQuantity": int(row["total_quantity"]),
                "totalRevenue": int(row["total_money_sold"]),
                "avgPrice": float(row["avg_price"]),
            }
            
            # Add growth rates if available
            if not pd.isna(row["quantity_growth"]):
                comparison["quantityGrowth"] = float(round(row["quantity_growth"], 1))
            if not pd.isna(row["revenue_growth"]):
                comparison["revenueGrowth"] = float(round(row["revenue_growth"], 1))
            if not pd.isna(row["price_growth"]):
                comparison["priceGrowth"] = float(round(row["price_growth"], 1))
                
            yearly_comparison.append(comparison)
        
        # Sort by year
        yearly_comparison = sorted(yearly_comparison, key=lambda x: x["year"])
        
        # Detect inflation impact
        inflation_impact = detect_inflation_impact(yearly_comparison)
        
        return jsonify({
            "category": category,
            "yearlyComparison": yearly_comparison,
            "inflationImpact": inflation_impact
        }), 200
        
    except Exception as e:
        print(f" Error comparing years for category {category}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@sales_strategy_bp.route('/seasonal-events/<category>', methods=['GET'])
def get_seasonal_events(category):
    """Get seasonal events impact for a specific category."""
    try:
        init_db()
        
        if not category:
            return jsonify({"error": "Category is required"}), 400
        
        # Fetch data for the category
        collection = get_collection("item_specification_monthly_demand")
        data = list(collection.find({"القسم": category}, {"_id": 0}))
        
        if not data:
            return jsonify({"error": f"No data found for category: {category}"}), 404
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Ensure numeric values
        df["total_quantity"] = pd.to_numeric(df["total_quantity"], errors="coerce")
        df["total_money_sold"] = pd.to_numeric(df["total_money_sold"], errors="coerce")
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["month"] = pd.to_numeric(df["month"], errors="coerce")
        
        # Define month names
        month_names = [
            'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
            'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
        ]
        
        # Create month name mapping
        month_name_map = {i+1: name for i, name in enumerate(month_names)}
        
        # Monthly analysis
        monthly_agg = df.groupby("month").agg({
            "total_quantity": "sum",
            "total_money_sold": "sum"
        }).reset_index()
        
        # Add month names
        monthly_agg["month_name"] = monthly_agg["month"].map(month_name_map)
        
        # Find peak months
        peak_months = monthly_agg.sort_values("total_quantity", ascending=False).head(3)
        peak_month_names = peak_months["month_name"].tolist()
        
        # Define seasons
        winter_months = [12, 1, 2]
        spring_months = [3, 4, 5]
        summer_months = [6, 7, 8]
        fall_months = [9, 10, 11]
        
        # Function to assign season
        def get_season(month):
            if month in winter_months:
                return "الشتاء"
            elif month in spring_months:
                return "الربيع"
            elif month in summer_months:
                return "الصيف"
            else:
                return "الخريف"
        
        # Add seasons to monthly data
        monthly_agg["season"] = monthly_agg["month"].apply(get_season)
        
        # Aggregate by season
        seasonal_agg = monthly_agg.groupby("season").agg({
            "total_quantity": "sum",
            "total_money_sold": "sum"
        }).reset_index()
        
        # Find strongest and weakest seasons
        strongest_season = seasonal_agg.loc[seasonal_agg["total_quantity"].idxmax(), "season"]
        weakest_season = seasonal_agg.loc[seasonal_agg["total_quantity"].idxmin(), "season"]
        
        # Define seasonal events
        seasonal_events = [
            {
                "name": "رمضان",
                "months": [8, 9, 10],  # Approximate Hijri months in Gregorian calendar
                "description": "شهر رمضان المبارك",
                "strategicImportance": "مرتفعة" if strongest_season in ["الصيف", "الخريف"] else "متوسطة",
                "salesPattern": "ارتفاع" if strongest_season in ["الصيف", "الخريف"] else "معتدل",
            },
            {
                "name": "عيد الفطر",
                "months": [9, 10],
                "description": "عيد الفطر المبارك",
                "strategicImportance": "مرتفعة جداً" if "سبتمبر" in peak_month_names or "أكتوبر" in peak_month_names else "مرتفعة",
                "salesPattern": "ارتفاع حاد" if "سبتمبر" in peak_month_names or "أكتوبر" in peak_month_names else "ارتفاع",
            },
            {
                "name": "عيد الأضحى",
                "months": [11, 12],
                "description": "عيد الأضحى المبارك",
                "strategicImportance": "مرتفعة جداً" if "نوفمبر" in peak_month_names or "ديسمبر" in peak_month_names else "مرتفعة",
                "salesPattern": "ارتفاع حاد" if "نوفمبر" in peak_month_names or "ديسمبر" in peak_month_names else "ارتفاع",
            },
            {
                "name": "العودة للمدارس",
                "months": [8, 9],  # August/September
                "description": "موسم العودة للمدارس",
                "strategicImportance": "مرتفعة جداً" if category.lower() in ["مدارس", "اطفال"] or "سبتمبر" in peak_month_names else "متوسطة",
                "salesPattern": "ارتفاع حاد" if category.lower() in ["مدارس", "اطفال"] or "سبتمبر" in peak_month_names else "معتدل",
            },
            {
                "name": "الصيف",
                "months": [6, 7, 8],  # June, July, August
                "description": "موسم الصيف",
                "strategicImportance": "مرتفعة" if strongest_season == "الصيف" else "متوسطة",
                "salesPattern": "ارتفاع" if strongest_season == "الصيف" else "معتدل",
            },
            {
                "name": "الشتاء",
                "months": [12, 1, 2],  # December, January, February
                "description": "موسم الشتاء",
                "strategicImportance": "مرتفعة" if strongest_season == "الشتاء" else "متوسطة",
                "salesPattern": "ارتفاع" if strongest_season == "الشتاء" else "معتدل",
            }
        ]
        
        # Check for year-over-year data to detect inflation impact
        yearly_agg = df.groupby("year").agg({
            "total_quantity": "sum",
            "total_money_sold": "sum"
        }).reset_index()
        
        yearly_agg["avg_price"] = yearly_agg["total_money_sold"] / yearly_agg["total_quantity"]
        yearly_agg = yearly_agg.dropna().reset_index(drop=True)
        
        yearly_performance = []
        for _, row in yearly_agg.iterrows():
            performance = {
                "year": int(row["year"]),
                "totalQuantity": int(row["total_quantity"]),
                "totalRevenue": int(row["total_money_sold"]),
                "avgPrice": float(row["avg_price"]),
            }
            yearly_performance.append(performance)
        
        # Detect inflation impact
        inflation_impact = detect_inflation_impact(yearly_performance)
        
        # Generate strategies for each event
        for event in seasonal_events:
            event["strategies"] = generate_event_strategies(event, category, inflation_impact)
        
        return jsonify({
            "category": category,
            "peakMonths": peak_month_names,
            "strongestSeason": strongest_season,
            "weakestSeason": weakest_season,
            "seasonalEvents": seasonal_events,
            "inflationImpact": inflation_impact
        }), 200
        
    except Exception as e:
        print(f" Error getting seasonal events for category {category}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@sales_strategy_bp.route('/monthly-trends/<category>', methods=['GET'])
def get_monthly_trends(category):
    """Get monthly trends across years for a specific category."""
    try:
        init_db()
        
        if not category:
            return jsonify({"error": "Category is required"}), 400
        
        # Fetch data for the category
        collection = get_collection("item_specification_monthly_demand")
        data = list(collection.find({"القسم": category}, {"_id": 0}))
        
        if not data:
            return jsonify({"error": f"No data found for category: {category}"}), 404
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Ensure numeric values
        df["total_quantity"] = pd.to_numeric(df["total_quantity"], errors="coerce")
        df["total_money_sold"] = pd.to_numeric(df["total_money_sold"], errors="coerce")
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["month"] = pd.to_numeric(df["month"], errors="coerce")
        
        # Define month names
        month_names = [
            'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
            'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
        ]
        
        # Create month name mapping
        month_name_map = {i+1: name for i, name in enumerate(month_names)}
        
        # Group by year and month
        monthly_yearly_agg = df.groupby(["year", "month"]).agg({
            "total_quantity": "sum",
            "total_money_sold": "sum"
        }).reset_index()
        
        # Add month names
        monthly_yearly_agg["month_name"] = monthly_yearly_agg["month"].map(month_name_map)
        
        # Get the most recent years (up to 3) for trend analysis
        recent_years = sorted(monthly_yearly_agg["year"].unique(), reverse=True)[:3]
        
        # Monthly trends by year
        monthly_trends = {}
        monthly_data_by_year = {}
        
        for month in range(1, 13):
            month_data = monthly_yearly_agg[monthly_yearly_agg["month"] == month]
            month_data_by_year = {}
            
            for year in sorted(month_data["year"].unique()):
                year_data = month_data[month_data["year"] == year]
                if not year_data.empty:
                    month_data_by_year[int(year)] = {
                        "quantity": int(year_data["total_quantity"].iloc[0]),
                        "revenue": int(year_data["total_money_sold"].iloc[0])
                    }
            
            monthly_data_by_year[month_name_map[month]] = month_data_by_year
            
            # Calculate trends for recent years
            recent_month_data = month_data[month_data["year"].isin(recent_years)].sort_values("year")
            
            # Skip if less than 2 years of data
            if len(recent_month_data) < 2:
                continue
                
            # Calculate year-over-year growth
            first_year = recent_month_data.iloc[0]["year"]
            last_year = recent_month_data.iloc[-1]["year"]
            first_qty = recent_month_data.iloc[0]["total_quantity"]
            last_qty = recent_month_data.iloc[-1]["total_quantity"]
            
            # Calculate average annual growth rate
            if len(recent_month_data) > 1 and first_qty > 0:
                years_diff = last_year - first_year
                if years_diff > 0:
                    compound_growth = ((last_qty / first_qty) ** (1 / years_diff)) - 1
                    growth_percent = compound_growth * 100
                else:
                    growth_percent = ((last_qty - first_qty) / first_qty) * 100
            else:
                growth_percent = 0
                
            monthly_trends[month_name_map[month]] = {
                "growthRate": round(growth_percent, 1),
                "lastYear": int(last_year),
                "lastQuantity": int(last_qty),
                "trend": "upward" if growth_percent > 5 else "downward" if growth_percent < -5 else "stable"
            }
        
        return {
            "category": category,
            "monthlyTrends": monthly_trends,
            "monthlyDataByYear": monthly_data_by_year
        }
        
    except Exception as e:
        print(f" Error getting monthly trends for category {category}: {str(e)}")
        raise

@sales_strategy_bp.route('/seasonal-recommendations/<category>', methods=['GET'])
def get_seasonal_recommendations(category):
    """Get detailed seasonal recommendations for a specific category."""
    try:
        init_db()
        
        if not category:
            return jsonify({"error": "Category is required"}), 400
            
        # Analyze seasonal patterns and events
        seasonal_events_data = get_seasonal_events(category)
        
        # Get monthly trends
        monthly_trends_data = get_monthly_trends(category)
        
        # Analyze year-over-year performance
        yearly_comparison_data = compare_years(category)
        
        # Combine all analyses for comprehensive recommendations
        recommendations = {
            "category": category,
            "seasonalEvents": seasonal_events_data.get("seasonalEvents", []),
            "peakMonths": seasonal_events_data.get("peakMonths", []),
            "strongestSeason": seasonal_events_data.get("strongestSeason", ""),
            "weakestSeason": seasonal_events_data.get("weakestSeason", ""),
            "monthlyTrends": monthly_trends_data.get("monthlyTrends", {}),
            "yearlyComparison": yearly_comparison_data.get("yearlyComparison", []),
            "inflationImpact": yearly_comparison_data.get("inflationImpact", {"detected": False}),
            "marketingStrategies": generate_marketing_strategies(
                category, 
                seasonal_events_data,
                monthly_trends_data,
                yearly_comparison_data
            ),
            "pricingStrategies": generate_pricing_strategies(
                category,
                seasonal_events_data,
                yearly_comparison_data
            ),
            "inventoryStrategies": generate_inventory_strategies(
                category,
                seasonal_events_data,
                monthly_trends_data
            )
        }
        
        return jsonify(recommendations), 200
        
    except Exception as e:
        print(f" Error generating seasonal recommendations for {category}: {str(e)}")
        return jsonify({"error": str(e)}), 500

def generate_marketing_strategies(category, seasonal_data, monthly_data, yearly_data):
    """Generate detailed marketing strategies based on all analyses."""
    strategies = []
    
    # Extract key data points
    strong_season = seasonal_data.get("strongestSeason", "")
    weak_season = seasonal_data.get("weakestSeason", "")
    peak_months = seasonal_data.get("peakMonths", [])
    seasonal_events = seasonal_data.get("seasonalEvents", [])
    inflation_impact = yearly_data.get("inflationImpact", {"detected": False})
    monthly_trends = monthly_data.get("monthlyTrends", {})
    
    # Base marketing strategies for strong seasons and peak months
    if strong_season:
        strategies.append({
            "type": "seasonal",
            "title": f"استراتيجية تسويق موسم {strong_season}",
            "description": f"تكثيف الحملات التسويقية خلال موسم {strong_season} للاستفادة من ارتفاع الطلب",
            "tactics": [
                "زيادة الميزانية الإعلانية بنسبة 25-30% خلال هذا الموسم",
                "التركيز على عرض المنتجات الأكثر طلباً في واجهة العرض",
                "إطلاق حملات على وسائل التواصل الاجتماعي قبل الموسم بأسبوعين",
                "تنظيم فعاليات ترويجية خاصة خلال فترة الذروة"
            ]
        })
    
    # Marketing strategies for weak seasons to boost sales
    if weak_season:
        strategies.append({
            "type": "seasonal",
            "title": f"استراتيجية تحفيز المبيعات في موسم {weak_season}",
            "description": f"تنشيط المبيعات خلال موسم {weak_season} الذي يشهد انخفاضاً في الطلب",
            "tactics": [
                "تقديم عروض ترويجية حصرية خلال هذا الموسم",
                "إطلاق منتجات جديدة أو حصرية لجذب اهتمام العملاء",
                "التركيز على حملات الولاء واستهداف العملاء الحاليين",
                "الترويج للقيمة المضافة للمنتجات بدلاً من التركيز على السعر فقط"
            ]
        })
    
    # Add inflation-specific strategies if detected
    if inflation_impact and inflation_impact.get("detected", False):
        strategies.append({
            "type": "economic",
            "title": "استراتيجية التسويق في ظل التضخم",
            "description": "تعديل الاستراتيجية التسويقية لمواجهة تأثير التضخم على سلوك المستهلك",
            "tactics": [
                "التركيز على إبراز القيمة المضافة للمنتجات لتبرير الأسعار",
                "تطوير حملات تروج لجودة المنتجات وعمرها الافتراضي",
                "تقديم خيارات دفع مرنة أو خطط تقسيط لتسهيل الشراء",
                "إطلاق منتجات بفئات سعرية مختلفة لتناسب مختلف القدرات الشرائية",
                "تطوير برامج ولاء تقدم مزايا غير سعرية للعملاء"
            ]
        })
    
    # Add strategies for specific events
    for event in seasonal_events:
        if event.get("strategicImportance") in ["مرتفعة", "مرتفعة جداً"]:
            event_name = event.get("name", "")
            
            # Skip if already covered in seasonal strategies
            if (event_name == "الصيف" and strong_season == "الصيف") or \
               (event_name == "الشتاء" and strong_season == "الشتاء"):
                continue
                
            event_strategies = []
            
            if event_name == "رمضان":
                event_strategies = [
                    "تصميم حملات إعلانية تعكس روح شهر رمضان",
                    "تكثيف الإعلانات خلال فترات المساء بعد الإفطار",
                    "تقديم عروض خاصة تناسب احتياجات التسوق الرمضانية",
                    "إطلاق حملات تسويق تفاعلية على منصات التواصل الاجتماعي"
                ]
            elif event_name in ["عيد الفطر", "عيد الأضحى"]:
                event_strategies = [
                    "إطلاق حملة ترويجية قبل العيد بثلاثة أسابيع",
                    "تصميم عروض هدايا مميزة مع تغليف خاص للعيد",
                    "تنفيذ استراتيجية تسويق متكاملة عبر القنوات المختلفة",
                    "تقديم خصومات تصاعدية مع زيادة قيمة المشتريات"
                ]
            elif event_name == "العودة للمدارس":
                event_strategies = [
                    "إطلاق حملة 'العودة للمدرسة' قبل بداية العام الدراسي بشهر",
                    "تقديم عروض خاصة للمشتريات العائلية أو للمدارس",
                    "تطوير حملات تسويقية تستهدف الأهالي والطلاب",
                    "الترويج لمنتجات متكاملة كحزم متكاملة بسعر مميز"
                ]
            
            if event_strategies:
                strategies.append({
                    "type": "event",
                    "title": f"استراتيجية تسويق {event_name}",
                    "description": f"تحقيق أقصى استفادة من موسم {event_name}",
                    "tactics": event_strategies
                })
    
    # Add strategies for months with declining sales trends
    declining_months = [month for month, data in monthly_trends.items() if data.get("trend") == "downward"]
    if declining_months:
        months_str = " و".join(declining_months)
        strategies.append({
            "type": "recovery",
            "title": f"استراتيجية تحسين أداء المبيعات في شهور {months_str}",
            "description": "معالجة انخفاض الأداء في الشهور التي تظهر اتجاهاً هبوطياً",
            "tactics": [
                "تحليل أسباب انخفاض المبيعات في هذه الشهور",
                "تقديم عروض ترويجية مخصصة خلال هذه الفترات",
                "تكثيف التواصل مع العملاء من خلال حملات عبر البريد الإلكتروني والرسائل",
                "تطوير أنشطة تسويقية مبتكرة لجذب العملاء خلال هذه الفترات"
            ]
        })
    
    return strategies

def generate_pricing_strategies(category, seasonal_data, yearly_data):
    """Generate pricing strategies based on seasonal patterns and economic indicators."""
    strategies = []
    
    # Extract key data
    strong_season = seasonal_data.get("strongestSeason", "")
    weak_season = seasonal_data.get("weakestSeason", "")
    seasonal_events = seasonal_data.get("seasonalEvents", [])
    inflation_impact = yearly_data.get("inflationImpact", {"detected": False})
    yearly_comparison = yearly_data.get("yearlyComparison", [])
    
    # General seasonal pricing strategy
    strategies.append({
        "type": "seasonal",
        "title": "استراتيجية التسعير الموسمية",
        "description": "تعديل الأسعار وفقاً للطلب الموسمي لتحقيق أقصى ربحية",
        "tactics": [
            f"زيادة الأسعار بنسبة 10-15% خلال موسم {strong_season}" if strong_season else "زيادة الأسعار خلال مواسم الطلب المرتفع",
            f"تخفيض الأسعار بنسبة 5-10% خلال موسم {weak_season} لتحفيز الطلب" if weak_season else "تقديم خصومات في مواسم الطلب المنخفض",
            "تطبيق استراتيجية التسعير الديناميكي وفقاً لتغيرات الطلب",
            "الحفاظ على استقرار الأسعار خلال الفترات الانتقالية بين المواسم"
        ]
    })
    
    # Pricing strategies for special events
    event_pricing_tactics = []
    for event in seasonal_events:
        if event.get("strategicImportance") in ["مرتفعة", "مرتفعة جداً"]:
            event_name = event.get("name", "")
            
            if event_name in ["عيد الفطر", "عيد الأضحى"]:
                tactic = f"تطبيق أسعار خاصة لمنتجات {event_name} مع التركيز على جودة المنتج"
                event_pricing_tactics.append(tactic)
            elif event_name == "العودة للمدارس":
                tactic = "تقديم خصومات تصاعدية على مشتريات العودة للمدارس كلما زادت الكمية"
                event_pricing_tactics.append(tactic)
            elif event_name == "رمضان":
                tactic = "تطوير باقات منتجات بأسعار خاصة خلال شهر رمضان"
                event_pricing_tactics.append(tactic)
    
    if event_pricing_tactics:
        strategies.append({
            "type": "event",
            "title": "استراتيجية تسعير المناسبات الخاصة",
            "description": "تعديل الأسعار خلال المناسبات الخاصة لتحقيق التوازن بين المبيعات والربحية",
            "tactics": event_pricing_tactics
        })
    
    # Inflation-based pricing strategy
    if inflation_impact and inflation_impact.get("detected", False):
        avg_price_increase = inflation_impact.get("avgPriceIncrease", 0)
        quantity_decrease = inflation_impact.get("quantityDecrease", 0)
        
        inflation_tactics = [
            "زيادة الأسعار تدريجياً بدلاً من زيادات كبيرة مفاجئة",
            "تطوير منتجات بفئات سعرية متنوعة لتلبية احتياجات مختلف العملاء",
            "تقديم خصومات استراتيجية على منتجات مختارة لزيادة حجم المبيعات"
        ]
        
        # Add specific tactics based on severity
        if quantity_decrease > 15:  # High impact
            inflation_tactics.append("تخفيض هامش الربح على بعض المنتجات للحفاظ على حجم المبيعات")
            inflation_tactics.append("إعادة تقييم هيكل التكاليف للبحث عن فرص لخفض التكاليف")
        
        strategies.append({
            "type": "economic",
            "title": "استراتيجية التسعير في ظل التضخم",
            "description": "تعديل استراتيجية التسعير لمواجهة التضخم مع الحفاظ على حجم المبيعات",
            "tactics": inflation_tactics
        })
    
    # Value-based pricing strategy
    strategies.append({
        "type": "value",
        "title": "استراتيجية التسعير على أساس القيمة",
        "description": "تسعير المنتجات على أساس القيمة المقدمة للعملاء وليس فقط التكلفة",
        "tactics": [
            "إبراز مزايا وفوائد المنتجات لتبرير أسعارها",
            "تقديم ضمانات وخدمات إضافية لتعزيز القيمة المدركة",
            "تصنيف المنتجات وفقاً لمستويات جودة مختلفة مع تسعير مناسب لكل مستوى",
            "إجراء استطلاعات دورية لقياس مدى تقبل العملاء للأسعار"
        ]
    })
    
    return strategies

def generate_inventory_strategies(category, seasonal_data, monthly_data):
    """Generate inventory management strategies based on seasonal patterns."""
    strategies = []
    
    # Extract key data
    strong_season = seasonal_data.get("strongestSeason", "")
    weak_season = seasonal_data.get("weakestSeason", "")
    peak_months = seasonal_data.get("peakMonths", [])
    seasonal_events = seasonal_data.get("seasonalEvents", [])
    monthly_trends = monthly_data.get("monthlyTrends", {})
    
    # Base inventory strategy by season
    if strong_season:
        strategies.append({
            "type": "seasonal",
            "title": f"إدارة المخزون لموسم {strong_season}",
            "description": f"تحسين مستويات المخزون استعداداً لموسم {strong_season} الذي يشهد ارتفاعاً في الطلب",
            "tactics": [
                f"زيادة مستويات المخزون قبل بداية موسم {strong_season} بشهر على الأقل",
                "توسيع تشكيلة المنتجات المعروضة خلال هذا الموسم",
                "تأمين خط إمداد مرن ومستمر خلال فترة الذروة",
                "تعزيز نظام تتبع المخزون لتفادي نفاد المنتجات الأكثر طلباً"
            ]
        })
    
    if weak_season:
        strategies.append({
            "type": "seasonal",
            "title": f"إدارة المخزون لموسم {weak_season}",
            "description": f"تحسين كفاءة المخزون خلال موسم {weak_season} لتقليل التكاليف وتجنب التكدس",
            "tactics": [
                f"تخفيض مستويات المخزون خلال موسم {weak_season} لتجنب التكدس",
                "التركيز على المنتجات الأساسية والأكثر مبيعاً",
                "جدولة عمليات الجرد وإعادة التنظيم خلال هذا الموسم",
                "تطوير برامج تصفية للمنتجات بطيئة الحركة"
            ]
        })
    
    # Special event inventory strategies
    event_inventory_tactics = {}
    for event in seasonal_events:
        if event.get("strategicImportance") in ["مرتفعة", "مرتفعة جداً"]:
            event_name = event.get("name", "")
            
            if event_name not in event_inventory_tactics:
                event_inventory_tactics[event_name] = []
            
            if event_name in ["عيد الفطر", "عيد الأضحى"]:
                event_inventory_tactics[event_name].extend([
                    f"زيادة المخزون قبل {event_name} بثلاثة أسابيع على الأقل",
                    "توفير مخزون إضافي للمنتجات الأكثر طلباً خلال العيد",
                    "تحضير مواد تغليف خاصة بالعيد مسبقاً"
                ])
            elif event_name == "العودة للمدارس":
                event_inventory_tactics[event_name].extend([
                    "تحضير مخزون متنوع من المنتجات المدرسية قبل بداية العام الدراسي بشهرين",
                    "وضع خطة توريد مرنة تستجيب للطلب المتزايد",
                    "تنظيم المخزون وفقاً للفئات العمرية والمراحل الدراسية"
                ])
            elif event_name == "رمضان":
                event_inventory_tactics[event_name].extend([
                    "تعديل ساعات تجديد المخزون لتتناسب مع أنماط التسوق في رمضان",
                    "زيادة المخزون من المنتجات الأكثر طلباً في رمضان"
                ])
    
    # Create strategies from event tactics
    for event_name, tactics in event_inventory_tactics.items():
        if tactics:
            strategies.append({
                "type": "event",
                "title": f"إدارة المخزون لموسم {event_name}",
                "description": f"تحسين إدارة المخزون استعداداً لموسم {event_name}",
                "tactics": tactics
            })
    
    # Monthly inventory planning
    upward_months = [month for month, data in monthly_trends.items() if data.get("trend") == "upward"]
    downward_months = [month for month, data in monthly_trends.items() if data.get("trend") == "downward"]
    
    monthly_inventory_tactics = []
    if upward_months:
        months_str = " و".join(upward_months)
        monthly_inventory_tactics.append(f"زيادة المخزون قبل أشهر {months_str} التي تشهد نمواً في المبيعات")
    
    if downward_months:
        months_str = " و".join(downward_months)
        monthly_inventory_tactics.append(f"تخفيض المخزون خلال أشهر {months_str} التي تشهد انخفاضاً في المبيعات")
    
    if peak_months:
        months_str = " و".join(peak_months)
        monthly_inventory_tactics.append(f"تأمين كميات كافية من المنتجات الأكثر طلباً خلال أشهر الذروة {months_str}")
    
    if monthly_inventory_tactics:
        strategies.append({
            "type": "monthly",
            "title": "خطة إدارة المخزون الشهرية",
            "description": "تحسين إدارة المخزون وفقاً للاتجاهات الشهرية للمبيعات",
            "tactics": monthly_inventory_tactics + [
                "تطوير نظام إنذار مبكر لانخفاض مستويات المخزون",
                "تحليل بيانات المبيعات الشهرية بشكل دوري لتعديل خطط المخزون"
            ]
        })
    
    # General inventory management
    strategies.append({
        "type": "general",
        "title": "استراتيجية إدارة المخزون العامة",
        "description": "تحسين كفاءة إدارة المخزون بشكل عام على مدار السنة",
        "tactics": [
            "تطبيق نظام تصنيف ABC للمنتجات لتحديد أولويات إدارة المخزون",
            "تحسين دقة توقعات الطلب باستخدام تحليل البيانات التاريخية",
            "تطوير شراكات مرنة مع الموردين للاستجابة السريعة للتغيرات في الطلب",
            "مراجعة وتحسين مستويات المخزون الاحتياطي بشكل دوري",
            "تقليل وقت الانتظار بين الطلب والتوريد لتحسين دوران المخزون"
        ]
    })
    
    return strategies

@sales_strategy_bp.route('/performance-analysis/<category>', methods=['POST'])
def analyze_performance(category):
    """Comprehensive performance analysis with user input for specific strategic needs."""
    try:
        init_db()
        data = request.get_json()
        
        if not category:
            return jsonify({"error": "Category is required"}), 400
            
        # Get user input parameters
        inflation_factor = data.get('inflation_factor', 30)  # Default 30%
        analysis_notes = data.get('analysis_notes', '')
        
        # Run comprehensive analysis
        result = {
            "category": category,
            "analysis": {
                "seasonal": get_seasonal_events(category),
                "monthly": get_monthly_trends(category),
                "yearly": compare_years(category)
            },
            "inflationFactor": inflation_factor,
            "analysisNotes": analysis_notes
        }
        
        # Add specialized analysis based on trends
        result["performanceInsights"] = generate_performance_insights(
            category, 
            result["analysis"],
            inflation_factor
        )
        
        # Generate strategic recommendations
        result["strategicRecommendations"] = {
            "marketing": generate_marketing_strategies(
                category,
                result["analysis"]["seasonal"],
                result["analysis"]["monthly"],
                result["analysis"]["yearly"]
            ),
            "pricing": generate_pricing_strategies(
                category,
                result["analysis"]["seasonal"],
                result["analysis"]["yearly"]
            ),
            "inventory": generate_inventory_strategies(
                category,
                result["analysis"]["seasonal"],
                result["analysis"]["monthly"]
            )
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f" Error analyzing performance for {category}: {str(e)}")
        return jsonify({"error": str(e)}), 500

def generate_performance_insights(category, analysis_data, inflation_factor):
    """Generate in-depth performance insights based on all analyses."""
    insights = []
    
    # Extract key data points
    seasonal_data = analysis_data.get("seasonal", {})
    monthly_data = analysis_data.get("monthly", {})
    yearly_data = analysis_data.get("yearly", {})
    
    peak_months = seasonal_data.get("peakMonths", [])
    strongest_season = seasonal_data.get("strongestSeason", "")
    weakest_season = seasonal_data.get("weakestSeason", "")
    seasonal_events = seasonal_data.get("seasonalEvents", [])
    inflation_impact = yearly_data.get("inflationImpact", {"detected": False})
    yearly_comparison = yearly_data.get("yearlyComparison", [])
    monthly_trends = monthly_data.get("monthlyTrends", {})
    
    # Overall performance trend insights
    if yearly_comparison and len(yearly_comparison) >= 2:
        sorted_years = sorted(yearly_comparison, key=lambda x: x.get("year", 0))
        latest_year = sorted_years[-1]
        previous_year = sorted_years[-2]
        
        quantity_change = 0
        revenue_change = 0
        price_change = 0
        
        if "quantityGrowth" in latest_year:
            quantity_change = latest_year["quantityGrowth"]
        elif "totalQuantity" in latest_year and "totalQuantity" in previous_year and previous_year["totalQuantity"] > 0:
            quantity_change = ((latest_year["totalQuantity"] - previous_year["totalQuantity"]) / previous_year["totalQuantity"]) * 100
            
        if "revenueGrowth" in latest_year:
            revenue_change = latest_year["revenueGrowth"]
        elif "totalRevenue" in latest_year and "totalRevenue" in previous_year and previous_year["totalRevenue"] > 0:
            revenue_change = ((latest_year["totalRevenue"] - previous_year["totalRevenue"]) / previous_year["totalRevenue"]) * 100
            
        if "priceGrowth" in latest_year:
            price_change = latest_year["priceGrowth"]
        elif "avgPrice" in latest_year and "avgPrice" in previous_year and previous_year["avgPrice"] > 0:
            price_change = ((latest_year["avgPrice"] - previous_year["avgPrice"]) / previous_year["avgPrice"]) * 100
        
        # Create general performance insight
        performance_status = "مستقر" if -5 <= quantity_change <= 5 else "متزايد" if quantity_change > 5 else "متناقص"
        performance_insight = {
            "type": "overall",
            "title": f"أداء قسم {category} العام",
            "trend": performance_status,
            "description": f"أداء القسم {performance_status} مع تغير في الكمية بنسبة {quantity_change:.1f}% وتغير في الإيرادات بنسبة {revenue_change:.1f}%",
            "factors": []
        }
        
        # Add factors affecting performance
        if quantity_change < -5 and price_change > 5:
            performance_insight["factors"].append({
                "name": "تأثير التضخم",
                "description": f"يوجد مؤشرات على تأثير التضخم حيث ارتفعت الأسعار بنسبة {price_change:.1f}% بينما انخفضت الكميات بنسبة {abs(quantity_change):.1f}%",
                "severity": "عالية" if abs(quantity_change) > 15 else "متوسطة",
                "recommendations": [
                    "مراجعة استراتيجية التسعير للحفاظ على حجم المبيعات",
                    "تقديم منتجات بفئات سعرية متنوعة لتلبية مختلف الاحتياجات",
                    "تطوير برامج تحفيزية للحفاظ على العملاء الحاليين"
                ]
            })
        elif quantity_change < -10:
            performance_insight["factors"].append({
                "name": "انخفاض الطلب",
                "description": f"تراجع حجم المبيعات بشكل ملحوظ بنسبة {abs(quantity_change):.1f}%",
                "severity": "عالية" if abs(quantity_change) > 20 else "متوسطة",
                "recommendations": [
                    "تطوير حملات ترويجية لتحفيز الطلب",
                    "إجراء استطلاعات رأي للعملاء لفهم أسباب انخفاض الطلب",
                    "تحسين جودة المنتجات أو إضافة مزايا جديدة"
                ]
            })
        elif quantity_change > 15:
            performance_insight["factors"].append({
                "name": "نمو الطلب",
                "description": f"نمو ملحوظ في حجم المبيعات بنسبة {quantity_change:.1f}%",
                "severity": "إيجابية",
                "recommendations": [
                    "تأمين مستويات مخزون كافية لتلبية الطلب المتزايد",
                    "دراسة أسباب النمو واستثمارها في التسويق",
                    "تطوير تشكيلة المنتجات بناءً على تفضيلات العملاء"
                ]
            })
        
        insights.append(performance_insight)
    
    # Seasonal insights
    if strongest_season:
        seasonal_insight = {
            "type": "seasonal",
            "title": "تحليل الأداء الموسمي",
            "description": f"موسم {strongest_season} هو الأقوى أداءً، بينما موسم {weakest_season} هو الأضعف",
            "seasons": []
        }
        
        # Add peak seasons data
        seasonal_insight["seasons"].append({
            "name": strongest_season,
            "status": "قوي",
            "description": f"يُعد {strongest_season} موسم الذروة لمبيعات هذا القسم",
            "recommendations": [
                f"زيادة المخزون قبل موسم {strongest_season} بفترة كافية",
                "تطوير حملات تسويقية مكثفة خلال هذا الموسم",
                "تدريب فريق المبيعات على إدارة فترات الذروة",
                "تعديل الأسعار بما يتناسب مع ارتفاع الطلب"
            ]
        })
        
        # Add weak seasons data
        seasonal_insight["seasons"].append({
            "name": weakest_season,
            "status": "ضعيف",
            "description": f"يشهد موسم {weakest_season} أدنى مستويات المبيعات",
            "recommendations": [
                "تطوير عروض ترويجية خاصة لتحفيز المبيعات",
                "تخفيض مستويات المخزون لتجنب التكدس",
                "الاستفادة من هذه الفترة لتجديد المنتجات والتخطيط",
                "تقديم خصومات على المنتجات بطيئة الحركة"
            ]
        })
        
        insights.append(seasonal_insight)
    
    # Monthly trends insights
    if monthly_trends:
        growing_months = []
        declining_months = []
        
        for month, data in monthly_trends.items():
            if data.get("trend") == "upward":
                growing_months.append({
                    "name": month,
                    "growth_rate": data.get("growthRate", 0)
                })
            elif data.get("trend") == "downward":
                declining_months.append({
                    "name": month,
                    "decline_rate": abs(data.get("growthRate", 0))
                })
        
        # Sort by growth/decline rate
        growing_months.sort(key=lambda x: x["growth_rate"], reverse=True)
        declining_months.sort(key=lambda x: x["decline_rate"], reverse=True)
        
        if growing_months or declining_months:
            monthly_insight = {
                "type": "monthly",
                "title": "تحليل الاتجاهات الشهرية",
                "description": "تحليل أداء المبيعات على مستوى الشهور يظهر تبايناً واضحاً",
                "months": []
            }
            
            # Add top growing months
            if growing_months:
                top_growing = growing_months[:3]  # Top 3 growing months
                monthly_names = ", ".join([m["name"] for m in top_growing])
                monthly_insight["months"].append({
                    "type": "growing",
                    "names": monthly_names,
                    "description": f"أشهر {monthly_names} تظهر نمواً ملحوظاً في المبيعات",
                    "recommendations": [
                        "زيادة المخزون قبل هذه الشهور بفترة كافية",
                        "تكثيف الحملات التسويقية خلال هذه الفترات",
                        "استثمار هذه الفترات في تقديم منتجات جديدة"
                    ]
                })
            
            # Add top declining months
            if declining_months:
                top_declining = declining_months[:3]  # Top 3 declining months
                monthly_names = ", ".join([m["name"] for m in top_declining])
                monthly_insight["months"].append({
                    "type": "declining",
                    "names": monthly_names,
                    "description": f"أشهر {monthly_names} تشهد انخفاضاً في المبيعات",
                    "recommendations": [
                        "تطوير عروض ترويجية خاصة لتحفيز المبيعات",
                        "تخفيض مستويات المخزون خلال هذه الفترات",
                        "دراسة أسباب انخفاض المبيعات واتخاذ إجراءات تصحيحية"
                    ]
                })
            
            insights.append(monthly_insight)
    
    # Special events insights
    special_events_insight = {
        "type": "events",
        "title": "أثر المناسبات الخاصة على المبيعات",
        "description": "تحليل أثر المناسبات والمواسم الخاصة على أداء المبيعات",
        "events": []
    }
    
    # Process special events
    for event in seasonal_events:
        if event.get("strategicImportance") in ["مرتفعة", "مرتفعة جداً"]:
            event_name = event.get("name", "")
            sales_pattern = event.get("salesPattern", "")
            
            event_insight = {
                "name": event_name,
                "importance": event.get("strategicImportance", ""),
                "pattern": sales_pattern,
                "description": f"يؤثر موسم {event_name} بشكل {sales_pattern} على المبيعات",
                "recommendations": []
            }
            
            # Add specific recommendations based on event type
            if event_name == "رمضان":
                event_insight["recommendations"] = [
                    "تصميم حملات تسويقية خاصة بشهر رمضان",
                    "تعديل ساعات العمل لتناسب أنماط التسوق الرمضانية",
                    "تقديم عروض خاصة للتسوق بعد الإفطار",
                    "تجهيز مخزون كافٍ من المنتجات الأكثر طلباً"
                ]
            elif event_name in ["عيد الفطر", "عيد الأضحى"]:
                event_insight["recommendations"] = [
                    "بدء الاستعداد قبل العيد بثلاثة أسابيع على الأقل",
                    "تقديم باقات هدايا مميزة مع خدمات تغليف خاصة",
                    "تقديم عروض تصاعدية للمشتريات الكبيرة",
                    "تخصيص حملة تسويقية خاصة لفترة ما قبل العيد"
                ]
            elif event_name == "العودة للمدارس":
                if "مدارس" in category.lower() or "اطفال" in category.lower():
                    event_insight["recommendations"] = [
                        "بدء الاستعداد قبل بداية العام الدراسي بشهرين",
                        "تقديم عروض خاصة للمدارس والمشتريات الجماعية",
                        "تطوير باقات متكاملة من المستلزمات المدرسية",
                        "تنظيم حملات تسويقية تستهدف الأهالي والطلاب"
                    ]
                else:
                    event_insight["recommendations"] = [
                        "الاستفادة من موسم العودة للمدارس لجذب العائلات",
                        "تطوير عروض مشتركة مع منتجات مدرسية",
                        "زيادة الحملات الإعلانية خلال فترة التحضير للمدارس"
                    ]
            else:
                # Generic recommendations for other events
                event_insight["recommendations"] = [
                    f"تطوير استراتيجية تسويقية خاصة بموسم {event_name}",
                    "زيادة المخزون من المنتجات المناسبة للموسم",
                    "تقديم عروض خاصة خلال هذه الفترة"
                ]
            
            special_events_insight["events"].append(event_insight)
    
    # Only add events insight if we have special events
    if special_events_insight["events"]:
        insights.append(special_events_insight)
    
    # Inflation impact insights
    if inflation_impact and inflation_impact.get("detected", True):
        inflation_severity = inflation_impact.get("severity", "medium")
        avg_price_increase = inflation_impact.get("avgPriceIncrease", 0)
        quantity_decrease = inflation_impact.get("quantityDecrease", 0)
        
        inflation_insight = {
            "type": "economic",
            "title": "تأثير التضخم على أداء المبيعات",
            "severity": inflation_severity,
            "description": f"تأثير ملحوظ للتضخم مع زيادة الأسعار بنسبة {avg_price_increase:.1f}% وانخفاض الكميات بنسبة {quantity_decrease:.1f}%",
            "strategies": [
                {
                    "title": "استراتيجية التسعير في ظل التضخم",
                    "recommendations": [
                        "زيادة الأسعار بشكل تدريجي بدلاً من زيادات مفاجئة كبيرة",
                        "تطوير منتجات بفئات سعرية متنوعة لتلبية احتياجات مختلف العملاء",
                        "تقديم خصومات استراتيجية على منتجات مختارة للحفاظ على حجم المبيعات",
                        "إعادة تقييم هيكل التكاليف والبحث عن فرص لتحسين الكفاءة"
                    ]
                },
                {
                    "title": "استراتيجية القيمة المضافة",
                    "recommendations": [
                        "التركيز على إبراز القيمة المضافة للمنتجات لتبرير الأسعار",
                        "تقديم خدمات إضافية تميز المنتجات عن المنافسين",
                        "تطوير برامج ولاء لتعزيز العلاقة مع العملاء",
                        "الاهتمام بتجربة العملاء لتحقيق مستويات أعلى من الرضا"
                    ]
                }
            ]
        }
        
        # Add specific strategies based on severity
        if inflation_severity == "high":
            inflation_insight["strategies"].append({
                "title": "استراتيجية الحفاظ على الحصة السوقية",
                "recommendations": [
                    "إعادة تقييم هوامش الربح للمنتجات الأكثر حساسية للسعر",
                    "تطوير منتجات اقتصادية تناسب القدرة الشرائية المتغيرة",
                    "الاستثمار في تحسين كفاءة سلسلة التوريد لخفض التكاليف",
                    "التركيز على الميزة التنافسية غير السعرية (الجودة، الخدمة، التوفر)"
                ]
            })
        
        insights.append(inflation_insight)
    
    # Future forecasting insights
    future_insight = {
        "type": "forecast",
        "title": "توقعات الأداء المستقبلي",
        "description": f"توقعات أداء قسم {category} خلال الفترة القادمة في ضوء الاتجاهات الحالية",
        "forecasts": []
    }
    
    # Add different forecast scenarios based on analysis
    if yearly_comparison and len(yearly_comparison) >= 2:
        sorted_years = sorted(yearly_comparison, key=lambda x: x.get("year", 0))
        latest_year = sorted_years[-1]
        
        # Quantity trend forecast
        quantity_trend = "مستقر"
        if "quantityGrowth" in latest_year:
            if latest_year["quantityGrowth"] > 5:
                quantity_trend = "متزايد"
            elif latest_year["quantityGrowth"] < -5:
                quantity_trend = "متناقص"
        
        # Price trend forecast
        price_trend = "مستقر"
        if "priceGrowth" in latest_year:
            if latest_year["priceGrowth"] > 5:
                price_trend = "متزايد"
            elif latest_year["priceGrowth"] < -5:
                price_trend = "متناقص"
        
        # Base scenario
        future_insight["forecasts"].append({
            "scenario": "السيناريو الأساسي",
            "description": f"استناداً للاتجاهات الحالية، من المتوقع أن يكون حجم المبيعات {quantity_trend} ومستوى الأسعار {price_trend}",
            "factors": [
                f"استمرار تأثير التضخم بنسبة تقارب {inflation_factor}%" if inflation_impact and inflation_impact.get("detected", False) else "تأثير محدود للتضخم",
                f"موسم {strongest_season} سيستمر كأقوى موسم للمبيعات" if strongest_season else "استمرار التذبذب الموسمي في المبيعات",
                "الاستفادة من المناسبات الخاصة في زيادة المبيعات"
            ],
            "recommendations": [
                "الاستعداد المبكر للمواسم والمناسبات الخاصة",
                "تعديل استراتيجية التسعير بما يتناسب مع التغيرات الاقتصادية",
                "التركيز على تحسين تجربة العملاء لتعزيز الولاء",
                "مراقبة مستمرة لسلوك العملاء والاستجابة السريعة للتغيرات"
            ]
        })
        
        # Optimistic scenario
        future_insight["forecasts"].append({
            "scenario": "السيناريو المتفائل",
            "description": "توقع تحسن في أداء المبيعات مع انخفاض تأثير التضخم وزيادة الطلب",
            "factors": [
                "انخفاض معدلات التضخم وتحسن القدرة الشرائية",
                "تحسن في الأداء الاقتصادي العام",
                "نجاح الحملات التسويقية وزيادة الحصة السوقية"
            ],
            "recommendations": [
                "الاستثمار في توسيع تشكيلة المنتجات",
                "زيادة المخزون استعداداً للنمو المتوقع",
                "تطوير استراتيجيات تسويقية جديدة للاستفادة من التحسن الاقتصادي"
            ]
        })
        
        # Pessimistic scenario
        future_insight["forecasts"].append({
            "scenario": "السيناريو المتشائم",
            "description": "توقع استمرار انخفاض الطلب وزيادة تأثير التضخم",
            "factors": [
                "استمرار الضغوط التضخمية وانخفاض القدرة الشرائية",
                "تزايد المنافسة في السوق",
                "تغير في أنماط الاستهلاك"
            ],
            "recommendations": [
                "تخفيض مستويات المخزون وتحسين كفاءة إدارته",
                "التركيز على المنتجات الأساسية والأكثر مبيعاً",
                "تقديم خيارات منتجات اقتصادية",
                "تطوير استراتيجيات للحفاظ على العملاء الحاليين"
            ]
        })
        
        insights.append(future_insight)
    
    return insights

# Helper function to generate strategic action plans for various business aspects
def generate_strategic_action_plan(category, insights, inflation_factor=30):
    """Generate a comprehensive strategic action plan based on performance insights."""
    action_plans = {
        "marketing": {
            "title": "خطة العمل التسويقية",
            "description": f"خطة عمل تسويقية متكاملة لقسم {category} بناءً على تحليل الأداء",
            "timeframes": {
                "immediate": {
                    "title": "إجراءات فورية (1-3 أشهر)",
                    "actions": []
                },
                "short_term": {
                    "title": "إجراءات قصيرة المدى (3-6 أشهر)",
                    "actions": []
                },
                "long_term": {
                    "title": "إجراءات طويلة المدى (6-12 شهر)",
                    "actions": []
                }
            }
        },
        "pricing": {
            "title": "خطة استراتيجية التسعير",
            "description": f"خطة استراتيجية للتسعير لقسم {category} مع مراعاة التأثيرات الاقتصادية",
            "timeframes": {
                "immediate": {
                    "title": "إجراءات فورية (1-3 أشهر)",
                    "actions": []
                },
                "short_term": {
                    "title": "إجراءات قصيرة المدى (3-6 أشهر)",
                    "actions": []
                },
                "long_term": {
                    "title": "إجراءات طويلة المدى (6-12 شهر)",
                    "actions": []
                }
            }
        },
        "inventory": {
            "title": "خطة إدارة المخزون",
            "description": f"خطة متكاملة لإدارة مخزون قسم {category} وفقاً للاتجاهات الموسمية",
            "timeframes": {
                "immediate": {
                    "title": "إجراءات فورية (1-3 أشهر)",
                    "actions": []
                },
                "short_term": {
                    "title": "إجراءات قصيرة المدى (3-6 أشهر)",
                    "actions": []
                },
                "long_term": {
                    "title": "إجراءات طويلة المدى (6-12 شهر)",
                    "actions": []
                }
            }
        }
    }
    
    # Process all insights to extract action items
    for insight in insights:
        insight_type = insight.get("type", "")
        
        # Process overall performance insights
        if insight_type == "overall":
            trend = insight.get("trend", "")
            factors = insight.get("factors", [])
            
            if trend == "متناقص":
                # Marketing actions for declining performance
                action_plans["marketing"]["timeframes"]["immediate"]["actions"].extend([
                    "إجراء تحليل فوري لأسباب انخفاض المبيعات",
                    "تطوير حملة ترويجية عاجلة لتنشيط المبيعات",
                    "مراجعة استراتيجية التواصل مع العملاء وتحسينها"
                ])
                
                # Pricing actions for declining performance
                action_plans["pricing"]["timeframes"]["immediate"]["actions"].extend([
                    "مراجعة هيكل الأسعار ومقارنته بالمنافسين",
                    "تقديم عروض خاصة على المنتجات الأكثر طلباً",
                    "دراسة إمكانية تخفيض هوامش الربح مؤقتاً للحفاظ على حجم المبيعات"
                ])
                
                # Inventory actions for declining performance
                action_plans["inventory"]["timeframes"]["immediate"]["actions"].extend([
                    "تقليل مستويات المخزون تدريجياً",
                    "التركيز على المنتجات سريعة الحركة",
                    "تطوير خطة لتصفية المخزون بطيء الحركة"
                ])
            
            elif trend == "متزايد":
                # Marketing actions for growing performance
                action_plans["marketing"]["timeframes"]["short_term"]["actions"].extend([
                    "تحليل أسباب النمو وتعزيز العوامل الإيجابية",
                    "زيادة الميزانية التسويقية للبناء على النمو الحالي",
                    "توسيع استهداف شرائح جديدة من العملاء"
                ])
                
                # Pricing actions for growing performance
                action_plans["pricing"]["timeframes"]["short_term"]["actions"].extend([
                    "مراجعة هيكل الأسعار لتحقيق أقصى ربحية مع الحفاظ على النمو",
                    "تقديم برامج ولاء ومكافآت للعملاء المتكررين",
                    "دراسة إمكانية تحسين هوامش الربح تدريجياً"
                ])
                
                # Inventory actions for growing performance
                action_plans["inventory"]["timeframes"]["immediate"]["actions"].extend([
                    "زيادة مستويات المخزون لتلبية الطلب المتزايد",
                    "توسيع تشكيلة المنتجات",
                    "تطوير نظام إنذار مبكر لانخفاض المخزون"
                ])
            
            # Process inflation factors
            for factor in factors:
                if "تأثير التضخم" in factor.get("name", ""):
                    severity = factor.get("severity", "متوسطة")
                    
                    # Marketing actions for inflation
                    action_plans["marketing"]["timeframes"]["short_term"]["actions"].extend([
                        "تطوير حملات تسويقية تركز على القيمة المضافة للمنتجات",
                        "تعزيز التواصل مع العملاء لشرح سياسات التسعير",
                        "إطلاق حملات تستهدف العملاء ذوي الولاء العالي"
                    ])
                    
                    # Pricing actions for inflation
                    pricing_actions = [
                        "تطبيق زيادات سعرية تدريجية بدلاً من زيادة واحدة كبيرة",
                        "تطوير منتجات بفئات سعرية متنوعة",
                        "تقديم خيارات دفع مرنة أو تقسيط للمشتريات الكبيرة"
                    ]
                    
                    if severity == "عالية":
                        pricing_actions.extend([
                            "تخفيض هوامش الربح على بعض المنتجات الاستراتيجية للحفاظ على حجم المبيعات",
                            "إعادة تقييم شامل لهيكل التكاليف للحد من تأثير التضخم"
                        ])
                    
                    action_plans["pricing"]["timeframes"]["immediate"]["actions"].extend(pricing_actions)
                    
                    # Inventory actions for inflation
                    action_plans["inventory"]["timeframes"]["short_term"]["actions"].extend([
                        "تحسين كفاءة سلسلة التوريد لتقليل التكاليف",
                        "التركيز على المنتجات ذات هامش الربح الأعلى",
                        "تخفيض المخزون من المنتجات ذات الحساسية السعرية العالية"
                    ])
        
        # Process seasonal insights
        elif insight_type == "seasonal":
            seasons = insight.get("seasons", [])
            
            for season in seasons:
                season_name = season.get("name", "")
                status = season.get("status", "")
                recommendations = season.get("recommendations", [])
                
                if status == "قوي":
                    # Strong season actions
                    action_plans["marketing"]["timeframes"]["short_term"]["actions"].extend([
                        f"تطوير حملة تسويقية مخصصة لموسم {season_name}",
                        "زيادة الميزانية التسويقية خلال هذا الموسم",
                        "تنظيم فعاليات ترويجية خاصة خلال فترة الذروة"
                    ])
                    
                    action_plans["pricing"]["timeframes"]["short_term"]["actions"].extend([
                        f"رفع الأسعار بنسبة 10-15% خلال موسم {season_name}",
                        "تقديم عروض خاصة على المنتجات المكملة لزيادة متوسط قيمة المشتريات"
                    ])
                    
                    action_plans["inventory"]["timeframes"]["short_term"]["actions"].extend([
                        f"زيادة المخزون قبل موسم {season_name} بشهر على الأقل",
                        "توسيع تشكيلة المنتجات خلال هذا الموسم",
                        "تأمين خط إمداد مرن ومستمر خلال فترة الذروة"
                    ])
                
                elif status == "ضعيف":
                    # Weak season actions
                    action_plans["marketing"]["timeframes"]["short_term"]["actions"].extend([
                        f"تطوير حملات ترويجية خاصة لتنشيط المبيعات في موسم {season_name}",
                        "تقديم عروض حصرية للعملاء الدائمين",
                        "استخدام استراتيجيات التسويق الرقمي بشكل مكثف"
                    ])
                    
                    action_plans["pricing"]["timeframes"]["short_term"]["actions"].extend([
                        f"تخفيض الأسعار بنسبة 5-10% خلال موسم {season_name}",
                        "تقديم خصومات تصاعدية مع زيادة قيمة المشتريات",
                        "تطوير برامج ولاء وحوافز للعملاء"
                    ])
                    
                    action_plans["inventory"]["timeframes"]["short_term"]["actions"].extend([
                        f"تخفيض مستويات المخزون خلال موسم {season_name}",
                        "التركيز على المنتجات الأساسية والأكثر مبيعاً",
                        "تطوير برامج تصفية للمنتجات بطيئة الحركة"
                    ])
        
        # Process monthly trends insights
        elif insight_type == "monthly":
            months = insight.get("months", [])
            
            for month_data in months:
                month_type = month_data.get("type", "")
                month_names = month_data.get("names", "")
                recommendations = month_data.get("recommendations", [])
                
                if month_type == "growing":
                    # Growing months actions
                    action_plans["marketing"]["timeframes"]["short_term"]["actions"].extend([
                        f"تكثيف الحملات التسويقية قبل وخلال أشهر {month_names}",
                        "استخدام التحليلات للتنبؤ بالمنتجات الأكثر طلباً في هذه الأشهر"
                    ])
                    
                    action_plans["pricing"]["timeframes"]["short_term"]["actions"].extend([
                        f"تعديل الأسعار بما يتناسب مع زيادة الطلب في أشهر {month_names}",
                        "تقديم عروض خاصة على المنتجات المكملة"
                    ])
                    
                    action_plans["inventory"]["timeframes"]["short_term"]["actions"].extend([
                        f"زيادة المخزون قبل أشهر {month_names}",
                        "توفير تشكيلة واسعة من المنتجات"
                    ])
                
                elif month_type == "declining":
                    # Declining months actions
                    action_plans["marketing"]["timeframes"]["short_term"]["actions"].extend([
                        f"تطوير حملات ترويجية مخصصة لأشهر {month_names}",
                        "استهداف العملاء السابقين بعروض خاصة",
                        "تنويع قنوات التسويق لزيادة الوصول"
                    ])
                    
                    action_plans["pricing"]["timeframes"]["short_term"]["actions"].extend([
                        f"تخفيض الأسعار خلال أشهر {month_names}",
                        "تقديم خصومات استثنائية على المنتجات بطيئة الحركة"
                    ])
                    
                    action_plans["inventory"]["timeframes"]["short_term"]["actions"].extend([
                        f"تخفيض مستويات المخزون خلال أشهر {month_names}",
                        "جدولة عمليات الجرد وإعادة التنظيم"
                    ])
        
        # Process special events insights
        elif insight_type == "events":
            events = insight.get("events", [])
            
            for event in events:
                event_name = event.get("name", "")
                importance = event.get("importance", "")
                recommendations = event.get("recommendations", [])
                
                # Only process important events
                if importance in ["مرتفعة", "مرتفعة جداً"]:
                    # Add the recommendations to appropriate action plans
                    marketing_actions = []
                    pricing_actions = []
                    inventory_actions = []
                    
                    for rec in recommendations:
                        if "تسويق" in rec or "حمل" in rec or "إعلان" in rec or "ترويج" in rec:
                            marketing_actions.append(rec)
                        elif "سعر" in rec or "خصم" in rec:
                            pricing_actions.append(rec)
                        elif "مخزون" in rec or "كمي" in rec:
                            inventory_actions.append(rec)
                    
                    if marketing_actions:
                        action_plans["marketing"]["timeframes"]["short_term"]["actions"].extend(marketing_actions)
                    
                    if pricing_actions:
                        action_plans["pricing"]["timeframes"]["short_term"]["actions"].extend(pricing_actions)
                    
                    if inventory_actions:
                        action_plans["inventory"]["timeframes"]["short_term"]["actions"].extend(inventory_actions)
        
        # Process economic insights
        elif insight_type == "economic":
            strategies = insight.get("strategies", [])
            
            for strategy in strategies:
                strategy_title = strategy.get("title", "")
                recommendations = strategy.get("recommendations", [])
                
                # Categorize recommendations by department
                for rec in recommendations:
                    if "تسويق" in rec or "القيمة" in rec or "العملاء" in rec or "تجربة" in rec:
                        action_plans["marketing"]["timeframes"]["immediate"]["actions"].append(rec)
                    elif "سعر" in rec or "خصم" in rec or "قيمة" in rec:
                        action_plans["pricing"]["timeframes"]["immediate"]["actions"].append(rec)
                    elif "مخزون" in rec or "توريد" in rec or "تكاليف" in rec:
                        action_plans["inventory"]["timeframes"]["immediate"]["actions"].append(rec)
        
        # Process forecast insights
        elif insight_type == "forecast":
            forecasts = insight.get("forecasts", [])
            
            for forecast in forecasts:
                scenario = forecast.get("scenario", "")
                recommendations = forecast.get("recommendations", [])
                
                # Only process base scenario for action plans
                if scenario == "السيناريو الأساسي":
                    # Add long term actions
                    action_plans["marketing"]["timeframes"]["long_term"]["actions"].extend([rec for rec in recommendations if "تسويق" in rec or "عملاء" in rec or "حمل" in rec])
                    action_plans["pricing"]["timeframes"]["long_term"]["actions"].extend([rec for rec in recommendations if "سعر" in rec or "خصم" in rec])
                    action_plans["inventory"]["timeframes"]["long_term"]["actions"].extend([rec for rec in recommendations if "مخزون" in rec or "كمي" in rec])
    
    # Remove duplicate actions
    for dept in action_plans:
        for timeframe in action_plans[dept]["timeframes"]:
            action_plans[dept]["timeframes"][timeframe]["actions"] = list(set(action_plans[dept]["timeframes"][timeframe]["actions"]))
    
    return action_plans

@sales_strategy_bp.route('/cross-year-comparison/<category>', methods=['GET'])
def cross_year_comparison(category):
    """Compare sales performance across years for the same months/seasons."""
    try:
        init_db()
        
        if not category:
            return jsonify({"error": "Category is required"}), 400
        
        # Fetch data for the category
        collection = get_collection("item_specification_monthly_demand")
        data = list(collection.find({"القسم": category}, {"_id": 0}))
        
        if not data:
            return jsonify({"error": f"No data found for category: {category}"}), 404
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Ensure numeric values
        df["total_quantity"] = pd.to_numeric(df["total_quantity"], errors="coerce")
        df["total_money_sold"] = pd.to_numeric(df["total_money_sold"], errors="coerce")
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["month"] = pd.to_numeric(df["month"], errors="coerce")
        
        # Define month names
        month_names = [
            'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
            'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
        ]
        
        # Create month name mapping
        month_name_map = {i+1: name for i, name in enumerate(month_names)}
        
        # Cross-year comparison by month
        monthly_comparison = []
        
        for month in range(1, 13):
            month_data = df[df["month"] == month]
            
            if month_data.empty:
                continue
                
            # Group by year
            year_data = month_data.groupby("year").agg({
                "total_quantity": "sum",
                "total_money_sold": "sum"
            }).reset_index()
            
            # Calculate unit price
            year_data["unit_price"] = year_data["total_money_sold"] / year_data["total_quantity"]
            year_data["unit_price"] = year_data["unit_price"].round(2)
            
            # Check for declining quantities with rising prices
            has_declining_quantity = False
            has_rising_prices = False
            
            if len(year_data) >= 2:
                sorted_data = year_data.sort_values("year")
                
                # Calculate year-over-year changes
                sorted_data["qty_change"] = sorted_data["total_quantity"].pct_change() * 100
                sorted_data["price_change"] = sorted_data["unit_price"].pct_change() * 100
                
                # Check last year's change
                latest_data = sorted_data.iloc[-1]
                
                if "qty_change" in latest_data and "price_change" in latest_data:
                    has_declining_quantity = latest_data["qty_change"] < -5  # More than 5% decrease
                    has_rising_prices = latest_data["price_change"] > 5  # More than 5% increase
            
            # Format data for response
            month_comparison = {
                "month": month,
                "month_name": month_name_map[month],
                "years": [],
                "has_inflation_impact": has_declining_quantity and has_rising_prices
            }
            
            for _, row in year_data.iterrows():
                year_item = {
                    "year": int(row["year"]),
                    "quantity": int(row["total_quantity"]),
                    "revenue": float(row["total_money_sold"]),
                    "unit_price": float(row["unit_price"])
                }
                
                if "qty_change" in row and not pd.isna(row["qty_change"]):
                    year_item["quantity_change"] = float(round(row["qty_change"], 1))
                
                if "price_change" in row and not pd.isna(row["price_change"]):
                    year_item["price_change"] = float(round(row["price_change"], 1))
                
                month_comparison["years"].append(year_item)
            
            monthly_comparison.append(month_comparison)
        
        # Cross-year comparison by season
        # Define seasons
        winter_months = [12, 1, 2]
        spring_months = [3, 4, 5]
        summer_months = [6, 7, 8]
        fall_months = [9, 10, 11]
        
        # Function to assign season
        def get_season(month):
            if month in winter_months:
                return "الشتاء"
            elif month in spring_months:
                return "الربيع"
            elif month in summer_months:
                return "الصيف"
            else:
                return "الخريف"
        
        # Add season to data
        df["season"] = df["month"].apply(get_season)
        
        # Cross-year comparison by season
        seasonal_comparison = []
        
        for season in ["الشتاء", "الربيع", "الصيف", "الخريف"]:
            season_data = df[df["season"] == season]
            
            if season_data.empty:
                continue
                
            # Group by year
            year_data = season_data.groupby("year").agg({
                "total_quantity": "sum",
                "total_money_sold": "sum"
            }).reset_index()
            
            # Calculate unit price
            year_data["unit_price"] = year_data["total_money_sold"] / year_data["total_quantity"]
            year_data["unit_price"] = year_data["unit_price"].round(2)
            
            # Check for declining quantities with rising prices
            has_declining_quantity = False
            has_rising_prices = False
            
            if len(year_data) >= 2:
                sorted_data = year_data.sort_values("year")
                
                # Calculate year-over-year changes
                sorted_data["qty_change"] = sorted_data["total_quantity"].pct_change() * 100
                sorted_data["price_change"] = sorted_data["unit_price"].pct_change() * 100
                
                # Check last year's change
                latest_data = sorted_data.iloc[-1]
                
                if "qty_change" in latest_data and "price_change" in latest_data:
                    has_declining_quantity = latest_data["qty_change"] < -5  # More than 5% decrease
                    has_rising_prices = latest_data["price_change"] > 5  # More than 5% increase
            
            # Format data for response
            season_comparison = {
                "season": season,
                "years": [],
                "has_inflation_impact": has_declining_quantity and has_rising_prices
            }
            
            for _, row in year_data.iterrows():
                year_item = {
                    "year": int(row["year"]),
                    "quantity": int(row["total_quantity"]),
                    "revenue": float(row["total_money_sold"]),
                    "unit_price": float(row["unit_price"])
                }
                
                if "qty_change" in row and not pd.isna(row["qty_change"]):
                    year_item["quantity_change"] = float(round(row["qty_change"], 1))
                
                if "price_change" in row and not pd.isna(row["price_change"]):
                    year_item["price_change"] = float(round(row["price_change"], 1))
                
                season_comparison["years"].append(year_item)
            
            seasonal_comparison.append(season_comparison)
        
        # Identify overall inflation impact
        overall_inflation_impact = any(m["has_inflation_impact"] for m in monthly_comparison) or any(s["has_inflation_impact"] for s in seasonal_comparison)
        
        # Identify patterns
        quantity_declining_months = [m["month_name"] for m in monthly_comparison if m["years"] and len(m["years"]) >= 2 and "quantity_change" in m["years"][-1] and m["years"][-1]["quantity_change"] < -5]
        
        quantity_growing_months = [m["month_name"] for m in monthly_comparison if m["years"] and len(m["years"]) >= 2 and "quantity_change" in m["years"][-1] and m["years"][-1]["quantity_change"] > 5]
        
        # Generate strategic insights
        strategic_insights = {
            "overall": {
                "has_inflation_impact": overall_inflation_impact,
                "quantity_declining_months": quantity_declining_months,
                "quantity_growing_months": quantity_growing_months
            },
            "marketing_strategies": [],
            "pricing_strategies": [],
            "inventory_strategies": []
        }
        
        # Add inflation related strategies
        if overall_inflation_impact:
            strategic_insights["marketing_strategies"].extend([
                "تطوير حملات تسويقية تركز على القيمة المضافة للمنتجات وليس فقط السعر",
                "تعزيز التواصل مع العملاء لشرح سياسات التسعير في ظل التضخم",
                "إطلاق برامج ولاء لمكافأة العملاء الدائمين"
            ])
            
            strategic_insights["pricing_strategies"].extend([
                "تطبيق زيادات سعرية تدريجية بدلاً من زيادة واحدة كبيرة",
                "تطوير منتجات بفئات سعرية متنوعة لتلبية احتياجات مختلف العملاء",
                "تحليل مرونة الطلب السعرية لتحديد أفضل استراتيجية تسعير"
            ])
            
            strategic_insights["inventory_strategies"].extend([
                "تحسين كفاءة سلسلة التوريد لتقليل التكاليف",
                "التركيز على المنتجات ذات هامش الربح الأعلى",
                "إعادة تقييم مستويات المخزون للتأقلم مع انخفاض الطلب"
            ])
        
        # Add strategies for declining months
        if quantity_declining_months:
            month_str = " و".join(quantity_declining_months)
            
            strategic_insights["marketing_strategies"].extend([
                f"تطوير حملات ترويجية خاصة لأشهر {month_str} التي تشهد انخفاضاً في المبيعات",
                "استهداف العملاء السابقين بعروض خاصة",
                "تنويع قنوات التسويق لزيادة الوصول"
            ])
            
            strategic_insights["pricing_strategies"].extend([
                f"تقديم خصومات استراتيجية خلال أشهر {month_str}",
                "تطوير عروض خاصة للكميات الكبيرة",
                "تقديم حوافز سعرية للعملاء الجدد"
            ])
            
            strategic_insights["inventory_strategies"].extend([
                f"تخفيض مستويات المخزون خلال أشهر {month_str}",
                "التركيز على المنتجات الأساسية والأكثر مبيعاً",
                "تطوير خطة لتصفية المنتجات بطيئة الحركة"
            ])
        
        # Add strategies for growing months
        if quantity_growing_months:
            month_str = " و".join(quantity_growing_months)
            
            strategic_insights["marketing_strategies"].extend([
                f"تكثيف الحملات التسويقية قبل وخلال أشهر {month_str}",
                "الاستثمار في حملات إعلانية مستهدفة",
                "تطوير عروض خاصة للمناسبات والمواسم"
            ])
            
            strategic_insights["pricing_strategies"].extend([
                f"تعديل الأسعار بما يتناسب مع زيادة الطلب في أشهر {month_str}",
                "تقديم عروض خاصة على المنتجات المكملة لزيادة متوسط قيمة المشتريات"
            ])
            
            strategic_insights["inventory_strategies"].extend([
                f"زيادة المخزون قبل أشهر {month_str} بفترة كافية",
                "توسيع تشكيلة المنتجات خلال هذه الفترات",
                "تأمين خط إمداد مرن ومستمر خلال فترات الذروة"
            ])
        
        # Add seasonal event strategies
        event_strategies = generate_seasonal_event_strategies(category, monthly_comparison)
        
        strategic_insights["event_strategies"] = event_strategies
        
        return jsonify({
            "category": category,
            "monthly_comparison": monthly_comparison,
            "seasonal_comparison": seasonal_comparison,
            "strategic_insights": strategic_insights
        }), 200
        
    except Exception as e:
        print(f" Error in cross-year comparison for {category}: {str(e)}")
        return jsonify({"error": str(e)}), 500

def generate_seasonal_event_strategies(category, monthly_data):
    """Generate strategies for seasonal events based on monthly performance data."""
    event_strategies = []
    
    # Define key seasonal events and their typical months
    seasonal_events = [
        {
            "name": "رمضان",
            "months": [8, 9, 10],  # Approximate Ramadan months
            "month_names": ["أغسطس", "سبتمبر", "أكتوبر"]
        },
        {
            "name": "عيد الفطر",
            "months": [9, 10],  # Approximate Eid al-Fitr months
            "month_names": ["سبتمبر", "أكتوبر"]
        },
        {
            "name": "عيد الأضحى",
            "months": [11, 12],  # Approximate Eid al-Adha months
            "month_names": ["نوفمبر", "ديسمبر"]
        },
        {
            "name": "العودة للمدارس",
            "months": [8, 9],  # Back to school months
            "month_names": ["أغسطس", "سبتمبر"]
        },
        {
            "name": "الشتاء",
            "months": [12, 1, 2],  # Winter months
            "month_names": ["ديسمبر", "يناير", "فبراير"]
        },
        {
            "name": "الصيف",
            "months": [6, 7, 8],  # Summer months
            "month_names": ["يونيو", "يوليو", "أغسطس"]
        }
    ]
    
    # Check if there's growth in the event months
    for event in seasonal_events:
        event_months = event["month_names"]
        
        # Check if there's data for these months
        relevant_data = [m for m in monthly_data if m["month_name"] in event_months]
        
        if not relevant_data:
            continue
        
        # Check if there's sales growth in these months
        growing_months = []
        for m in relevant_data:
            if m["years"] and len(m["years"]) >= 2:
                latest_year = sorted(m["years"], key=lambda x: x["year"])[-1]
                if "quantity_change" in latest_year and latest_year["quantity_change"] > 0:
                    growing_months.append(m["month_name"])
        
        # Generate strategies based on growth patterns
        if growing_months:
            # This is a growing seasonal event
            strategies = {
                "event": event["name"],
                "growing_months": growing_months,
                "is_growing": True,
                "marketing_strategies": [],
                "pricing_strategies": [],
                "inventory_strategies": []
            }
            
            # Event-specific strategies
            if event["name"] == "رمضان":
                strategies["marketing_strategies"] = [
                    "تصميم حملات إعلانية تعكس روح شهر رمضان",
                    "تكثيف الإعلانات خلال فترات المساء بعد الإفطار",
                    "إطلاق حملات تسويق تفاعلية على منصات التواصل الاجتماعي"
                ]
                
                strategies["pricing_strategies"] = [
                    "تطوير باقات منتجات بأسعار خاصة لشهر رمضان",
                    "تقديم خصومات للمشتريات بكميات كبيرة للعائلات"
                ]
                
                strategies["inventory_strategies"] = [
                    "زيادة المخزون قبل شهر رمضان بثلاثة أسابيع",
                    "تعديل ساعات تجديد المخزون لتتناسب مع أنماط التسوق الرمضانية"
                ]
            
            elif event["name"] in ["عيد الفطر", "عيد الأضحى"]:
                strategies["marketing_strategies"] = [
                    "إطلاق حملة ترويجية قبل العيد بثلاثة أسابيع",
                    "تصميم عروض هدايا مميزة مع تغليف خاص للعيد",
                    "تنفيذ استراتيجية تسويق متكاملة عبر القنوات المختلفة"
                ]
                
                strategies["pricing_strategies"] = [
                    "تطبيق أسعار خاصة لمنتجات العيد مع التركيز على جودة المنتج",
                    "تقديم خصومات تصاعدية مع زيادة قيمة المشتريات"
                ]
                
                strategies["inventory_strategies"] = [
                    "زيادة المخزون قبل العيد بثلاثة أسابيع على الأقل",
                    "توفير مخزون إضافي للمنتجات الأكثر طلباً خلال العيد",
                    "تحضير مواد تغليف خاصة بالعيد مسبقاً"
                ]
            
            elif event["name"] == "العودة للمدارس":
                if category.lower() in ["مدارس", "اطفال"]:
                    strategies["marketing_strategies"] = [
                        "إطلاق حملة 'العودة للمدرسة' قبل بداية العام الدراسي بشهر",
                        "تقديم عروض خاصة للمشتريات العائلية أو للمدارس",
                        "الترويج لمنتجات متكاملة كحزم متكاملة بسعر مميز"
                    ]
                    
                    strategies["pricing_strategies"] = [
                        "تقديم خصومات تصاعدية على مشتريات العودة للمدارس كلما زادت الكمية",
                        "عروض خاصة للمدارس والمشتريات الجماعية"
                    ]
                    
                    strategies["inventory_strategies"] = [
                        "تحضير مخزون متنوع من المنتجات المدرسية قبل بداية العام الدراسي بشهرين",
                        "تنظيم المخزون وفقاً للفئات العمرية والمراحل الدراسية"
                    ]
                else:
                    strategies["marketing_strategies"] = [
                        "الاستفادة من موسم العودة للمدارس لجذب العائلات",
                        "تطوير عروض مشتركة مع منتجات مدرسية",
                        "زيادة الحملات الإعلانية خلال فترة التحضير للمدارس"
                    ]
            
            elif event["name"] == "الصيف":
                strategies["marketing_strategies"] = [
                    "التركيز على الملابس الخفيفة والألوان الفاتحة",
                    "تقديم عروض خاصة للعطلات الصيفية",
                    "تطوير حملات تستهدف السفر والأنشطة الصيفية"
                ]
                
            elif event["name"] == "الشتاء":
                strategies["marketing_strategies"] = [
                    "التركيز على الملابس الثقيلة والدافئة",
                    "تقديم عروض خاصة للمناسبات الشتوية",
                    "تطوير حملات تناسب أجواء الشتاء"
                ]
            
            # Add the strategies to the result
            event_strategies.append(strategies)
    
    return event_strategies

@sales_strategy_bp.route('/monthly-performance-comparison/<category>', methods=['GET'])
def monthly_performance_comparison(category):
    """Compare performance of the same month across different years to detect seasonal patterns and annual trends."""
    try:
        init_db()
        
        if not category:
            return jsonify({"error": "Category is required"}), 400
        
        # Fetch data for the category
        collection = get_collection("item_specification_monthly_demand")
        data = list(collection.find({"القسم": category}, {"_id": 0}))
        
        if not data:
            return jsonify({"error": f"No data found for category: {category}"}), 404
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Ensure numeric values
        df["total_quantity"] = pd.to_numeric(df["total_quantity"], errors="coerce")
        df["total_money_sold"] = pd.to_numeric(df["total_money_sold"], errors="coerce")
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["month"] = pd.to_numeric(df["month"], errors="coerce")
        
        # Define month names
        month_names = [
            'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
            'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
        ]
        
        # Create month name mapping
        month_name_map = {i+1: name for i, name in enumerate(month_names)}
        
        # Group by month and year
        monthly_yearly = df.groupby(["month", "year"]).agg({
            "total_quantity": "sum",
            "total_money_sold": "sum"
        }).reset_index()
        
        # Calculate unit price
        monthly_yearly["unit_price"] = monthly_yearly["total_money_sold"] / monthly_yearly["total_quantity"]
        monthly_yearly["unit_price"] = monthly_yearly["unit_price"].fillna(0).round(2)
        
        # Format response for all months
        months_comparison = {}
        
        for month in range(1, 13):
            month_data = monthly_yearly[monthly_yearly["month"] == month]
            
            if month_data.empty:
                continue
                
            # Sort by year
            month_data = month_data.sort_values("year")
            
            # Calculate year-over-year growth rates
            month_data["quantity_growth"] = month_data["total_quantity"].pct_change() * 100
            month_data["revenue_growth"] = month_data["total_money_sold"].pct_change() * 100
            month_data["price_growth"] = month_data["unit_price"].pct_change() * 100
            
            # Prepare data for response
            years_data = []
            for _, row in month_data.iterrows():
                year_data = {
                    "year": int(row["year"]),
                    "quantity": int(row["total_quantity"]),
                    "revenue": float(row["total_money_sold"]),
                    "unit_price": float(row["unit_price"])
                }
                
                # Add growth rates if available
                if not pd.isna(row["quantity_growth"]):
                    year_data["quantity_growth"] = float(row["quantity_growth"].round(1))
                if not pd.isna(row["revenue_growth"]):
                    year_data["revenue_growth"] = float(row["revenue_growth"].round(1))
                if not pd.isna(row["price_growth"]):
                    year_data["price_growth"] = float(row["price_growth"].round(1))
                
                years_data.append(year_data)
            
            # Calculate average metrics across years
            avg_metrics = {
                "avg_quantity": float(month_data["total_quantity"].mean().round()),
                "avg_revenue": float(month_data["total_money_sold"].mean().round()),
                "avg_unit_price": float(month_data["unit_price"].mean().round(2))
            }
            
            # Check for inflation impact in the most recent year
            has_inflation_impact = False
            if len(years_data) >= 2:
                latest_year = years_data[-1]
                if "price_growth" in latest_year and "quantity_growth" in latest_year:
                    if latest_year["price_growth"] > 5 and latest_year["quantity_growth"] < 0:
                        has_inflation_impact = True
            
            months_comparison[month_name_map[month]] = {
                "years_data": years_data,
                "avg_metrics": avg_metrics,
                "has_inflation_impact": has_inflation_impact
            }
        
        # Identify top and bottom months by average quantity
        month_avg_quantities = [(month, data["avg_metrics"]["avg_quantity"]) for month, data in months_comparison.items()]
        month_avg_quantities.sort(key=lambda x: x[1], reverse=True)
        
        top_months = [month for month, _ in month_avg_quantities[:3]]
        bottom_months = [month for month, _ in month_avg_quantities[-3:]]
        
        # Generate strategic insights
        insights = {
            "top_performing_months": top_months,
            "weak_performing_months": bottom_months,
            "months_with_inflation_impact": [month for month, data in months_comparison.items() if data["has_inflation_impact"]],
            "marketing_strategies": generate_monthly_marketing_strategies(top_months, bottom_months),
            "pricing_strategies": generate_monthly_pricing_strategies(months_comparison, top_months, bottom_months),
            "inventory_strategies": generate_monthly_inventory_strategies(top_months, bottom_months)
        }
        
        # Generate data for comparing monthly patterns across years
        yearly_patterns = {}
        years = df["year"].unique()
        
        for year in sorted(years):
            year_data = df[df["year"] == year]
            monthly_agg = year_data.groupby("month").agg({
                "total_quantity": "sum",
                "total_money_sold": "sum"
            }).reset_index()
            
            # Add month names
            monthly_agg["month_name"] = monthly_agg["month"].map(month_name_map)
            
            # Calculate average price
            monthly_agg["avg_price"] = monthly_agg["total_money_sold"] / monthly_agg["total_quantity"]
            
            # Format for response
            yearly_patterns[int(year)] = {
                "months": monthly_agg["month_name"].tolist(),
                "quantities": monthly_agg["total_quantity"].tolist(),
                "revenues": monthly_agg["total_money_sold"].tolist(),
                "avg_prices": monthly_agg["avg_price"].round(2).tolist()
            }
        
        return jsonify({
            "category": category,
            "months_comparison": months_comparison,
            "yearly_patterns": yearly_patterns,
            "strategic_insights": insights
        }), 200
        
    except Exception as e:
        print(f" Error in monthly performance comparison for {category}: {str(e)}")
        return jsonify({"error": str(e)}), 500

def generate_monthly_marketing_strategies(top_months, bottom_months):
    """Generate marketing strategies based on monthly performance patterns."""
    strategies = []
    
    # Strategies for top performing months
    if top_months:
        top_months_str = "، ".join(top_months)
        strategies.append({
            "title": f"استراتيجية تسويق لأشهر الذروة ({top_months_str})",
            "description": "تعظيم الاستفادة من فترات الطلب المرتفع",
            "tactics": [
                "زيادة الميزانية التسويقية خلال هذه الأشهر بنسبة 20-30%",
                "تنفيذ حملات إعلانية مكثفة قبل بداية هذه الأشهر بأسبوعين",
                "تنظيم فعاليات ترويجية خاصة خلال هذه الفترات",
                "استهداف العملاء السابقين بعروض خاصة لزيادة معدل التكرار",
                "توسيع نطاق الحملات التسويقية لاستهداف شرائح جديدة من العملاء"
            ]
        })
    
    # Strategies for bottom performing months
    if bottom_months:
        bottom_months_str = "، ".join(bottom_months)
        strategies.append({
            "title": f"استراتيجية تنشيط المبيعات خلال الأشهر الضعيفة ({bottom_months_str})",
            "description": "تحفيز الطلب خلال فترات الركود الموسمي",
            "tactics": [
                "تقديم عروض ترويجية حصرية خلال هذه الأشهر",
                "تطوير حملات تسويقية مبتكرة لجذب انتباه العملاء",
                "استهداف العملاء الدائمين بعروض خاصة لزيادة الولاء",
                "تنظيم فعاليات خاصة لجذب العملاء خلال فترات الركود",
                "اختبار فئات منتجات جديدة أو عروض مميزة لتنويع المبيعات"
            ]
        })
    
    # General year-round strategy
    strategies.append({
        "title": "استراتيجية تسويق متكاملة على مدار السنة",
        "description": "ضمان استمرارية التواصل التسويقي مع العملاء",
        "tactics": [
            "تطوير خطة تسويق سنوية مع تعديلات موسمية",
            "بناء قاعدة بيانات للعملاء وتطوير برامج ولاء",
            "تنفيذ استراتيجية تسويق محتوى مستمرة عبر وسائل التواصل الاجتماعي",
            "التركيز على بناء العلامة التجارية وتعزيز الصورة الذهنية",
            "قياس فعالية الحملات التسويقية باستمرار وتعديلها وفقاً للنتائج"
        ]
    })
    
    return strategies

def generate_monthly_pricing_strategies(months_comparison, top_months, bottom_months):
    """Generate pricing strategies based on monthly performance patterns."""
    strategies = []
    
    # Dynamic pricing strategy for high-demand months
    if top_months:
        top_months_str = "، ".join(top_months)
        strategies.append({
            "title": f"استراتيجية تسعير ديناميكية خلال أشهر الطلب المرتفع ({top_months_str})",
            "description": "الاستفادة من فترات الطلب المرتفع لتحسين الهوامش",
            "tactics": [
                "زيادة الأسعار بنسبة 10-15% خلال أشهر الذروة",
                "تقديم قيمة مضافة تبرر الزيادة في السعر",
                "تطوير باقات منتجات متكاملة بسعر مميز",
                "تقليل الخصومات خلال فترات الطلب المرتفع",
                "تقديم خدمات إضافية مميزة بدلاً من تخفيض الأسعار"
            ]
        })
    
    # Promotional pricing for low-demand months
    if bottom_months:
        bottom_months_str = "، ".join(bottom_months)
        strategies.append({
            "title": f"استراتيجية تسعير تحفيزية خلال الأشهر الضعيفة ({bottom_months_str})",
            "description": "تنشيط المبيعات خلال فترات الطلب المنخفض",
            "tactics": [
                "تقديم خصومات بنسبة 10-20% خلال الأشهر الضعيفة",
                "تطوير عروض تسعيرية خاصة (اشتر قطعة واحصل على الثانية بنصف السعر)",
                "تقديم خصومات تصاعدية مع زيادة كمية المشتريات",
                "إطلاق عروض تصفية نهاية الموسم بخصومات جذابة",
                "تقديم خيارات دفع مرنة أو تقسيط للمشتريات الكبيرة"
            ]
        })
    
    # Inflation response strategy
    months_with_inflation = [month for month, data in months_comparison.items() if data["has_inflation_impact"]]
    if months_with_inflation:
        months_str = "، ".join(months_with_inflation)
        strategies.append({
            "title": f"استراتيجية التسعير لمواجهة التضخم (تأثير ملحوظ في أشهر {months_str})",
            "description": "الحفاظ على حجم المبيعات مع مواكبة التضخم",
            "tactics": [
                "تطبيق زيادات سعرية تدريجية بدلاً من زيادة واحدة كبيرة",
                "تطوير منتجات بفئات سعرية متنوعة لمختلف شرائح العملاء",
                "تقديم خصومات استراتيجية على بعض المنتجات لزيادة حجم المبيعات",
                "تحسين كفاءة سلسلة التوريد للحد من تأثير ارتفاع التكاليف",
                "التركيز على إبراز القيمة المضافة للمنتجات لتبرير الأسعار"
            ]
        })
    
    # Value-based pricing strategy
    strategies.append({
        "title": "استراتيجية التسعير المبني على القيمة",
        "description": "تسعير المنتجات بناءً على القيمة المدركة وليس فقط التكلفة",
        "tactics": [
            "تحسين جودة المنتجات وتجربة العملاء لتبرير الأسعار",
            "تقديم ضمانات وخدمات ما بعد البيع",
            "تطوير تشكيلة منتجات متنوعة بمستويات جودة وأسعار مختلفة",
            "إعادة تصميم العبوات والتغليف لتعزيز القيمة المدركة",
            "استطلاع آراء العملاء بشكل مستمر لقياس تقبلهم للأسعار"
        ]
    })
    
    return strategies

def generate_monthly_inventory_strategies(top_months, bottom_months):
    """Generate inventory management strategies based on monthly performance patterns."""
    strategies = []
    
    # Stock management for peak months
    if top_months:
        top_months_str = "، ".join(top_months)
        strategies.append({
            "title": f"استراتيجية إدارة المخزون لأشهر الذروة ({top_months_str})",
            "description": "ضمان توفر المنتجات خلال فترات الطلب المرتفع",
            "tactics": [
                "زيادة مستويات المخزون قبل فترة الذروة بشهر على الأقل",
                "توسيع تشكيلة المنتجات خلال هذه الفترة",
                "تأمين خط إمداد مرن ومستمر خلال فترات الذروة",
                "تطوير نظام إنذار مبكر لانخفاض المخزون",
                "تدريب الفريق على إدارة المخزون خلال فترات الضغط"
            ]
        })
    
    # Stock optimization for slow months
    if bottom_months:
        bottom_months_str = "، ".join(bottom_months)
        strategies.append({
            "title": f"استراتيجية إدارة المخزون للأشهر الضعيفة ({bottom_months_str})",
            "description": "تقليل تكاليف التخزين وتجنب تكدس المخزون",
            "tactics": [
                "تخفيض مستويات المخزون خلال الأشهر الضعيفة",
                "التركيز على المنتجات الأساسية والأكثر مبيعاً",
                "تطوير برامج تصفية للمنتجات بطيئة الحركة",
                "جدولة عمليات الجرد وإعادة التنظيم خلال هذه الفترة",
                "الاستفادة من هذه الفترة لتجديد المخزون للموسم القادم"
            ]
        })
    
    # Year-round inventory management
    strategies.append({
        "title": "استراتيجية إدارة المخزون المتكاملة",
        "description": "تحسين كفاءة إدارة المخزون على مدار السنة",
        "tactics": [
            "تطبيق نظام تصنيف ABC للمنتجات لتحديد أولويات إدارة المخزون",
            "تحسين دقة توقعات الطلب باستخدام تحليل البيانات التاريخية",
            "تطوير شراكات مرنة مع الموردين للاستجابة السريعة للتغيرات",
            "أتمتة عمليات مراقبة المخزون وإعادة الطلب",
            "مراجعة وتحسين مستويات المخزون الاحتياطي بشكل دوري"
        ]
    })
    
    return strategies

@sales_strategy_bp.route('/seasonal-event-analysis/<category>', methods=['POST'])
def seasonal_event_analysis(category):
    """Analyze impact of seasonal events on sales and generate strategies."""
    try:
        init_db()
        data = request.get_json()
        
        # Get which seasonal events to analyze
        events = data.get('events', [])
        if not events:
            # Default events if none specified
            events = ["رمضان", "عيد الفطر", "عيد الأضحى", "العودة للمدارس", "الصيف", "الشتاء"]
        
        inflation_factor = data.get('inflation_factor', 30)  # Default inflation factor
        
        if not category:
            return jsonify({"error": "Category is required"}), 400
        
        # Fetch data for the category
        collection = get_collection("item_specification_monthly_demand")
        item_data = list(collection.find({"القسم": category}, {"_id": 0}))
        
        if not item_data:
            return jsonify({"error": f"No data found for category: {category}"}), 404
        
        # Convert to DataFrame
        df = pd.DataFrame(item_data)
        
        # Ensure numeric values
        df["total_quantity"] = pd.to_numeric(df["total_quantity"], errors="coerce")
        df["total_money_sold"] = pd.to_numeric(df["total_money_sold"], errors="coerce")
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["month"] = pd.to_numeric(df["month"], errors="coerce")
        
        # Define month names
        month_names = [
            'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
            'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
        ]
        
        # Map month numbers to names
        month_name_map = {i+1: name for i, name in enumerate(month_names)}
        
        # Define seasonal events mapping to months (approximate)
        seasonal_event_months = {
            "رمضان": [8, 9, 10],  # Approximate Hijri months in Gregorian
            "عيد الفطر": [9, 10],
            "عيد الأضحى": [11, 12],
            "العودة للمدارس": [8, 9],
            "الصيف": [6, 7, 8],
            "الشتاء": [12, 1, 2]
        }
        
        # Analyze each requested event
        event_analysis = []
        
        for event_name in events:
            if event_name not in seasonal_event_months:
                continue
                
            event_months = seasonal_event_months[event_name]
            
            # Filter data for this event's months
            event_data = df[df["month"].isin(event_months)]
            
            if event_data.empty:
                continue
                
            # Group by year
            yearly_event_data = event_data.groupby("year").agg({
                "total_quantity": "sum",
                "total_money_sold": "sum"
            }).reset_index()
            
            # Calculate average price
            yearly_event_data["avg_price"] = yearly_event_data["total_money_sold"] / yearly_event_data["total_quantity"]
            yearly_event_data["avg_price"] = yearly_event_data["avg_price"].round(2)
            
            # Calculate year-over-year growth
            yearly_event_data["quantity_growth"] = yearly_event_data["total_quantity"].pct_change() * 100
            yearly_event_data["revenue_growth"] = yearly_event_data["total_money_sold"].pct_change() * 100
            yearly_event_data["price_growth"] = yearly_event_data["avg_price"].pct_change() * 100
            
            # Prepare years data for response
            years_data = []
            for _, row in yearly_event_data.iterrows():
                year_data = {
                    "year": int(row["year"]),
                    "quantity": int(row["total_quantity"]),
                    "revenue": float(row["total_money_sold"]),
                    "avg_price": float(row["avg_price"])
                }
                
                # Add growth rates if available
                if not pd.isna(row["quantity_growth"]):
                    year_data["quantity_growth"] = float(row["quantity_growth"].round(1))
                if not pd.isna(row["revenue_growth"]):
                    year_data["revenue_growth"] = float(row["revenue_growth"].round(1))
                if not pd.isna(row["price_growth"]):
                    year_data["price_growth"] = float(row["price_growth"].round(1))
                
                years_data.append(year_data)
            
            # Determine event growth trend
            growth_trend = "stable"
            if len(years_data) >= 2:
                latest_year = years_data[-1]
                if "quantity_growth" in latest_year:
                    if latest_year["quantity_growth"] > 10:
                        growth_trend = "strong_growth"
                    elif latest_year["quantity_growth"] > 5:
                        growth_trend = "moderate_growth"
                    elif latest_year["quantity_growth"] < -10:
                        growth_trend = "strong_decline"
                    elif latest_year["quantity_growth"] < -5:
                        growth_trend = "moderate_decline"
            
            # Check for inflation impact
            has_inflation_impact = False
            if len(years_data) >= 2:
                latest_year = years_data[-1]
                if "price_growth" in latest_year and "quantity_growth" in latest_year:
                    if latest_year["price_growth"] > 5 and latest_year["quantity_growth"] < 0:
                        has_inflation_impact = True
            
            # Calculate event importance
            # Compare event performance with overall category performance
            event_avg_quantity = yearly_event_data["total_quantity"].mean()
            
            # Get overall category monthly average
            monthly_avg = df.groupby("month").agg({
                "total_quantity": "sum",
                "total_money_sold": "sum"
            }).reset_index()
            
            overall_monthly_avg_quantity = monthly_avg["total_quantity"].mean() * len(event_months)
            
            # Determine importance
            importance_ratio = event_avg_quantity / overall_monthly_avg_quantity if overall_monthly_avg_quantity > 0 else 0
            
            if importance_ratio > 1.5:
                importance = "مرتفعة جداً"
            elif importance_ratio > 1.2:
                importance = "مرتفعة"
            elif importance_ratio > 0.8:
                importance = "متوسطة"
            else:
                importance = "منخفضة"
            
            # Generate strategies based on event and category
            strategies = generate_event_specific_strategies(
                event_name, 
                category, 
                growth_trend, 
                has_inflation_impact,
                importance,
                inflation_factor
            )
            
            # Prepare month names
            event_month_names = [month_name_map[m] for m in event_months if m in month_name_map]
            
            # Create event analysis object
            event_analysis.append({
                "name": event_name,
                "months": event_month_names,
                "importance": importance,
                "growth_trend": growth_trend,
                "has_inflation_impact": has_inflation_impact,
                "yearly_performance": years_data,
                "strategies": strategies
            })
        
        # Generate comprehensive calendar for yearly planning
        event_calendar = generate_event_calendar(event_analysis, category)
        
        return jsonify({
            "category": category,
            "event_analysis": event_analysis,
            "event_calendar": event_calendar,
            "inflation_factor": inflation_factor
        }), 200
        
    except Exception as e:
        print(f" Error in seasonal event analysis for {category}: {str(e)}")
        return jsonify({"error": str(e)}), 500

def generate_event_specific_strategies(event_name, category, growth_trend, has_inflation_impact, importance, inflation_factor):
    """Generate strategies specific to each seasonal event based on analysis."""
    strategies = {
        "marketing": [],
        "pricing": [],
        "inventory": [],
        "general": []
    }
    
    # Base strategies by event type
    if event_name == "رمضان":
        strategies["marketing"] = [
            "تصميم حملات إعلانية تعكس روح شهر رمضان",
            "تكثيف الإعلانات خلال فترات المساء بعد الإفطار",
            "إطلاق حملات تسويق تفاعلية على منصات التواصل الاجتماعي",
            "توظيف عناصر رمضانية في الديكور وعرض المنتجات"
        ]
        
        strategies["pricing"] = [
            "تطوير باقات منتجات بأسعار خاصة لشهر رمضان",
            "تقديم خصومات للمشتريات بكميات كبيرة للعائلات",
            "تطبيق استراتيجية تسعير مختلفة للفترات المختلفة من اليوم"
        ]
        
        strategies["inventory"] = [
            "زيادة المخزون قبل شهر رمضان بثلاثة أسابيع",
            "تعديل ساعات تجديد المخزون لتتناسب مع أنماط التسوق الرمضانية",
            "توفير تشكيلة متنوعة من المنتجات المناسبة للموسم"
        ]
    
    elif event_name in ["عيد الفطر", "عيد الأضحى"]:
        strategies["marketing"] = [
            "إطلاق حملة ترويجية قبل العيد بثلاثة أسابيع",
            "تصميم عروض هدايا مميزة مع تغليف خاص للعيد",
            "تنفيذ استراتيجية تسويق متكاملة عبر القنوات المختلفة",
            "تعزيز تجربة العملاء من خلال أجواء احتفالية في نقاط البيع"]
        
        strategies["pricing"] = [
            "تطبيق أسعار خاصة لمنتجات العيد مع التركيز على جودة المنتج",
            "تقديم خصومات تصاعدية مع زيادة قيمة المشتريات",
            "تقديم عروض خاصة على مجموعات المنتجات المتكاملة"
        ]
        
        strategies["inventory"] = [
            "زيادة المخزون قبل العيد بثلاثة أسابيع على الأقل",
            "توفير مخزون إضافي للمنتجات الأكثر طلباً خلال العيد",
            "تحضير مواد تغليف خاصة بالعيد مسبقاً",
            "وضع خطة طوارئ لإعادة التزويد السريع للمنتجات الأكثر طلباً"
        ]
    
    elif event_name == "العودة للمدارس":
        if category.lower() in ["مدارس", "اطفال"]:
            strategies["marketing"] = [
                "إطلاق حملة 'العودة للمدرسة' قبل بداية العام الدراسي بشهر",
                "تقديم عروض خاصة للمشتريات العائلية أو للمدارس",
                "الترويج لمنتجات متكاملة كحزم متكاملة بسعر مميز",
                "تنظيم فعاليات خاصة بالعودة للمدارس في نقاط البيع"
            ]
            
            strategies["pricing"] = [
                "تقديم خصومات تصاعدية على مشتريات العودة للمدارس كلما زادت الكمية",
                "عروض خاصة للمدارس والمشتريات الجماعية",
                "تطوير باقات منتجات متكاملة بسعر موحد مخفض"
            ]
            
            strategies["inventory"] = [
                "تحضير مخزون متنوع من المنتجات المدرسية قبل بداية العام الدراسي بشهرين",
                "تنظيم المخزون وفقاً للفئات العمرية والمراحل الدراسية",
                "وضع خطة لإدارة المخزون أثناء فترة الذروة قبل بداية العام الدراسي"
            ]
        else:
            strategies["marketing"] = [
                "الاستفادة من موسم العودة للمدارس لجذب العائلات",
                "تطوير عروض مشتركة مع منتجات مدرسية",
                "زيادة الحملات الإعلانية خلال فترة التحضير للمدارس"
            ]
            
            strategies["pricing"] = [
                "تقديم خصومات خاصة للعائلات خلال فترة العودة للمدارس",
                "تطوير عروض متكاملة تشمل منتجات متنوعة بسعر مخفض"
            ]
            
            strategies["inventory"] = [
                "زيادة مخزون المنتجات التي تستهدف العائلات خلال هذه الفترة",
                "التركيز على المنتجات المكملة للاحتياجات المدرسية"
            ]
    
    elif event_name == "الصيف":
        if category in ["احذية حريمي", "احذية رجالي", "احذية اطفال"]:
            strategies["marketing"] = [
                "تقديم تشكيلة متنوعة من الأحذية الصيفية",
                "إبراز الميزات المناسبة للطقس الحار في الحملات الترويجية",
                "تنظيم حملات خاصة لبداية موسم الصيف"
            ]
        elif category in ["حريمي", "رجالي", "اطفال"]:
            strategies["marketing"] = [
                "التركيز على الملابس الخفيفة والألوان الفاتحة",
                "تقديم عروض خاصة للعطلات الصيفية",
                "تطوير حملات تستهدف السفر والعطلات"
            ]
        else:
            strategies["marketing"] = [
                "تطوير حملات تناسب أجواء الصيف",
                "تقديم عروض مناسبة للأنشطة الصيفية",
                "استهداف المستهلكين خلال فترة الإجازات الصيفية"
            ]
        
        strategies["pricing"] = [
            "تعديل الأسعار بما يتناسب مع الطلب المتزايد على المنتجات الصيفية",
            "تقديم عروض خاصة على مجموعات المنتجات الصيفية"
        ]
        
        strategies["inventory"] = [
            "زيادة مخزون المنتجات الصيفية قبل بداية الموسم",
            "التنويع في تشكيلة المنتجات الصيفية لتلبية مختلف الاحتياجات",
            "وضع خطة لتصفية المخزون المتبقي في نهاية الموسم"
        ]
    
    elif event_name == "الشتاء":
        if category in ["حريمي", "رجالي", "اطفال"]:
            strategies["marketing"] = [
                "توفير تشكيلة متنوعة من الملابس الشتوية",
                "تسليط الضوء على الدفء والراحة في الحملات الترويجية",
                "تطوير عروض خاصة لبداية موسم الشتاء"
            ]
            
            strategies["pricing"] = [
                "عروض على المعاطف والملابس الثقيلة",
                "تقديم خصومات على المشتريات المتعددة من الملابس الشتوية",
                "تطوير استراتيجية تسعير للمنتجات الموسمية الشتوية"
            ]
            
            strategies["inventory"] = [
                "الاستعداد المبكر بتجهيز مخزون الشتاء قبل بداية الموسم",
                "توفير مجموعة متنوعة من المقاسات والألوان",
                "وضع خطة لإدارة المخزون في نهاية الموسم"
            ]
        else:
            strategies["marketing"] = [
                "تطوير حملات تسويقية مناسبة لأجواء الشتاء",
                "تقديم عروض تناسب احتياجات المستهلكين في الطقس البارد",
                "استهداف المناسبات والاحتفالات الشتوية"
            ]
            
            strategies["pricing"] = [
                "تعديل الأسعار بما يتناسب مع الطلب المتغير في فصل الشتاء",
                "تقديم عروض خاصة على المنتجات المناسبة للشتاء"
            ]
            
            strategies["inventory"] = [
                "زيادة مخزون المنتجات المناسبة للطقس البارد",
                "التركيز على المنتجات الأكثر طلباً خلال فصل الشتاء"
            ]
    
    # Adjust strategies based on growth trend
    if growth_trend == "strong_growth":
        strategies["general"].append(f"الاستثمار بشكل أكبر في موسم {event_name} نظراً للنمو القوي")
        strategies["pricing"].append("الاستفادة من النمو القوي لتحسين هوامش الربح")
        strategies["inventory"].append("توفير مخزون أكبر لتلبية الطلب المتزايد")
    
    elif growth_trend == "moderate_growth":
        strategies["general"].append(f"تعزيز النمو في موسم {event_name} من خلال استراتيجيات تسويقية مبتكرة")
        strategies["pricing"].append("الحفاظ على توازن السعر والقيمة مع النمو المعتدل")
    
    elif growth_trend == "strong_decline":
        strategies["general"].append(f"تطوير استراتيجية إنعاش لموسم {event_name} لمعالجة الانخفاض الحاد")
        strategies["pricing"].append("تقديم عروض سعرية جذابة لوقف الانخفاض في المبيعات")
        strategies["marketing"].append("إعادة تقييم وتجديد الاستراتيجية التسويقية")
    
    elif growth_trend == "moderate_decline":
        strategies["general"].append(f"مراجعة وتحسين استراتيجية موسم {event_name} لعكس اتجاه الانخفاض")
        strategies["pricing"].append("مراجعة هيكل الأسعار ومقارنته بالمنافسين")
    
    # Adjust for inflation impact
    if has_inflation_impact:
        strategies["general"].append("تطوير استراتيجية متكاملة لمواجهة تأثير التضخم على المبيعات")
        strategies["pricing"].extend([
            "تطبيق زيادات سعرية تدريجية بدلاً من زيادة واحدة كبيرة",
            "تطوير منتجات بفئات سعرية متنوعة لتلبية احتياجات مختلف العملاء",
            f"تعديل الأسعار بما يتناسب مع معدل التضخم السنوي ({inflation_factor}%)"
        ])
        strategies["marketing"].append("التركيز على القيمة المضافة للمنتجات في الحملات التسويقية لتبرير الأسعار")
        strategies["inventory"].append("تحسين كفاءة سلسلة التوريد للحد من تأثير ارتفاع التكاليف")
    
    # Adjust based on importance
    if importance == "مرتفعة جداً":
        strategies["general"].extend([
            f"جعل موسم {event_name} أولوية قصوى في استراتيجية المبيعات السنوية",
            "تخصيص ميزانية تسويقية أكبر لهذا الموسم",
            "تدريب الفريق بشكل خاص على التعامل مع هذا الموسم"
        ])
    elif importance == "مرتفعة":
        strategies["general"].append(f"إعطاء اهتمام خاص لموسم {event_name} في خطة المبيعات السنوية")
    
    return strategies

def generate_event_calendar(event_analysis, category):
    """Generate a yearly calendar with key events and strategic actions."""
    calendar = []
    
    # Define months and seasons
    months = [
        'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
        'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
    ]
    
    # Create a monthly framework
    for i, month in enumerate(months):
        month_data = {
            "month": month,
            "month_number": i + 1,
            "events": [],
            "actions": {
                "marketing": [],
                "pricing": [],
                "inventory": []
            }
        }
        
        # Add events for this month
        for event in event_analysis:
            if month in event["months"]:
                month_data["events"].append({
                    "name": event["name"],
                    "importance": event["importance"]
                })
                
                # Add relevant strategies for this event
                if "strategies" in event:
                    # Add marketing strategies
                    if "marketing" in event["strategies"]:
                        month_data["actions"]["marketing"].extend(event["strategies"]["marketing"])
                    
                    # Add pricing strategies
                    if "pricing" in event["strategies"]:
                        month_data["actions"]["pricing"].extend(event["strategies"]["pricing"])
                    
                    # Add inventory strategies
                    if "inventory" in event["strategies"]:
                        month_data["actions"]["inventory"].extend(event["strategies"]["inventory"])
        
        # Add preparation actions for upcoming events
        for event in event_analysis:
            # Check if this event happens in the next 1-2 months
            event_months = [months.index(m) for m in event["months"]]
            
            # Consider circular month calculation (December -> January)
            next_months = [(i + 1) % 12, (i + 2) % 12]
            
            if any(m in event_months for m in next_months):
                # Add preparation actions
                month_data["actions"]["marketing"].append(f"البدء بالتخطيط للحملات التسويقية لموسم {event['name']}")
                month_data["actions"]["inventory"].append(f"بدء تجهيز المخزون لموسم {event['name']}")
        
        # Add seasonal category-specific actions
        if category in ["حريمي", "رجالي", "اطفال", "احذية حريمي", "احذية رجالي", "احذية اطفال"]:
            # Winter season preparation (October-November)
            if month in ["أكتوبر", "نوفمبر"]:
                month_data["actions"]["inventory"].append("تجهيز المخزون لموسم الشتاء")
                month_data["actions"]["marketing"].append("تطوير حملات تسويقية للمنتجات الشتوية")
            
            # Summer season preparation (March-April)
            elif month in ["مارس", "أبريل"]:
                month_data["actions"]["inventory"].append("تجهيز المخزون لموسم الصيف")
                month_data["actions"]["marketing"].append("تطوير حملات تسويقية للمنتجات الصيفية")
            
            # End of season sales (February, August)
            elif month in ["فبراير"]:
                month_data["actions"]["pricing"].append("تصفية المنتجات الشتوية مع نهاية الموسم")
            elif month in ["أغسطس"]:
                month_data["actions"]["pricing"].append("تصفية المنتجات الصيفية مع نهاية الموسم")
        
        # Back to school specific actions
        if category in ["مدارس", "اطفال"]:
            if month in ["يوليو", "أغسطس"]:
                month_data["actions"]["marketing"].append("تكثيف حملات العودة للمدارس")
                month_data["actions"]["inventory"].append("ضمان توفر كافة المقاسات والتشكيلات المدرسية")
        
        # Remove duplicates in actions
        for action_type in month_data["actions"]:
            month_data["actions"][action_type] = list(set(month_data["actions"][action_type]))
        
        calendar.append(month_data)
    
    return calendar

@sales_strategy_bp.route('/inflation-impact-analysis/<category>', methods=['POST'])
def analyze_inflation_impact(category):
    """Analyze the impact of inflation on sales and generate mitigation strategies."""
    try:
        init_db()
        data = request.get_json()
        
        inflation_factor = data.get('inflation_factor', 30)  # Default inflation factor
        
        if not category:
            return jsonify({"error": "Category is required"}), 400
        
        # Fetch data for the category
        collection = get_collection("item_specification_monthly_demand")
        item_data = list(collection.find({"القسم": category}, {"_id": 0}))
        
        if not item_data:
            return jsonify({"error": f"No data found for category: {category}"}), 404
        
        # Convert to DataFrame
        df = pd.DataFrame(item_data)
        
        # Ensure numeric values
        df["total_quantity"] = pd.to_numeric(df["total_quantity"], errors="coerce")
        df["total_money_sold"] = pd.to_numeric(df["total_money_sold"], errors="coerce")
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["month"] = pd.to_numeric(df["month"], errors="coerce")
        
        # Calculate yearly aggregates
        yearly_agg = df.groupby("year").agg({
            "total_quantity": "sum",
            "total_money_sold": "sum"
        }).reset_index()
        
        # Calculate average unit price
        yearly_agg["avg_price"] = yearly_agg["total_money_sold"] / yearly_agg["total_quantity"]
        yearly_agg["avg_price"] = yearly_agg["avg_price"].fillna(0).round(2)
        
        # Calculate year-over-year growth rates
        yearly_agg["quantity_growth"] = yearly_agg["total_quantity"].pct_change() * 100
        yearly_agg["revenue_growth"] = yearly_agg["total_money_sold"].pct_change() * 100
        yearly_agg["price_growth"] = yearly_agg["avg_price"].pct_change() * 100
        
        # Format data for response
        yearly_data = []
        for _, row in yearly_agg.iterrows():
            year_data = {
                "year": int(row["year"]),
                "quantity": int(row["total_quantity"]),
                "revenue": float(row["total_money_sold"]),
                "avg_price": float(row["avg_price"])
            }
            
            # Add growth rates if available
            if not pd.isna(row["quantity_growth"]):
                year_data["quantity_growth"] = float(row["quantity_growth"].round(1))
            if not pd.isna(row["revenue_growth"]):
                year_data["revenue_growth"] = float(row["revenue_growth"].round(1))
            if not pd.isna(row["price_growth"]):
                year_data["price_growth"] = float(row["price_growth"].round(1))
            
            yearly_data.append(year_data)
        
        # Check for inflation impact
        inflation_impact = {
            "detected": False,
            "years_affected": [],
            "severity": "none"
        }
        
        for year_data in yearly_data:
            if "price_growth" in year_data and "quantity_growth" in year_data:
                if year_data["price_growth"] > 5 and year_data["quantity_growth"] < 0:
                    inflation_impact["detected"] = True
                    inflation_impact["years_affected"].append(year_data["year"])
                    
                    # Determine severity
                    if year_data["quantity_growth"] < -15:
                        severity = "high"
                    elif year_data["quantity_growth"] < -10:
                        severity = "medium-high"
                    elif year_data["quantity_growth"] < -5:
                        severity = "medium"
                    else:
                        severity = "low"
                    
                    # Update overall severity to highest detected
                    if severity == "high" or inflation_impact["severity"] == "none":
                        inflation_impact["severity"] = severity
                    elif severity == "medium-high" and inflation_impact["severity"] not in ["high"]:
                        inflation_impact["severity"] = severity
                    elif severity == "medium" and inflation_impact["severity"] not in ["high", "medium-high"]:
                        inflation_impact["severity"] = severity
        
        # Calculate monthly impact to identify which months are most affected
        monthly_impact = []
        
        if inflation_impact["detected"]:
            # Define month names
            month_names = [
                'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
            ]
            
            # Map month numbers to names
            month_name_map = {i+1: name for i, name in enumerate(month_names)}
            
            for month in range(1, 13):
                month_data = df[df["month"] == month]
                
                if month_data.empty:
                    continue
                    
                # Group by year
                monthly_yearly = month_data.groupby("year").agg({
                    "total_quantity": "sum",
                    "total_money_sold": "sum"
                }).reset_index()
                
                # Calculate average price
                monthly_yearly["avg_price"] = monthly_yearly["total_money_sold"] / monthly_yearly["total_quantity"]
                monthly_yearly["avg_price"] = monthly_yearly["avg_price"].fillna(0).round(2)
                
                # Check the last two years for inflation impact
                if len(monthly_yearly) >= 2:
                    last_two_years = monthly_yearly.tail(2).copy()
                    last_two_years = last_two_years.sort_values("year")
                    
                    # Calculate changes
                    prev_year = last_two_years.iloc[0]
                    curr_year = last_two_years.iloc[1]
                    
                    quantity_change = ((curr_year["total_quantity"] - prev_year["total_quantity"]) / prev_year["total_quantity"]) * 100
                    price_change = ((curr_year["avg_price"] - prev_year["avg_price"]) / prev_year["avg_price"]) * 100
                    
                    # Check for inflation impact
                    if price_change > 5 and quantity_change < 0:
                        monthly_impact.append({
                            "month": month_name_map[month],
                            "month_number": month,
                            "price_increase": float(price_change.round(1)),
                            "quantity_decrease": float(abs(quantity_change.round(1))),
                            "year": int(curr_year["year"]),
                            "severity": "high" if quantity_change < -15 else "medium" if quantity_change < -10 else "low"
                        })
        
        # Sort monthly impact by severity
        monthly_impact.sort(key=lambda x: (0 if x["severity"] == "high" else 1 if x["severity"] == "medium" else 2, -x["quantity_decrease"]))
        
        # Generate mitigation strategies
        strategies = generate_inflation_mitigation_strategies(
            inflation_impact, 
            monthly_impact, 
            inflation_factor, 
            category
        )
        
        # Generate price elasticity estimates
        price_elasticity = estimate_price_elasticity(yearly_data)
        
        # Forecast impact of different pricing strategies
        pricing_scenarios = forecast_pricing_scenarios(
            yearly_data, 
            inflation_factor, 
            price_elasticity
        )
        
        return jsonify({
            "category": category,
            "yearly_data": yearly_data,
            "inflation_impact": inflation_impact,
            "monthly_impact": monthly_impact,
            "inflation_factor": inflation_factor,
            "price_elasticity": price_elasticity,
            "mitigation_strategies": strategies,
            "pricing_scenarios": pricing_scenarios
        }), 200
        
    except Exception as e:
        print(f" Error in inflation impact analysis for {category}: {str(e)}")
        return jsonify({"error": str(e)}), 500

def generate_inflation_mitigation_strategies(inflation_impact, monthly_impact, inflation_factor, category):
    """Generate strategies to mitigate the impact of inflation on sales."""
    strategies = {
        "pricing": [],
        "marketing": [],
        "product": [],
        "operational": []
    }
    
    # Base strategies for inflation mitigation
    strategies["pricing"] = [
        "تطبيق زيادات سعرية تدريجية بدلاً من زيادة واحدة كبيرة",
        "تطوير منتجات بفئات سعرية متنوعة لتلبية احتياجات مختلف العملاء",
        "تقديم قيمة مضافة للعملاء لتبرير الزيادة في الأسعار"
    ]
    
    strategies["marketing"] = [
        "التركيز على إبراز القيمة المضافة للمنتجات في الحملات التسويقية",
        "تعزيز التواصل مع العملاء لشرح أسباب تغييرات الأسعار",
        "تطوير برامج ولاء لتشجيع العملاء على الشراء المتكرر"
    ]
    
    strategies["product"] = [
        "تحسين جودة المنتجات لتبرير الأسعار المرتفعة",
        "تطوير تشكيلة منتجات بأحجام وأسعار مختلفة",
        "التركيز على المنتجات ذات هامش الربح الأعلى"
    ]
    
    strategies["operational"] = [
        "تحسين كفاءة سلسلة التوريد لتقليل التكاليف",
        "تبسيط عمليات الإنتاج والتوزيع لخفض النفقات التشغيلية",
        "تطوير شراكات استراتيجية مع الموردين للحصول على أسعار أفضل"
    ]
    
    # Add strategies based on severity
    if inflation_impact["detected"]:
        if inflation_impact["severity"] in ["high", "medium-high"]:
            strategies["pricing"].extend([
                "إعادة تقييم هيكل الأسعار بشكل شامل",
                "تطبيق استراتيجية تسعير مرنة تستجيب للتغيرات في السوق",
                "تخفيض هوامش الربح مؤقتاً على بعض المنتجات الاستراتيجية للحفاظ على حجم المبيعات"
            ])
            
            strategies["marketing"].extend([
                "تطوير حملات تسويقية تركز على الجودة والقيمة بدلاً من السعر",
                "تقديم ضمانات وخدمات إضافية لتعزيز القيمة المدركة للمنتجات"
            ])
            
            strategies["product"].extend([
                "إعادة تصميم المنتجات لخفض تكاليف الإنتاج مع الحفاظ على الجودة",
                "تطوير منتجات جديدة بتكلفة أقل وأسعار تنافسية"
            ])
            
            strategies["operational"].extend([
                "تطوير استراتيجية تحوط ضد تقلبات أسعار المواد الخام",
                "الاستثمار في التكنولوجيا لزيادة الكفاءة وخفض التكاليف التشغيلية"
            ])
        
        # Add strategies for most affected months
        if monthly_impact:
            affected_months = [m["month"] for m in monthly_impact]
            months_str = "، ".join(affected_months[:3] if len(affected_months) > 3 else affected_months)
            
            strategies["pricing"].append(f"تطوير استراتيجية تسعير خاصة لأشهر {months_str} الأكثر تأثراً بالتضخم")
            strategies["marketing"].append(f"تكثيف الحملات الترويجية خلال أشهر {months_str} لتحفيز الطلب")
    
    # Add category-specific strategies
    if category in ["حريمي", "رجالي", "اطفال"]:
        strategies["product"].append("تطوير خطوط إنتاج بأسعار متنوعة للملابس")
        strategies["pricing"].append("تقديم عروض على المنتجات الأساسية مع زيادة هوامش الربح على الإكسسوارات والمنتجات المكملة")
    
    elif category in ["احذية حريمي", "احذية رجالي", "احذية اطفال"]:
        strategies["marketing"].append("التركيز على الجودة والمتانة كميزة تنافسية لتبرير الأسعار")
        strategies["product"].append("تطوير تشكيلة من الأحذية ذات التصاميم التقليدية التي لا تتأثر بالموضة")
    
    elif category == "مدارس":
        strategies["pricing"].append("تقديم باقات مدرسية متكاملة بأسعار تنافسية")
        strategies["marketing"].append("التركيز على عروض بداية العام الدراسي المبكرة للتغلب على تأثير التضخم")
    return strategies

def estimate_price_elasticity(yearly_data):
    """Estimate price elasticity of demand based on historical data."""
    elasticity_estimates = []
    
    # Need at least two years of data to calculate elasticity
    if len(yearly_data) < 2:
        return {
            "elasticity": -0.5,  # Default assumption
            "confidence": "low",
            "explanation": "غير كافي. بيانات أقل من سنتين."
        }
    
    # Calculate elasticity for each pair of consecutive years
    for i in range(1, len(yearly_data)):
        current_year = yearly_data[i]
        previous_year = yearly_data[i-1]
        
        # Check if we have the necessary data
        if ("quantity_growth" in current_year and 
            "price_growth" in current_year and 
            current_year["price_growth"] != 0):
            
            # Calculate price elasticity: % change in quantity / % change in price
            elasticity = current_year["quantity_growth"] / current_year["price_growth"]
            
            elasticity_estimates.append({
                "year": current_year["year"],
                "elasticity": elasticity,
                "price_change": current_year["price_growth"],
                "quantity_change": current_year["quantity_growth"]
            })
    
    if not elasticity_estimates:
        return {
            "elasticity": -0.5,  # Default assumption
            "confidence": "low",
            "explanation": "لا يمكن حساب المرونة. بيانات غير كافية أو متناقضة."
        }
    
    # Calculate average elasticity
    avg_elasticity = sum(e["elasticity"] for e in elasticity_estimates) / len(elasticity_estimates)
    
    # Determine confidence level
    if len(elasticity_estimates) >= 3:
        confidence = "high"
    elif len(elasticity_estimates) == 2:
        confidence = "medium"
    else:
        confidence = "low"
    
    # Check consistency of elasticity values
    elasticity_values = [e["elasticity"] for e in elasticity_estimates]
    elasticity_range = max(elasticity_values) - min(elasticity_values)
    
    if elasticity_range > 1:
        confidence = "low"
        explanation = "تقدير منخفض الثقة بسبب تباين كبير في قيم المرونة."
    elif avg_elasticity > 0:
        explanation = "سلوك غير اعتيادي: زيادة الأسعار تؤدي إلى زيادة الطلب. قد يشير إلى تأثير عوامل أخرى."
        avg_elasticity = -0.5  # Use default assumption in this case
    else:
        if avg_elasticity > -0.5:
            explanation = "مرونة منخفضة: الطلب لا يتأثر كثيراً بتغيرات الأسعار."
        elif avg_elasticity > -1:
            explanation = "مرونة معتدلة: الطلب يتأثر بتغيرات الأسعار لكن ليس بشكل كبير."
        else:
            explanation = "مرونة عالية: الطلب يتأثر بشكل كبير بتغيرات الأسعار."
    
    return {
        "elasticity": round(avg_elasticity, 2),
        "confidence": confidence,
        "explanation": explanation,
        "yearly_estimates": elasticity_estimates
    }

def forecast_pricing_scenarios(yearly_data, inflation_factor, price_elasticity):
    """Generate forecast scenarios based on different pricing strategies."""
    # Ensure we have data to work with
    if not yearly_data or len(yearly_data) < 1:
        return []
    
    # Use the most recent year as base
    latest_year = max(yearly_data, key=lambda x: x["year"])
    base_quantity = latest_year["quantity"]
    base_revenue = latest_year["revenue"]
    base_price = latest_year["avg_price"]
    
    # Get elasticity value
    elasticity = price_elasticity["elasticity"]
    
    # Generate scenarios
    scenarios = []
    
    # Scenario 1: Full inflation pass-through (price increase = inflation)
    price_increase_pct = inflation_factor
    quantity_change_pct = elasticity * price_increase_pct
    
    new_price = base_price * (1 + price_increase_pct/100)
    new_quantity = base_quantity * (1 + quantity_change_pct/100)
    new_revenue = new_price * new_quantity
    
    scenarios.append({
        "name": "تمرير التضخم كاملاً",
        "description": f"زيادة الأسعار بنسبة {inflation_factor}% لتغطية التضخم بالكامل",
        "price_change": round(price_increase_pct, 1),
        "quantity_change": round(quantity_change_pct, 1),
        "revenue_change": round(((new_revenue - base_revenue) / base_revenue) * 100, 1),
        "new_price": round(new_price, 2),
        "new_quantity": round(new_quantity),
        "new_revenue": round(new_revenue),
        "profit_impact": "محافظة على هوامش الربح مع انخفاض الكميات",
        "recommended_for": "المنتجات ذات المرونة المنخفضة أو المنتجات الفاخرة"
    })
    
    # Scenario 2: Partial inflation pass-through (price increase = 70% of inflation)
    price_increase_pct = inflation_factor * 0.7
    quantity_change_pct = elasticity * price_increase_pct
    
    new_price = base_price * (1 + price_increase_pct/100)
    new_quantity = base_quantity * (1 + quantity_change_pct/100)
    new_revenue = new_price * new_quantity
    
    scenarios.append({
        "name": "تمرير جزئي للتضخم",
        "description": f"زيادة الأسعار بنسبة {round(price_increase_pct, 1)}% (70% من التضخم)",
        "price_change": round(price_increase_pct, 1),
        "quantity_change": round(quantity_change_pct, 1),
        "revenue_change": round(((new_revenue - base_revenue) / base_revenue) * 100, 1),
        "new_price": round(new_price, 2),
        "new_quantity": round(new_quantity),
        "new_revenue": round(new_revenue),
        "profit_impact": "انخفاض طفيف في هوامش الربح مع انخفاض أقل في الكميات",
        "recommended_for": "معظم المنتجات الاستهلاكية العادية"
    })
    
    # Scenario 3: Minimal price increase (price increase = 50% of inflation)
    price_increase_pct = inflation_factor * 0.5
    quantity_change_pct = elasticity * price_increase_pct
    
    new_price = base_price * (1 + price_increase_pct/100)
    new_quantity = base_quantity * (1 + quantity_change_pct/100)
    new_revenue = new_price * new_quantity
    
    scenarios.append({
        "name": "زيادة سعرية محدودة",
        "description": f"زيادة الأسعار بنسبة {round(price_increase_pct, 1)}% (50% من التضخم)",
        "price_change": round(price_increase_pct, 1),
        "quantity_change": round(quantity_change_pct, 1),
        "revenue_change": round(((new_revenue - base_revenue) / base_revenue) * 100, 1),
        "new_price": round(new_price, 2),
        "new_quantity": round(new_quantity),
        "new_revenue": round(new_revenue),
        "profit_impact": "انخفاض معتدل في هوامش الربح مع الحفاظ على حجم المبيعات",
        "recommended_for": "المنتجات الأساسية والمنتجات ذات المنافسة العالية"
    })
    
    # Scenario 4: Price maintenance (no price increase)
    price_increase_pct = 0
    quantity_change_pct = 0  # No price change = no quantity effect
    
    new_price = base_price
    new_quantity = base_quantity
    new_revenue = new_price * new_quantity
    
    scenarios.append({
        "name": "تثبيت الأسعار",
        "description": "الحفاظ على الأسعار الحالية دون زيادة",
        "price_change": 0,
        "quantity_change": 0,
        "revenue_change": 0,
        "new_price": round(new_price, 2),
        "new_quantity": round(new_quantity),
        "new_revenue": round(new_revenue),
        "profit_impact": "انخفاض كبير في هوامش الربح مع الحفاظ على حجم المبيعات",
        "recommended_for": "المنتجات شديدة المنافسة أو للحفاظ على الحصة السوقية"
    })
    
    # Scenario 5: Strategic price decrease (10% price decrease to stimulate demand)
    price_increase_pct = -10
    quantity_change_pct = elasticity * price_increase_pct  # Note: This will be positive as elasticity is negative
    
    new_price = base_price * (1 + price_increase_pct/100)
    new_quantity = base_quantity * (1 + quantity_change_pct/100)
    new_revenue = new_price * new_quantity
    
    scenarios.append({
        "name": "تخفيض استراتيجي للأسعار",
        "description": "تخفيض الأسعار بنسبة 10% لتحفيز الطلب",
        "price_change": price_increase_pct,
        "quantity_change": round(quantity_change_pct, 1),
        "revenue_change": round(((new_revenue - base_revenue) / base_revenue) * 100, 1),
        "new_price": round(new_price, 2),
        "new_quantity": round(new_quantity),
        "new_revenue": round(new_revenue),
        "profit_impact": "انخفاض كبير في هوامش الربح مع زيادة كبيرة في الكميات",
        "recommended_for": "المنتجات ذات المرونة العالية أو لزيادة الحصة السوقية"
    })
    
    # Sort scenarios by revenue impact
    scenarios.sort(key=lambda x: x["revenue_change"], reverse=True)
    
    # Identify recommended scenario based on elasticity
    if elasticity > -0.5:  # Low elasticity (inelastic demand)
        recommended_scenario = "تمرير التضخم كاملاً"
    elif elasticity > -1.0:  # Moderate elasticity
        recommended_scenario = "تمرير جزئي للتضخم"
    else:  # High elasticity (elastic demand)
        recommended_scenario = "زيادة سعرية محدودة"
    
    # Add recommendation to response
    for scenario in scenarios:
        if scenario["name"] == recommended_scenario:
            scenario["recommended"] = True
        else:
            scenario["recommended"] = False
    
    return scenarios

@sales_strategy_bp.route('/comprehensive-strategy/<category>', methods=['POST'])
def comprehensive_strategy(category):
    """Generate a comprehensive business strategy based on all analyses."""
    try:
        init_db()
        data = request.get_json()
        
        inflation_factor = data.get('inflation_factor', 30)  # Default inflation factor
        analysis_notes = data.get('analysis_notes', '')
        
        if not category:
            return jsonify({"error": "Category is required"}), 400
        
        # Fetch data for the category
        collection = get_collection("item_specification_monthly_demand")
        item_data = list(collection.find({"القسم": category}, {"_id": 0}))
        
        if not item_data:
            return jsonify({"error": f"No data found for category: {category}"}), 404
        
        # Convert to DataFrame
        df = pd.DataFrame(item_data)
        
        # Ensure numeric values
        df["total_quantity"] = pd.to_numeric(df["total_quantity"], errors="coerce")
        df["total_money_sold"] = pd.to_numeric(df["total_money_sold"], errors="coerce")
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["month"] = pd.to_numeric(df["month"], errors="coerce")
        
        # Process the sales data
        strategy_data = process_sales_data(df, category, inflation_factor, analysis_notes)
        
        # Enhance with additional analyses
        
        # 1. Monthly performance comparison across years
        monthly_comparison = run_monthly_comparison(df, category)
        
        # 2. Cross-year seasonal comparison
        seasonal_comparison = run_seasonal_comparison(df, category)
        
        # 3. Inflation impact analysis
        inflation_analysis = run_inflation_analysis(df, category, inflation_factor)
        
        # 4. Generate comprehensive strategic recommendations
        strategic_recommendations = generate_comprehensive_recommendations(
            strategy_data, 
            monthly_comparison, 
            seasonal_comparison, 
            inflation_analysis,
            category,
            inflation_factor,
            analysis_notes
        )
        
        # Combine all analyses into a single response
        comprehensive_response = {
            "category": category,
            "summary": strategy_data,
            "monthly_comparison": monthly_comparison,
            "seasonal_comparison": seasonal_comparison,
            "inflation_analysis": inflation_analysis,
            "strategic_recommendations": strategic_recommendations,
            "inflation_factor": inflation_factor,
            "analysis_notes": analysis_notes
        }
        
        return jsonify(comprehensive_response), 200
        
    except Exception as e:
        print(f" Error generating comprehensive strategy for {category}: {str(e)}")
        return jsonify({"error": str(e)}), 500

def run_monthly_comparison(df, category):
    """Run monthly performance comparison analysis."""
    # Define month names
    month_names = [
        'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
        'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
    ]
    
    # Create month name mapping
    month_name_map = {i+1: name for i, name in enumerate(month_names)}
    
    # Group by month and year
    monthly_yearly = df.groupby(["month", "year"]).agg({
        "total_quantity": "sum",
        "total_money_sold": "sum"
    }).reset_index()
    
    # Calculate unit price
    monthly_yearly["unit_price"] = monthly_yearly["total_money_sold"] / monthly_yearly["total_quantity"]
    monthly_yearly["unit_price"] = monthly_yearly["unit_price"].fillna(0).round(2)
    
    # Format response for all months
    months_comparison = {}
    
    for month in range(1, 13):
        month_data = monthly_yearly[monthly_yearly["month"] == month]
        
        if month_data.empty:
            continue
            
        # Sort by year
        month_data = month_data.sort_values("year")
        
        # Calculate year-over-year growth rates
        month_data["quantity_growth"] = month_data["total_quantity"].pct_change() * 100
        month_data["revenue_growth"] = month_data["total_money_sold"].pct_change() * 100
        month_data["price_growth"] = month_data["unit_price"].pct_change() * 100
        
        # Prepare data for response
        years_data = []
        for _, row in month_data.iterrows():
            year_data = {
                "year": int(row["year"]),
                "quantity": int(row["total_quantity"]),
                "revenue": float(row["total_money_sold"]),
                "unit_price": float(row["unit_price"])
            }
            
            # Add growth rates if available
            if not pd.isna(row["quantity_growth"]):
                year_data["quantity_growth"] = float(row["quantity_growth"].round(1))
            if not pd.isna(row["revenue_growth"]):
                year_data["revenue_growth"] = float(row["revenue_growth"].round(1))
            if not pd.isna(row["price_growth"]):
                year_data["price_growth"] = float(row["price_growth"].round(1))
            
            years_data.append(year_data)
        
        # Calculate average metrics across years
        avg_metrics = {
            "avg_quantity": float(month_data["total_quantity"].mean().round()),
            "avg_revenue": float(month_data["total_money_sold"].mean().round()),
            "avg_unit_price": float(month_data["unit_price"].mean().round(2))
        }
        
        # Check for inflation impact in the most recent year
        has_inflation_impact = False
        if len(years_data) >= 2:
            latest_year = years_data[-1]
            if "price_growth" in latest_year and "quantity_growth" in latest_year:
                if latest_year["price_growth"] > 5 and latest_year["quantity_growth"] < 0:
                    has_inflation_impact = True
        
        months_comparison[month_name_map[month]] = {
            "years_data": years_data,
            "avg_metrics": avg_metrics,
            "has_inflation_impact": has_inflation_impact
        }
    
    return months_comparison

def run_seasonal_comparison(df, category):
    """Run seasonal performance comparison analysis."""
    # Define seasons
    winter_months = [12, 1, 2]
    spring_months = [3, 4, 5]
    summer_months = [6, 7, 8]
    fall_months = [9, 10, 11]
    
    # Function to assign season
    def get_season(month):
        if month in winter_months:
            return "الشتاء"
        elif month in spring_months:
            return "الربيع"
        elif month in summer_months:
            return "الصيف"
        else:
            return "الخريف"
    
    # Add season to data
    df["season"] = df["month"].apply(get_season)
    
    # Group by season and year
    seasonal_yearly = df.groupby(["season", "year"]).agg({
        "total_quantity": "sum",
        "total_money_sold": "sum"
    }).reset_index()
    
    # Calculate unit price
    seasonal_yearly["unit_price"] = seasonal_yearly["total_money_sold"] / seasonal_yearly["total_quantity"]
    seasonal_yearly["unit_price"] = seasonal_yearly["unit_price"].fillna(0).round(2)
    
    # Format response for all seasons
    seasons_comparison = {}
    
    for season in ["الشتاء", "الربيع", "الصيف", "الخريف"]:
        season_data = seasonal_yearly[seasonal_yearly["season"] == season]
        
        if season_data.empty:
            continue
            
        # Sort by year
        season_data = season_data.sort_values("year")
        
        # Calculate year-over-year growth rates
        season_data["quantity_growth"] = season_data["total_quantity"].pct_change() * 100
        season_data["revenue_growth"] = season_data["total_money_sold"].pct_change() * 100
        season_data["price_growth"] = season_data["unit_price"].pct_change() * 100
        
        # Prepare data for response
        years_data = []
        for _, row in season_data.iterrows():
            year_data = {
                "year": int(row["year"]),
                "quantity": int(row["total_quantity"]),
                "revenue": float(row["total_money_sold"]),
                "unit_price": float(row["unit_price"])
            }
            
            # Add growth rates if available
            if not pd.isna(row["quantity_growth"]):
                year_data["quantity_growth"] = float(row["quantity_growth"].round(1))
            if not pd.isna(row["revenue_growth"]):
                year_data["revenue_growth"] = float(row["revenue_growth"].round(1))
            if not pd.isna(row["price_growth"]):
                year_data["price_growth"] = float(row["price_growth"].round(1))
            
            years_data.append(year_data)
        
        # Calculate average metrics across years
        avg_metrics = {
            "avg_quantity": float(season_data["total_quantity"].mean().round()),
            "avg_revenue": float(season_data["total_money_sold"].mean().round()),
            "avg_unit_price": float(season_data["unit_price"].mean().round(2))
        }
        
        # Check for inflation impact in the most recent year
        has_inflation_impact = False
        if len(years_data) >= 2:
            latest_year = years_data[-1]
            if "price_growth" in latest_year and "quantity_growth" in latest_year:
                if latest_year["price_growth"] > 5 and latest_year["quantity_growth"] < 0:
                    has_inflation_impact = True
        
        seasons_comparison[season] = {
            "years_data": years_data,
            "avg_metrics": avg_metrics,
            "has_inflation_impact": has_inflation_impact
        }
    
    return seasons_comparison

def run_inflation_analysis(df, category, inflation_factor):
    """Run inflation impact analysis."""
    # Calculate yearly aggregates
    yearly_agg = df.groupby("year").agg({
        "total_quantity": "sum",
        "total_money_sold": "sum"
    }).reset_index()
    
    # Calculate average unit price
    yearly_agg["avg_price"] = yearly_agg["total_money_sold"] / yearly_agg["total_quantity"]
    yearly_agg["avg_price"] = yearly_agg["avg_price"].fillna(0).round(2)
    
    # Calculate year-over-year growth rates
    yearly_agg["quantity_growth"] = yearly_agg["total_quantity"].pct_change() * 100
    yearly_agg["revenue_growth"] = yearly_agg["total_money_sold"].pct_change() * 100
    yearly_agg["price_growth"] = yearly_agg["avg_price"].pct_change() * 100
    
    # Format data for response
    yearly_data = []
    for _, row in yearly_agg.iterrows():
        year_data = {
            "year": int(row["year"]),
            "quantity": int(row["total_quantity"]),
            "revenue": float(row["total_money_sold"]),
            "avg_price": float(row["avg_price"])
        }
        
        # Add growth rates if available
        if not pd.isna(row["quantity_growth"]):
            year_data["quantity_growth"] = float(row["quantity_growth"].round(1))
        if not pd.isna(row["revenue_growth"]):
            year_data["revenue_growth"] = float(row["revenue_growth"].round(1))
        if not pd.isna(row["price_growth"]):
            year_data["price_growth"] = float(row["price_growth"].round(1))
        
        yearly_data.append(year_data)
    
    # Check for inflation impact
    inflation_impact = {
        "detected": False,
        "years_affected": [],
        "severity": "none"
    }
    
    for year_data in yearly_data:
        if "price_growth" in year_data and "quantity_growth" in year_data:
            if year_data["price_growth"] > 5 and year_data["quantity_growth"] < 0:
                inflation_impact["detected"] = True
                inflation_impact["years_affected"].append(year_data["year"])
                
                # Determine severity
                if year_data["quantity_growth"] < -15:
                    severity = "high"
                elif year_data["quantity_growth"] < -10:
                    severity = "medium-high"
                elif year_data["quantity_growth"] < -5:
                    severity = "medium"
                else:
                    severity = "low"
                
                # Update overall severity to highest detected
                if severity == "high" or inflation_impact["severity"] == "none":
                    inflation_impact["severity"] = severity
                elif severity == "medium-high" and inflation_impact["severity"] not in ["high"]:
                    inflation_impact["severity"] = severity
                elif severity == "medium" and inflation_impact["severity"] not in ["high", "medium-high"]:
                    inflation_impact["severity"] = severity
    
    # Estimate price elasticity
    price_elasticity = estimate_price_elasticity(yearly_data)
    
    # Generate pricing scenarios
    pricing_scenarios = forecast_pricing_scenarios(
        yearly_data, 
        inflation_factor, 
        price_elasticity
    ) if len(yearly_data) > 1 else []
    
    return {
        "yearly_data": yearly_data,
        "inflation_impact": inflation_impact,
        "price_elasticity": price_elasticity,
        "pricing_scenarios": pricing_scenarios
    }

def generate_comprehensive_recommendations(strategy_data, monthly_comparison, seasonal_comparison, inflation_analysis, category, inflation_factor, analysis_notes):
    """Generate comprehensive strategic recommendations based on all analyses."""
    recommendations = {
        "executive_summary": {
            "key_findings": [],
            "strategic_priorities": []
        },
        "seasonal_strategy": {
            "top_seasons": [],
            "weak_seasons": [],
            "seasonal_events": []
        },
        "pricing_strategy": {
            "overall_approach": "",
            "seasonal_pricing": [],
            "inflation_response": {}
        },
        "marketing_strategy": {
            "annual_plan": [],
            "campaign_calendar": []
        },
        "inventory_strategy": {
            "annual_plan": [],
            "seasonal_adjustments": []
        },
        "action_plan": {
            "immediate_actions": [],
            "short_term_actions": [],
            "long_term_actions": []
        }
    }
    
    # 1. Identify key findings
    
    # Performance trends
    has_declining_trend = False
    has_increasing_prices = False
    
    if inflation_analysis["yearly_data"] and len(inflation_analysis["yearly_data"]) >= 2:
        latest_year = inflation_analysis["yearly_data"][-1]
        if "quantity_growth" in latest_year and latest_year["quantity_growth"] < 0:
            has_declining_trend = True
            recommendations["executive_summary"]["key_findings"].append(
                f"انخفاض الكميات: انخفاض بنسبة {abs(latest_year['quantity_growth']):.1f}% في آخر سنة"
            )
        
        if "price_growth" in latest_year and latest_year["price_growth"] > 5:
            has_increasing_prices = True
            recommendations["executive_summary"]["key_findings"].append(
                f"ارتفاع الأسعار: زيادة بنسبة {latest_year['price_growth']:.1f}% في آخر سنة"
            )
    
    # Inflation impact
    if inflation_analysis["inflation_impact"]["detected"]:
        recommendations["executive_summary"]["key_findings"].append(
            f"تأثير التضخم: تم رصد تأثير التضخم على المبيعات (شدة: {inflation_analysis['inflation_impact']['severity']})"
        )
    
    # Seasonal performance
    strongest_season = strategy_data.get("strongestSeason")
    weakest_season = strategy_data.get("weakestSeason")
    
    if strongest_season:
        recommendations["executive_summary"]["key_findings"].append(
            f"أداء موسمي: {strongest_season} هو الموسم الأقوى أداءً"
        )
        recommendations["seasonal_strategy"]["top_seasons"].append({
            "season": strongest_season,
            "performance": f"أقوى موسم للمبيعات بإجمالي {strategy_data['seasonStats'][strongest_season.lower()]['totalQuantity']} قطعة",
            "strategies": [
                "زيادة مستويات المخزون قبل الموسم بفترة كافية",
                "تطوير حملات تسويقية مخصصة للموسم",
                "تدريب فريق المبيعات على إدارة فترات الذروة",
                "تعديل الأسعار بما يتناسب مع ارتفاع الطلب"
            ]
        })
    
    if weakest_season:
        recommendations["executive_summary"]["key_findings"].append(
            f"أداء موسمي: {weakest_season} هو الموسم الأضعف أداءً"
        )
        recommendations["seasonal_strategy"]["weak_seasons"].append({
            "season": weakest_season,
            "performance": f"أضعف موسم للمبيعات بإجمالي {strategy_data['seasonStats'][weakest_season.lower()]['totalQuantity']} قطعة",
            "strategies": [
                "تطوير عروض وخصومات لتحفيز الطلب",
                "تخفيض مستويات المخزون وتجنب التكدس",
                "الاستفادة من هذه الفترة للتخطيط الاستراتيجي"
            ]
        })
    
    # Monthly performance
    peak_months = strategy_data.get("peakMonths", [])
    if peak_months:
        recommendations["executive_summary"]["key_findings"].append(
            f"شهور الذروة: {', '.join(peak_months)}"
        )
    
    # 2. Define strategic priorities
    
    # Pricing priorities
    if inflation_analysis["inflation_impact"]["detected"]:
        recommendations["executive_summary"]["strategic_priorities"].append(
            "تطوير استراتيجية تسعير متوازنة لمواجهة التضخم مع الحفاظ على حجم المبيعات"
        )
        
        # Set pricing strategy for inflation response
        if inflation_analysis["pricing_scenarios"]:
            # Find recommended scenario
            recommended_scenario = next((s for s in inflation_analysis["pricing_scenarios"] if s.get("recommended", False)), None)
            
            if recommended_scenario:
                recommendations["pricing_strategy"]["inflation_response"] = {
                    "approach": recommended_scenario["name"],
                    "description": recommended_scenario["description"],
                    "price_change": recommended_scenario["price_change"],
                    "expected_impact": f"تغير في الكمية: {recommended_scenario['quantity_change']}%، تغير في الإيرادات: {recommended_scenario['revenue_change']}%"
                }
    
    # Seasonal priorities
    if strongest_season:
        recommendations["executive_summary"]["strategic_priorities"].append(
            f"تعظيم المبيعات خلال موسم {strongest_season} من خلال التخطيط الاستباقي وزيادة المخزون"
        )
    
    if weakest_season:
        recommendations["executive_summary"]["strategic_priorities"].append(
            f"تحسين أداء موسم {weakest_season} من خلال حملات ترويجية مبتكرة وعروض خاصة"
        )
    
    # General business priorities
    if has_declining_trend:
        recommendations["executive_summary"]["strategic_priorities"].append(
            "عكس اتجاه انخفاض المبيعات من خلال تحسين القيمة المقدمة وتطوير استراتيجيات تسويقية مبتكرة"
        )
    
    # 3. Seasonal events strategy
    
    # Add seasonal events from original strategy data
    seasonal_events = strategy_data.get("seasonalEvents", [])
    
    for event in seasonal_events:
        if event.get("strategicImportance") in ["مرتفعة", "مرتفعة جداً"]:
            event_strategies = event.get("strategies", [])
            
            recommendations["seasonal_strategy"]["seasonal_events"].append({
                "name": event["name"],
                "importance": event["strategicImportance"],
                "months": ", ".join([str(m) for m in event["months"]]),
                "strategies": event_strategies
            })
    
    # 4. Pricing strategy
    
    # Set overall pricing approach
    if inflation_analysis["inflation_impact"]["detected"]:
        recommendations["pricing_strategy"]["overall_approach"] = "استراتيجية تسعير ديناميكية تستجيب للتضخم مع الحفاظ على القدرة التنافسية"
    else:
        recommendations["pricing_strategy"]["overall_approach"] = "استراتيجية تسعير موسمية مع التركيز على القيمة المضافة"
    
    # Add seasonal pricing recommendations
    pricing_recommendations = strategy_data.get("pricingRecommendations", [])
    
    for rec in pricing_recommendations:
        recommendations["pricing_strategy"]["seasonal_pricing"].append({
            "season": rec["season"],
            "adjustment": rec["adjustment"],
            "reason": rec["reason"]
        })
    
    # 5. Marketing strategy
    
    # Add marketing campaigns
    marketing_campaigns = strategy_data.get("marketingCampaigns", [])
    
    for campaign in marketing_campaigns:
        recommendations["marketing_strategy"]["campaign_calendar"].append({
            "name": campaign["name"],
            "timing": campaign["timing"],
            "focus": campaign["focus"],
            "budget": campaign["budget"]
        })
    
    # Add annual marketing plan
    if has_declining_trend:
        recommendations["marketing_strategy"]["annual_plan"].append(
            "تطوير حملات ترويجية مبتكرة لعكس اتجاه انخفاض المبيعات"
        )
    
    if has_increasing_prices:
        recommendations["marketing_strategy"]["annual_plan"].append(
            "التركيز على إبراز القيمة المضافة للمنتجات في الحملات التسويقية لتبرير الأسعار"
        )
    
    recommendations["marketing_strategy"]["annual_plan"].extend([
        "تطوير استراتيجية تسويق متكاملة مع تعديلات موسمية",
        "بناء وتعزيز برامج ولاء العملاء لزيادة معدل تكرار الشراء",
        "الاستثمار في التسويق الرقمي وتحسين تجربة العملاء"
    ])
    
    # 6. Inventory strategy
    
    # Add seasonal inventory adjustments
    if strongest_season:
        recommendations["inventory_strategy"]["seasonal_adjustments"].append({
            "season": strongest_season,
            "action": "زيادة",
            "description": f"زيادة المخزون بنسبة 30-40% قبل موسم {strongest_season} بشهر على الأقل"
        })
    
    if weakest_season:
        recommendations["inventory_strategy"]["seasonal_adjustments"].append({
            "season": weakest_season,
            "action": "تخفيض",
            "description": f"تخفيض المخزون خلال موسم {weakest_season} لتجنب التكدس وتقليل تكاليف التخزين"
        })
    
    # Add annual inventory plan
    recommendations["inventory_strategy"]["annual_plan"].extend([
        "تطبيق نظام تصنيف ABC للمنتجات لتحديد أولويات إدارة المخزون",
        "تحسين دقة توقعات الطلب باستخدام تحليل البيانات التاريخية",
        "تطوير شراكات مرنة مع الموردين للاستجابة السريعة للتغيرات في الطلب",
        "أتمتة عمليات مراقبة المخزون وإعادة الطلب"
    ])
    
    # 7. Action plan
    
    # Immediate actions (1-3 months)
    recommendations["action_plan"]["immediate_actions"].extend([
        "مراجعة وتحديث استراتيجية التسعير استجابة للتضخم",
        "تطوير خطة تسويقية متكاملة للموسم القادم",
        "تحليل أداء المنتجات وتحديد المنتجات الأكثر ربحية"
    ])
    
    if has_declining_trend:
        recommendations["action_plan"]["immediate_actions"].append(
            "إجراء استطلاع لآراء العملاء لفهم أسباب انخفاض المبيعات"
        )
    
    # Short-term actions (3-6 months)
    recommendations["action_plan"]["short_term_actions"].extend([
        "تنفيذ استراتيجية تسويق محتوى مستمرة عبر وسائل التواصل الاجتماعي",
        "تطوير برنامج ولاء للعملاء",
        "تدريب فريق المبيعات على تقنيات البيع المتقدمة وخدمة العملاء"
    ])
    
    # Long-term actions (6-12 months)
    recommendations["action_plan"]["long_term_actions"].extend([
        "الاستثمار في تحليلات البيانات لفهم سلوك العملاء بشكل أفضل",
        "تطوير منتجات جديدة تلبي احتياجات مختلف شرائح العملاء",
        "أتمتة عمليات إدارة المخزون والطلبيات"
    ])
    
    if inflation_analysis["inflation_impact"]["detected"]:
        recommendations["action_plan"]["long_term_actions"].append(
            "تحسين كفاءة سلسلة التوريد للحد من تأثير ارتفاع التكاليف"
        )
    
    return recommendations

@sales_strategy_bp.route('/sales-trends-dashboard/<category>', methods=['GET'])
def sales_trends_dashboard(category):
    """Generate a comprehensive sales trends dashboard with key metrics and insights."""
    try:
        init_db()
        
        if not category:
            return jsonify({"error": "Category is required"}), 400
        
        # Fetch data for the category
        collection = get_collection("item_specification_monthly_demand")
        item_data = list(collection.find({"القسم": category}, {"_id": 0}))
        
        if not item_data:
            return jsonify({"error": f"No data found for category: {category}"}), 404
        
        # Convert to DataFrame
        df = pd.DataFrame(item_data)
        
        # Ensure numeric values
        df["total_quantity"] = pd.to_numeric(df["total_quantity"], errors="coerce")
        df["total_money_sold"] = pd.to_numeric(df["total_money_sold"], errors="coerce")
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["month"] = pd.to_numeric(df["month"], errors="coerce")
        
        # 1. Generate yearly trends
        yearly_trends = get_yearly_trends(df)
        
        # 2. Generate monthly trends
        monthly_trends = get_monthly_trends(df)
        
        # 3. Generate seasonal trends
        seasonal_trends = get_seasonal_trends(df)
        
        # 4. Generate product trends
        product_trends = get_product_trends(df)
        
        # 5. Generate key performance indicators
        kpis = generate_kpis(df, yearly_trends, monthly_trends)
        
        # 6. Generate insights and alerts
        insights = generate_dashboard_insights(yearly_trends, monthly_trends, seasonal_trends, kpis, category)
        
        return jsonify({
            "category": category,
            "kpis": kpis,
            "yearly_trends": yearly_trends,
            "monthly_trends": monthly_trends,
            "seasonal_trends": seasonal_trends,
            "product_trends": product_trends,
            "insights": insights
        }), 200
        
    except Exception as e:
        print(f" Error generating sales trends dashboard for {category}: {str(e)}")
        return jsonify({"error": str(e)}), 500

def get_yearly_trends(df):
    """Generate yearly sales trends data."""
    # Group by year
    yearly_agg = df.groupby("year").agg({
        "total_quantity": "sum",
        "total_money_sold": "sum"
    }).reset_index()
    
    # Calculate average unit price
    yearly_agg["avg_price"] = yearly_agg["total_money_sold"] / yearly_agg["total_quantity"]
    yearly_agg["avg_price"] = yearly_agg["avg_price"].fillna(0).round(2)
    
    # Calculate year-over-year growth rates
    yearly_agg["quantity_growth"] = yearly_agg["total_quantity"].pct_change() * 100
    yearly_agg["revenue_growth"] = yearly_agg["total_money_sold"].pct_change() * 100
    yearly_agg["price_growth"] = yearly_agg["avg_price"].pct_change() * 100
    
    # Format for response
    years_data = []
    for _, row in yearly_agg.iterrows():
        year_data = {
            "year": int(row["year"]),
            "quantity": int(row["total_quantity"]),
            "revenue": float(row["total_money_sold"]),
            "avg_price": float(row["avg_price"])
        }
        
        # Add growth rates if available
        if not pd.isna(row["quantity_growth"]):
            year_data["quantity_growth"] = float(row["quantity_growth"].round(1))
        if not pd.isna(row["revenue_growth"]):
            year_data["revenue_growth"] = float(row["revenue_growth"].round(1))
        if not pd.isna(row["price_growth"]):
            year_data["price_growth"] = float(row["price_growth"].round(1))
        
        years_data.append(year_data)
    
    # Calculate overall trend
    if len(years_data) >= 2:
        # Use the last 3 years or available years if less
        recent_years = years_data[-3:] if len(years_data) >= 3 else years_data
        
        # Calculate average growth rates
        avg_quantity_growth = sum(y.get("quantity_growth", 0) for y in recent_years if "quantity_growth" in y) / len(recent_years)
        avg_revenue_growth = sum(y.get("revenue_growth", 0) for y in recent_years if "revenue_growth" in y) / len(recent_years)
        avg_price_growth = sum(y.get("price_growth", 0) for y in recent_years if "price_growth" in y) / len(recent_years)
        
        trend = {
            "quantity_trend": "upward" if avg_quantity_growth > 5 else "downward" if avg_quantity_growth < -5 else "stable",
            "revenue_trend": "upward" if avg_revenue_growth > 5 else "downward" if avg_revenue_growth < -5 else "stable",
            "price_trend": "upward" if avg_price_growth > 5 else "downward" if avg_price_growth < -5 else "stable",
            "avg_quantity_growth": round(avg_quantity_growth, 1),
            "avg_revenue_growth": round(avg_revenue_growth, 1),
            "avg_price_growth": round(avg_price_growth, 1)
        }
    else:
        trend = {
            "quantity_trend": "stable",
            "revenue_trend": "stable",
            "price_trend": "stable",
            "avg_quantity_growth": 0,
            "avg_revenue_growth": 0,
            "avg_price_growth": 0
        }
    
    return {
        "years_data": years_data,
        "trend": trend
    }

def get_monthly_trends(df):
    """Generate monthly sales trends data."""
    # Define month names
    month_names = [
        'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
        'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
    ]
    
    # Map month numbers to names
    month_name_map = {i+1: name for i, name in enumerate(month_names)}
    
    # Group by month
    monthly_agg = df.groupby("month").agg({
        "total_quantity": "sum",
        "total_money_sold": "sum"
    }).reset_index()
    
    # Calculate average unit price
    monthly_agg["avg_price"] = monthly_agg["total_money_sold"] / monthly_agg["total_quantity"]
    monthly_agg["avg_price"] = monthly_agg["avg_price"].fillna(0).round(2)
    
    # Add month names
    monthly_agg["month_name"] = monthly_agg["month"].map(month_name_map)
    
    # Calculate distribution percentages
    total_quantity = monthly_agg["total_quantity"].sum()
    total_revenue = monthly_agg["total_money_sold"].sum()
    
    monthly_agg["quantity_pct"] = (monthly_agg["total_quantity"] / total_quantity * 100).round(1)
    monthly_agg["revenue_pct"] = (monthly_agg["total_money_sold"] / total_revenue * 100).round(1)
    
    # Sort by month
    monthly_agg = monthly_agg.sort_values("month")
    
    # Format for response
    monthly_data = []
    for _, row in monthly_agg.iterrows():
        month_data = {
            "month": row["month_name"],
            "month_number": int(row["month"]),
            "quantity": int(row["total_quantity"]),
            "revenue": float(row["total_money_sold"]),
            "avg_price": float(row["avg_price"]),
            "quantity_pct": float(row["quantity_pct"]),
            "revenue_pct": float(row["revenue_pct"])
        }
        
        monthly_data.append(month_data)
    
    # Find peak and low months
    peak_months = monthly_agg.sort_values("total_quantity", ascending=False).head(3)
    low_months = monthly_agg.sort_values("total_quantity").head(3)
    
    peak_months_data = [{
        "month": row["month_name"],
        "month_number": int(row["month"]),
        "quantity": int(row["total_quantity"]),
        "quantity_pct": float(row["quantity_pct"])
    } for _, row in peak_months.iterrows()]
    
    low_months_data = [{
        "month": row["month_name"],
        "month_number": int(row["month"]),
        "quantity": int(row["total_quantity"]),
        "quantity_pct": float(row["quantity_pct"])
    } for _, row in low_months.iterrows()]
    
    return {
        "monthly_data": monthly_data,
        "peak_months": peak_months_data,
        "low_months": low_months_data
    }

def get_seasonal_trends(df):
    """Generate seasonal sales trends data."""
    # Define seasons
    winter_months = [12, 1, 2]
    spring_months = [3, 4, 5]
    summer_months = [6, 7, 8]
    fall_months = [9, 10, 11]
    
    # Function to assign season
    def get_season(month):
        if month in winter_months:
            return "الشتاء"
        elif month in spring_months:
            return "الربيع"
        elif month in summer_months:
            return "الصيف"
        else:
            return "الخريف"
    
    # Add season to data
    df["season"] = df["month"].apply(get_season)
    
    # Group by season
    seasonal_agg = df.groupby("season").agg({
        "total_quantity": "sum",
        "total_money_sold": "sum"
    }).reset_index()
    
    # Calculate average unit price
    seasonal_agg["avg_price"] = seasonal_agg["total_money_sold"] / seasonal_agg["total_quantity"]
    seasonal_agg["avg_price"] = seasonal_agg["avg_price"].fillna(0).round(2)
    
    # Calculate distribution percentages
    total_quantity = seasonal_agg["total_quantity"].sum()
    total_revenue = seasonal_agg["total_money_sold"].sum()
    
    seasonal_agg["quantity_pct"] = (seasonal_agg["total_quantity"] / total_quantity * 100).round(1)
    seasonal_agg["revenue_pct"] = (seasonal_agg["total_money_sold"] / total_revenue * 100).round(1)
    
    # Format for response
    seasonal_data = []
    for _, row in seasonal_agg.iterrows():
        season_data = {
            "season": row["season"],
            "quantity": int(row["total_quantity"]),
            "revenue": float(row["total_money_sold"]),
            "avg_price": float(row["avg_price"]),
            "quantity_pct": float(row["quantity_pct"]),
            "revenue_pct": float(row["revenue_pct"])
        }
        
        seasonal_data.append(season_data)
    
    # Find strongest and weakest seasons
    strongest_season = seasonal_agg.loc[seasonal_agg["total_quantity"].idxmax(), "season"]
    weakest_season = seasonal_agg.loc[seasonal_agg["total_quantity"].idxmin(), "season"]
    
    # Calculate seasonality strength (ratio of strongest to weakest season)
    strongest_quantity = seasonal_agg.loc[seasonal_agg["season"] == strongest_season, "total_quantity"].iloc[0]
    weakest_quantity = seasonal_agg.loc[seasonal_agg["season"] == weakest_season, "total_quantity"].iloc[0]
    
    seasonality_ratio = strongest_quantity / weakest_quantity if weakest_quantity > 0 else 1
    
    # Determine seasonality strength
    if seasonality_ratio > 2:
        seasonality_strength = "strong"
    elif seasonality_ratio > 1.5:
        seasonality_strength = "moderate"
    else:
        seasonality_strength = "weak"
    
    return {
        "seasonal_data": seasonal_data,
        "strongest_season": strongest_season,
        "weakest_season": weakest_season,
        "seasonality_ratio": round(seasonality_ratio, 2),
        "seasonality_strength": seasonality_strength
    }

def get_product_trends(df):
    """Generate product sales trends data."""
    # Group by product specification
    product_agg = df.groupby("product_specification").agg({
        "total_quantity": "sum",
        "total_money_sold": "sum"
    }).reset_index()
    
    # Calculate average unit price
    product_agg["avg_price"] = product_agg["total_money_sold"] / product_agg["total_quantity"]
    product_agg["avg_price"] = product_agg["avg_price"].fillna(0).round(2)
    
    # Sort by quantity
    product_agg = product_agg.sort_values("total_quantity", ascending=False)
    
    # Calculate distribution percentages
    total_quantity = product_agg["total_quantity"].sum()
    total_revenue = product_agg["total_money_sold"].sum()
    
    product_agg["quantity_pct"] = (product_agg["total_quantity"] / total_quantity * 100).round(1)
    product_agg["revenue_pct"] = (product_agg["total_money_sold"] / total_revenue * 100).round(1)
    
    # Get top 10 products
    top_products = product_agg.head(15)
    
    # Format for response
    top_products_data = []
    for _, row in top_products.iterrows():
        product_data = {
            "product": row["product_specification"],
            "quantity": int(row["total_quantity"]),
            "revenue": float(row["total_money_sold"]),
            "avg_price": float(row["avg_price"]),
            "quantity_pct": float(row["quantity_pct"]),
            "revenue_pct": float(row["revenue_pct"])
        }
        
        top_products_data.append(product_data)
    
    # Calculate product concentration
    top_5_quantity_pct = product_agg.head(5)["quantity_pct"].sum()
    top_10_quantity_pct = product_agg.head(10)["quantity_pct"].sum()
    
    # Determine product concentration level
    if top_5_quantity_pct > 60:
        concentration_level = "high"
    elif top_5_quantity_pct > 40:
        concentration_level = "moderate"
    else:
        concentration_level = "low"
    
    return {
        "top_products": top_products_data,
        "top_5_concentration": round(top_5_quantity_pct, 1),
        "top_10_concentration": round(top_10_quantity_pct, 1),
        "concentration_level": concentration_level
    }

def generate_kpis(df, yearly_trends, monthly_trends):
    """Generate key performance indicators."""
    kpis = {}
    
    # Ensure we have at least one year of data
    if yearly_trends["years_data"]:
        # Get the most recent year
        latest_year = yearly_trends["years_data"][-1]
        
        # Annual sales volume
        kpis["annual_sales_volume"] = latest_year["quantity"]
        
        # Annual sales revenue
        kpis["annual_sales_revenue"] = latest_year["revenue"]
        
        # Average unit price
        kpis["avg_unit_price"] = latest_year["avg_price"]
        
        # Year-over-year growth
        if "quantity_growth" in latest_year:
            kpis["yoy_quantity_growth"] = latest_year["quantity_growth"]
            kpis["yoy_revenue_growth"] = latest_year.get("revenue_growth", 0)
            kpis["yoy_price_growth"] = latest_year.get("price_growth", 0)
        else:
            kpis["yoy_quantity_growth"] = 0
            kpis["yoy_revenue_growth"] = 0
            kpis["yoy_price_growth"] = 0
    
    # Sales concentration
    if monthly_trends["peak_months"]:
        # Calculate percentage of sales in peak 3 months
        peak_3_pct = sum(m["quantity_pct"] for m in monthly_trends["peak_months"])
        kpis["peak_months_concentration"] = round(peak_3_pct, 1)
    
    return kpis

def generate_dashboard_insights(yearly_trends, monthly_trends, seasonal_trends, kpis, category):
    """Generate insights and alerts for the sales dashboard."""
    insights = []
    
    # Yearly trends insights
    if yearly_trends["trend"]["quantity_trend"] == "downward":
        insights.append({
            "type": "alert",
            "category": "yearly",
            "title": "انخفاض المبيعات السنوية",
            "description": f"انخفاض متوسط في المبيعات السنوية بنسبة {abs(yearly_trends['trend']['avg_quantity_growth'])}% خلال السنوات الأخيرة",
            "recommendations": [
                "إجراء تحليل معمق لأسباب انخفاض المبيعات",
                "تطوير حملات ترويجية مبتكرة لتحفيز الطلب",
                "مراجعة استراتيجية التسعير ومقارنتها بالمنافسين"
            ]
        })
    elif yearly_trends["trend"]["quantity_trend"] == "upward":
        insights.append({
            "type": "positive",
            "category": "yearly",
            "title": "نمو المبيعات السنوية",
            "description": f"نمو إيجابي في المبيعات السنوية بنسبة {yearly_trends['trend']['avg_quantity_growth']}% خلال السنوات الأخيرة",
            "recommendations": [
                "الاستثمار في توسيع خط المنتجات لمواصلة النمو",
                "زيادة المخزون استعداداً للنمو المتوقع",
                "تحليل أسباب النمو وتعزيزها"
            ]
        })
    
    # Price and inflation insights
    if yearly_trends["trend"]["price_trend"] == "upward" and yearly_trends["trend"]["quantity_trend"] == "downward":
        insights.append({
            "type": "alert",
            "category": "inflation",
            "title": "تأثير التضخم على المبيعات",
            "description": f"ارتفاع الأسعار بنسبة {yearly_trends['trend']['avg_price_growth']}% مع انخفاض الكميات بنسبة {abs(yearly_trends['trend']['avg_quantity_growth'])}%، مما يشير إلى تأثير التضخم",
            "recommendations": [
                "تطوير استراتيجية تسعير متوازنة للحفاظ على حجم المبيعات",
                "تقديم خيارات منتجات بفئات سعرية متنوعة",
                "التركيز على إبراز القيمة المضافة للمنتجات لتبرير الأسعار"
            ]
        })
    
    # Seasonal insights
    if seasonal_trends["seasonality_strength"] == "strong":
        insights.append({
            "type": "strategy",
            "category": "seasonal",
            "title": "تباين موسمي قوي",
            "description": f"تباين كبير في المبيعات الموسمية (نسبة {seasonal_trends['seasonality_ratio']}x) مع تركيز في موسم {seasonal_trends['strongest_season']}",
            "recommendations": [
                f"تطوير استراتيجية متكاملة لموسم {seasonal_trends['strongest_season']}",
                "زيادة المخزون قبل الموسم القوي بفترة كافية",
                f"تطوير حملات ترويجية خاصة لتحسين أداء موسم {seasonal_trends['weakest_season']}"
            ]
        })
    
    # Monthly concentration insights
    if kpis.get("peak_months_concentration", 0) > 50:
        peak_months_str = ", ".join([m["month"] for m in monthly_trends["peak_months"]])
        insights.append({
            "type": "strategy",
            "category": "monthly",
            "title": "تركيز المبيعات في أشهر محددة",
            "description": f"تركيز {kpis['peak_months_concentration']}% من المبيعات في ثلاثة أشهر فقط ({peak_months_str})",
            "recommendations": [
                "تطوير استراتيجيات لتوزيع المبيعات بشكل أكثر توازناً على مدار السنة",
                "تحسين التخطيط للمخزون لتلبية الطلب خلال أشهر الذروة",
                "تقديم عروض خاصة خلال الأشهر الضعيفة لتحفيز الطلب"
            ]
        })
    
    # Product-specific insights
    if category in ["حريمي", "رجالي", "اطفال"]:
        insights.append({
            "type": "category",
            "category": "product",
            "title": f"توصيات خاصة بقسم {category}",
            "description": f"تحليل متخصص لقسم {category} ومنتجاته الرئيسية",
            "recommendations": [
                "متابعة اتجاهات الموضة والتصاميم الجديدة",
                "تطوير خطوط إنتاج متنوعة لتناسب مختلف الفئات السعرية",
                "التركيز على الجودة والمتانة كميزة تنافسية"
            ]
        })
    elif category == "مدارس":
        insights.append({
            "type": "category",
            "category": "product",
            "title": "توصيات خاصة بقسم المدارس",
            "description": "تحليل متخصص لقسم المدارس واستراتيجيات موسم العودة للمدارس",
            "recommendations": [
                "البدء بالإعداد والتسويق قبل بداية العام الدراسي بشهرين",
                "تقديم عروض للمشتريات الجماعية للمدارس والعائلات",
                "تطوير مجموعات متكاملة من مستلزمات المدارس بأسعار تنافسية"
            ]
        })
    elif category in ["احذية حريمي", "احذية رجالي", "احذية اطفال"]:
        insights.append({
            "type": "category",
            "category": "product",
            "title": f"توصيات خاصة بقسم {category}",
            "description": f"تحليل متخصص لقسم {category} واستراتيجياته",
            "recommendations": [
                "التركيز على الراحة والجودة كميزات تنافسية رئيسية",
                "متابعة اتجاهات الموضة والتصاميم الجديدة",
                "تقديم تشكيلات موسمية متنوعة (صيفية، شتوية)"
            ]
        })
    
    return insights

# Register the Blueprint for use with the application
def init_app(app):
    app.register_blueprint(sales_strategy_bp, url_prefix='/api/sales-strategy')
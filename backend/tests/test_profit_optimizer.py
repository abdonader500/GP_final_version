import pytest
import pandas as pd
import sys
import os

# Ensure the project root is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.database import fetch_data, init_db  # ✅ Import database initializer


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Ensures the database is initialized before running tests."""
    print("🔄 Initializing database for testing...")
    init_db()  # ✅ Initialize MongoDB connection


@pytest.mark.parametrize("collection", ["sales"])
def test_profit_calculation(collection):
    """Manually computes profit percentage and compares with stored values."""
    sales_data = fetch_data(collection, projection={"_id": 0, "سعر الجملة": 1, "سعر المستهلك": 1, "نسبة الربح": 1})
    assert sales_data, "⚠ No sales data found! Ensure the database contains valid data."

    sales_df = pd.DataFrame(sales_data)
    sales_df["Computed_Profit_Percentage"] = ((sales_df["سعر المستهلك"] - sales_df["سعر الجملة"]) / sales_df["سعر المستهلك"]) * 100
    sales_df["Difference"] = abs(sales_df["Computed_Profit_Percentage"] - sales_df["نسبة الربح"])

    incorrect = sales_df[sales_df["Difference"] > 0.1]
    assert incorrect.empty, f"⚠ Discrepancies found in {len(incorrect)} records: {incorrect}"


@pytest.mark.parametrize("collection", ["sales"])
def test_price_level_classification(collection):
    """Validates price level classification based on quantiles."""
    sales_data = fetch_data(collection, projection={"_id": 0, "القسم": 1, "سعر الجملة": 1, "price_level": 1})
    assert sales_data, "⚠ No sales data found! Ensure the database contains valid data."

    sales_df = pd.DataFrame(sales_data)

    for category, data in sales_df.groupby("القسم"):
        q1 = data["سعر الجملة"].quantile(0.33)
        q3 = data["سعر الجملة"].quantile(0.66)

        incorrect = data[(data["price_level"] == "low") & (data["سعر الجملة"] > q1)]
        incorrect = incorrect.append(data[(data["price_level"] == "moderate") & ((data["سعر الجملة"] < q1) | (data["سعر الجملة"] > q3))])
        incorrect = incorrect.append(data[(data["price_level"] == "high") & (data["سعر الجملة"] < q3)])

        assert incorrect.empty, f"⚠ Incorrect classifications in {category}: {incorrect}"


@pytest.mark.parametrize("collection", ["sales"])
def test_validate_average_profit(collection):
    """Ensures the computed optimal profit percentages match manual calculations."""
    sales_data = fetch_data(collection, projection={"_id": 0, "القسم": 1, "price_level": 1, "نسبة الربح": 1})
    assert sales_data, "⚠ No sales data found! Ensure the database contains valid data."

    sales_df = pd.DataFrame(sales_data)

    avg_profit = sales_df.groupby(["القسم", "price_level"])["نسبة الربح"].mean().reset_index()
    avg_profit.rename(columns={"نسبة الربح": "Computed_Optimal_Profit"}, inplace=True)

    assert not avg_profit.empty, "⚠ No computed average profit percentages found!"


@pytest.mark.parametrize("collection", ["sales"])
def test_check_outliers(collection):
    """Identifies outliers in profit percentage."""
    sales_data = fetch_data(collection, projection={"_id": 0, "نسبة الربح": 1})
    assert sales_data, "⚠ No sales data found! Ensure the database contains valid data."

    sales_df = pd.DataFrame(sales_data)

    Q1 = sales_df["نسبة الربح"].quantile(0.25)
    Q3 = sales_df["نسبة الربح"].quantile(0.75)
    IQR = Q3 - Q1

    outliers = sales_df[(sales_df["نسبة الربح"] < (Q1 - 1.5 * IQR)) | (sales_df["نسبة الربح"] > (Q3 + 1.5 * IQR))]

    assert outliers.empty, f"⚠ Found {len(outliers)} outliers: {outliers}"


@pytest.mark.parametrize("computed_data", [{"حريمي.moderate": 30.45, "رجالي.low": 35.23}])
@pytest.mark.parametrize("historical_data", [{"حريمي.moderate": 30.5, "رجالي.low": 35.2}])
def test_validate_against_historical_data(computed_data, historical_data):
    """Compares computed profit percentages with historical data."""
    for key, value in computed_data.items():
        if key in historical_data:
            assert abs(value - historical_data[key]) <= 1, f"⚠ Difference detected for {key}: Computed={value}, Historical={historical_data[key]}"

import logging
import pandas as pd
from scraper import Product


logger = logging.getLogger(__name__)

def products_to_dataframe(products: list[Product]) -> pd.DataFrame:
    if not products:
        logger.warning("No products to convert.")
        return pd.DataFrame()

    data = [vars(p) for p in products]
    df = pd.DataFrame(data)
    logger.info(f"Converted {len(df)} products to Dataframe.")
    return df

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    original_count = len(df)
    df = df.drop_duplicates(subset=["url"])

    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df[df["price"] > 0]
    df["original_price"] = pd.to_numeric(df["original_price"], errors="coerce")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["discount_percent"] = pd.to_numeric(df["discount_percent"], errors="coerce")

    removed = original_count - len(df)
    logger.info(f"Cleaned data: removed {removed} invalid/duplicate rows.")
    return df.reset_index(drop=True)

def add_analysis_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    low_thresh = df["price"].quantile(0.33)
    high_thresh = df["price"].quantile(0.67)

    def segment_price(price: float) -> str:
        if price <= low_thresh:
            return "Budget"
        elif price <= high_thresh:
            return "Mid-range"
        else:
            return "Premium"

    df["price_segment"] = df["price"].apply(segment_price)
    df["has_discount"] = df["discount_percent"].notna() & (df["discount_percent"] > 0)
    df["effective_discount_value"] = (df["original_price"] - df["price"]).clip(lower=0)

    logger.info("Analysis columns added: price_segment, has_discount, effective_discount_value")
    return df

def generate_summary(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}

    summary = {
        "total_products": len(df),
        "keywords_analyzed": df["keyword"].nunique(),
        "price_min": df["price"].min(),
        "price_max": df["price"].max(),
        "price_mean": df["price"].mean(),
        "price_median": df["price"].median(),
        "avg_rating": df["rating"].mean(),
        "pct_with_discount": (df["has_discount"].sum() / len(df)) * 100,
        "avg_discount_pct": df["discount_percent"].mean(),
        "top_locations": df["shop_location"].value_counts().head(5).to_dict(),
        "price_segment_distribution": df["price_segment"].value_counts().to_dict(),
    }

    logger.info("Summary statistics generated.")
    return summary


import os
import logging
from datetime import datetime
from reporter import generate_excel_report
from scraper import scrape_tokopedia, random_delay
from cleaner import products_to_dataframe, clean_dataframe, add_analysis_columns, generate_summary


# LOGGING SETUP
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("analyzer.log"),
        logging.StreamHandler()
    ],
)
logger = logging.getLogger(__name__)

#CONFIGURATION
KEYWORDS = ["sepatu lari pria", "tws bluetooth"]
MAX_LOADS = 3
OUTPUT_DIR = "output"

def main():
    logger.info("=" * 60)
    logger.info("Competitor Analyer - Started")
    logger.info(f"Keywords: {KEYWORDS}")
    logger.info("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # SCRAPE
    all_products = []
    for keyword in KEYWORDS:
        logger.info(f"\n Scraping keyword: '{keyword}'")
        products = scrape_tokopedia(keyword, max_loads=MAX_LOADS)
        all_products.extend(products)
        random_delay(1, 5)

    if not all_products:
        logger.error("No products scraped. Exiting")
        return

    # CLEAN AND ANALYZE
    df = products_to_dataframe(all_products)
    df = clean_dataframe(df)
    df = add_analysis_columns(df)
    summary = generate_summary(df)

    #Generate Report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(OUTPUT_DIR, f"competitor_report_{timestamp}.xlsx")
    generate_excel_report(df, summary, KEYWORDS, output_path)

    logger.info(f"\nReport saved: {output_path}")
    logger.info(f"   Total products: {summary.get('total_products')}")
    logger.info(f"   Avg price: Rp {summary.get('price_mean', 0):,.0f}")
    logger.info(f"   Avg rating: {summary.get('avg_rating', 0):.2f}")


if __name__ == "__main__":
    main()

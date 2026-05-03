import re
import time
import random
import logging
from typing import Optional
from bs4 import BeautifulSoup
from selenium import webdriver
from dataclasses import dataclass, field
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


logger = logging.getLogger(__name__)

@dataclass
class Product:
    name: str
    price: float
    original_price: Optional[float]
    discount_percent: Optional[int]
    rating: Optional[float]
    sold_count: Optional[str]
    shop_name: Optional[str]
    shop_location: Optional[str]
    url: str
    keyword: str
    scraped_at: str = field(default_factory=lambda: __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


def _init_driver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    return driver

def random_delay(min_sec: float = 1.5, max_sec: float = 3.5):
    delay = random.uniform(min_sec, max_sec)
    logger.debug(f"Waiting {delay:.1f}s before next request...")
    time.sleep(delay)

def parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    cleaned = "".join(c for c in text if c.isdigit())
    return float(cleaned) if cleaned else None

def parse_tokopedia_page(html: str, keyword: str) -> list[Product]:
    soup = BeautifulSoup(html, "lxml")
    products = []

    cards = soup.select("div.css-5wh65g")
    for card in cards:
        try:
            #URL
            url_el = card.select_one("a[href]")
            url = url_el["href"] if url_el else "#"

            content = card.select_one("div.y-oybT3IAd310DVdH3OwVg\\=\\=")
            if not content:
                a_tag = card.select_one("a")
                divs = a_tag.find_all("div", recursive=False) if a_tag else []
                content = divs[1] if len(divs) > 1 else None

            if not content:
                continue

            #Product Name
            name_el = content.select_one("span")
            name = name_el.get_text(strip=True) if name_el else "N/A"

            #Price
            all_divs = content.find_all("div", recursive=False)
            price_block = all_divs[1] if len(all_divs)>1 else None

            price_el = price_block.find("div") if price_block else None
            price_text = price_el.get_text(strip=True) if price_el else "0"
            price = parse_price(price_text)

            #Original Price
            original_price_el = price_block.select_one("span") if price_block else None
            original_price = parse_price(original_price_el.get_text()) if original_price_el else None

            #Discount
            discount_el = card.select_one("span[style*='background: rgb(249']")
            discount_text = discount_el.get_text(strip=True) if discount_el else None
            discount_percent = int("".join(filter(str.isdigit, discount_text))) if discount_text else None

            #Rating and Sold Count
            spans = content.find_all("span")
            rating = None
            sold_count = None

            for span in spans:
                text = span.get_text(strip=True)
                if re.fullmatch(r"[1-5]\.[0-9]", text):
                    try:
                        rating = float(text)
                    except ValueError:
                        pass
                if "terjual" in text.lower():
                        sold_count = text

            #Information
            shop_div = content.select_one("div._1yoE8Ml3qwvn-r\\+EZ5hlbA\\=\\=")
            if shop_div:
                shop_spans = shop_div.find_all("span")
                shop_name = shop_spans[0].get_text(strip=True) if len(shop_spans) > 0 else None
                shop_location = shop_spans[1].get_text(strip=True) if len(shop_spans) > 1 else None
            else:
                shop_name = None
                shop_location = None

            product = Product(
                name=name,
                price=price,
                original_price=original_price,
                discount_percent=discount_percent,
                rating=rating,
                sold_count=sold_count,
                shop_name=shop_name,
                shop_location=shop_location,
                url=url,
                keyword=keyword
            )
            products.append(product)

        except Exception as e:
            logger.debug(f"Skipping card due to parse error: {e}")
            continue

    logger.info(f"Total product parsed: {len(products)}")
    return products

def scrape_tokopedia(keyword: str, max_loads: int = 3) -> list[Product]:
    base_url = "https://www.tokopedia.com/search"
    driver = _init_driver()
    wait = WebDriverWait(driver, 15)

    all_products = []

    try:
        url = f"{base_url}?st=&q={keyword.replace(' ', '%20')}"
        logger.info(f"Opening: {url}")
        driver.get(url)

        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='dSRPSearchInfo']"))
        )
        logger.info("Initial products loaded.")

        for i in range(max_loads):
            try:
                current_height = 0
                while True:
                    driver.execute_script("window.scrollBy(0, 800);")
                    random_delay(0.3, 0.5)

                    new_height = driver.execute_script("return window.pageYOffset + window.innerHeight")
                    total_height = driver.execute_script("return document.body.scrollHeight")

                    if new_height >= total_height:
                        break
                    current_height = new_height

                load_more_btn = wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "[data-unify='Button']")
                    )
                )
                driver.execute_script("arguments[0].click();", load_more_btn)
                logger.info(f"Load more clicked {i + 1} of {max_loads}")
                random_delay(2, 3)

            except TimeoutException:
                logger.info("Load More Button Not Found — All the products loaded.")
                break
        html = driver.page_source
        all_products = parse_tokopedia_page(html, keyword)

    except Exception as e:
        logger.error(f"Scraping failed: {e}")

    finally:
        driver.quit()
        logger.info(f"Browser closed.")

    return all_products



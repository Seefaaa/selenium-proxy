from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
import uvicorn
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import logging
from typing import Optional
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Selenium Web Scraper", description="A FastAPI server that fetches web pages using Selenium")

# Remote WebDriver configuration
SELENIUM_HUB_URL = os.getenv("SELENIUM_HUB_URL", "http://localhost:4444/wd/hub")

def create_driver():
    """Create and configure a remote Chrome WebDriver instance"""
    chrome_options = Options()

    # Headless mode for server environments
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    # Disable images and CSS for faster loading (optional)
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Set up desired capabilities for Chrome
    desired_capabilities = DesiredCapabilities.CHROME.copy()
    desired_capabilities.update(chrome_options.to_capabilities())

    try:
        # Create remote WebDriver instance
        driver = webdriver.Remote(
            command_executor=SELENIUM_HUB_URL,
            desired_capabilities=desired_capabilities,
            options=chrome_options
        )
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        logger.error(f"Failed to create remote Chrome driver: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to remote browser at {SELENIUM_HUB_URL}")

@app.get("/", response_class=HTMLResponse)
async def fetch_page(url: str = Query(..., description="URL of the page to fetch")):
    """
    Fetch a web page using Selenium and return its HTML content

    Parameters:
    - url: The URL to fetch (required query parameter)

    Example: http://localhost:8000/?url=https://example.com
    """

    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required")

    # Basic URL validation
    if not (url.startswith('http://') or url.startswith('https://')):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

    driver = None
    try:
        logger.info(f"Fetching URL: {url}")
        driver = create_driver()

        # Navigate to the URL
        driver.get(url)

        # Wait for page to load (wait for body element)
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Get the page source
        page_source = driver.page_source

        logger.info(f"Successfully fetched page: {url}")
        return HTMLResponse(content=page_source)

    except TimeoutException:
        logger.error(f"Timeout while loading page: {url}")
        raise HTTPException(status_code=408, detail="Page load timeout")

    except WebDriverException as e:
        logger.error(f"Selenium WebDriver error: {e}")
        raise HTTPException(status_code=500, detail="Browser error occurred")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        # Always close the driver to prevent resource leaks
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logger.warning(f"Error closing driver: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "selenium-scraper"}

@app.get("/info")
async def info():
    """Get server information"""
    return {
        "title": "Selenium Web Scraper",
        "description": "FastAPI server that fetches web pages using Selenium",
        "selenium_hub": SELENIUM_HUB_URL,
        "usage": "GET /?url=<target_url>",
        "example": "/?url=https://example.com"
    }

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "main:app",  # Change "main" to your filename if different
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )

# Requirements for this server:
# pip install fastapi uvicorn selenium
#
# You'll need a Selenium Grid/Hub running:
# Option 1: Using Docker (recommended):
# docker run -d -p 4444:4444 -p 7900:7900 --shm-size=2g selenium/standalone-chrome:latest
#
# Option 2: Using Docker Compose:
# version: '3'
# services:
#   selenium-hub:
#     image: selenium/hub:latest
#     container_name: selenium-hub
#     ports:
#       - "4444:4444"
#   chrome:
#     image: selenium/node-chrome:latest
#     shm_size: 2gb
#     depends_on:
#       - selenium-hub
#     environment:
#       - HUB_HOST=selenium-hub
#       - HUB_PORT=4444
#
# Environment Variables:
# SELENIUM_HUB_URL - URL of the Selenium Hub (default: http://localhost:4444/wd/hub)
#
# To run the server:
# python main.py
# or
# uvicorn main:app --host 0.0.0.0 --port 8000 --reload
#
# Example usage:
# http://localhost:8000/?url=https://example.com
# http://localhost:8000/health
# http://localhost:8000/info

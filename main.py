from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import pandas as pd
import time
import os

# Configuration
URL = 'https://www.nhis.gov.gh/payments'
WAIT_TIMEOUT = 15
CSV_FILENAME = "nhis_payments_alls.csv"
CHECKPOINT_FILE = "nhis_checkpoint.txt"
HEADERS = ["Facility Name", "District", "Amount Paid", "Claim Month", "Payment Date"]


def setup_driver():
    options = webdriver.ChromeOptions()
    #options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    return driver

#loads from the checkpoint.txt
def load_checkpoint():
    """Loads progress from previous run"""
    try:
        with open(CHECKPOINT_FILE, 'r') as f:
            return int(f.read().strip())
    except:
        return 1

#save checkpoint
def save_checkpoint(page_num):
    """Saves current progress"""
    with open(CHECKPOINT_FILE, 'w') as f:
        f.write(str(page_num))

# scraping function
def scrape_data():
    driver = setup_driver()
    driver.get(URL)
    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    start_page = load_checkpoint()
    all_rows = []

    # Load existing data if resuming
    if start_page > 1 and os.path.exists(CSV_FILENAME):
        existing_df = pd.read_csv(CSV_FILENAME)
        all_rows = existing_df.values.tolist()
        print(f"Resuming from page {start_page} with {len(all_rows)} existing rows")

    current_page = start_page

    try:
        while True:
            # Wait for table and scrape data
            table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table.rgMasterTable')))
            rows = table.find_elements(By.CSS_SELECTOR, 'tr.rgRow, tr.rgAltRow')

            if not rows:
                print("No data found - stopping.")
                break

            # Extract data from current page
            new_rows = []
            for row in rows:
                cells = [cell.text.strip() for cell in row.find_elements(By.TAG_NAME, 'td')]
                if len(cells) == len(HEADERS):
                    new_rows.append(cells)

            all_rows.extend(new_rows)
            print(f"Scraped page {current_page} with {len(new_rows)} rows | Total: {len(all_rows)}")

            # Save data after each page
            save_to_csv(all_rows)
            save_checkpoint(current_page + 1)  # Save next page to resume

            # Try to click Next button
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, "button.rgPageNext[title='Next Page']")

                if "disabled" in next_btn.get_attribute("class"):
                    print("Reached last page.")
                    break

                # Scroll and click
                driver.execute_script("arguments[0].scrollIntoView();", next_btn)
                next_btn.click()

                # Wait for new page to load
                wait.until(EC.staleness_of(table))
                current_page += 1

                # Small delay to avoid overloading
                time.sleep(0.5)

            except NoSuchElementException:
                print("Next button not found. Ending scrape.")
                break
            except Exception as e:
                print(f"Error clicking next button: {str(e)}")
                break

    except Exception as e:
        print(f"Fatal error: {str(e)}")
    finally:
        driver.quit()
        return all_rows

def save_to_csv(data):
    df = pd.DataFrame(data, columns=HEADERS)
    df = df.dropna(how='all')
    df = df[df[HEADERS[0]].str.strip() != ""]
    df.to_csv(CSV_FILENAME, index=False)



scraped_data = scrape_data()
save_to_csv(scraped_data)

# Clean up checkpoint on successful completion
if os.path.exists(CHECKPOINT_FILE):
    os.remove(CHECKPOINT_FILE)
print(f"Saved {len(scraped_data)} records to {CSV_FILENAME}")
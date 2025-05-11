import os
import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (WebDriverException,
                                        TimeoutException,
                                        StaleElementReferenceException)

# ======================
# CONFIGURATION
# ======================
URL = "https://www.nhis.gov.gh/payments"
CSV_FILENAME = "nhis_payments_final.csv"
CHECKPOINT_FILE = "nhis_checkpoint.txt"
HEADERS = ["Facility Name", "District", "Amount Paid", "Claim Month", "Payment Date"]
MAX_RETRIES = 5
INITIAL_DELAY = 1.5
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
]


# ======================
# CORE ENGINE
# ======================
class NHISScraper:
    def __init__(self):
        self.driver = None
        self.current_page = 1
        self.total_rows = 0
        self.attempt_count = 0
        self.session_start = time.time()

    def _create_driver(self):
        """Initialize browser with anti-detection measures"""
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")

        driver = webdriver.Chrome(options=options)
        driver.set_window_size(random.randint(1200, 1400), random.randint(800, 1000))
        return driver

    def _human_delay(self):
        """Randomized human-like delays"""
        base_delay = random.uniform(0.8, 2.4)
        variance = random.choice([-0.3, 0, 0.3])
        time.sleep(max(0.5, base_delay + variance))

    def _save_progress(self, data):
        """Atomic save with backup creation"""
        try:
            # Save primary file
            df = pd.DataFrame(data, columns=HEADERS)
            df.to_csv(CSV_FILENAME, index=False)

            # Create timestamped backup
            backup_name = f"{CSV_FILENAME[:-4]}_backup_{int(time.time())}.csv"
            df.to_csv(backup_name, index=False)

            # Update checkpoint
            with open(CHECKPOINT_FILE, "w") as f:
                f.write(str(self.current_page))

        except Exception as e:
            print(f"CRITICAL SAVE ERROR: {str(e)}")

    def _load_resume_data(self):
        """Smart resume system with validation"""
        if not os.path.exists(CSV_FILENAME):
            return []

        try:
            df = pd.read_csv(CSV_FILENAME)
            rows = df.values.tolist()
            expected_pages = len(rows) // 20
            self.current_page = expected_pages + 1
            print(f"Resuming from page {self.current_page} with {len(rows)} existing rows")
            return rows
        except Exception as e:
            print(f"Resume data corrupted: {str(e)}")
            return []

    def _force_page_turn(self):
        """Nuclear-grade page turning solution"""
        for attempt in range(4):  # 4 attempts per page turn
            try:
                # Get fresh button reference
                next_btn = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//*[contains(@class, 'rgPageNext') and " \
                                   "not(contains(@class, 'rgDisabled'))]")
                    )
                )

                # Record pre-click state
                pre_click_hash = self._page_state_hash()

                # Human-like interaction sequence
                ActionChains(self.driver) \
                    .move_to_element(next_btn) \
                    .pause(random.uniform(0.2, 0.5)) \
                    .click() \
                    .perform()

                # Wait for state change using multiple verification methods
                WebDriverWait(self.driver, 20).until(
                    lambda d: self._page_state_hash() != pre_click_hash or
                              d.current_url != self.driver.current_url
                )

                # Final load verification
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "tr.rgRow:not(.rgLoading)"))
                )
                return True

            except Exception as e:
                print(f"Page turn attempt {attempt + 1} failed: {str(e)}")
                self.driver.refresh()
                WebDriverWait(self.driver, 25).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.rgMasterTable"))
                )
                self._human_delay()

        return False

    def _page_state_hash(self):
        """Create unique page fingerprint for verification"""
        try:
            return hash(self.driver.find_element(
                By.CSS_SELECTOR, "table.rgMasterTable").text
                        )
        except:
            return 0

    def _scrape_page(self):
        """Atomic page scraping operation with validation"""
        try:
            # Wait for stable page state
            WebDriverWait(self.driver, 25).until(
                lambda d: d.execute_script(
                    "return document.readyState === 'complete' && "
                    "typeof jQuery !== 'undefined' ? jQuery.active === 0 : true"
                )
            )

            # Get fresh table reference
            table = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.rgMasterTable"))
            )

            # Scrape with stale element protection
            rows = []
            for row in table.find_elements(By.CSS_SELECTOR, "tr.rgRow, tr.rgAltRow"):
                attempts = 0
                while attempts < 2:
                    try:
                        cells = [cell.text.strip() for cell in row.find_elements(By.TAG_NAME, "td")]
                        if len(cells) == len(HEADERS):
                            rows.append(cells)
                        break
                    except StaleElementReferenceException:
                        attempts += 1
                        table = self.driver.find_element(By.CSS_SELECTOR, "table.rgMasterTable")
                        row = table.find_elements(By.CSS_SELECTOR, "tr.rgRow, tr.rgAltRow")[0]

            # Data validation
            if len(rows) < 15:
                raise ValueError(f"Only {len(rows)} rows scraped")

            return rows

        except Exception as e:
            raise RuntimeError(f"Scrape failed: {str(e)}")

    def _emergency_recovery(self):
        """Full system reset on critical failure"""
        print("Initiating emergency recovery...")
        try:
            self.driver.save_screenshot(f"CRASH_PAGE_{self.current_page}.png")
        except:
            pass

        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

        self.driver = self._create_driver()
        self.driver.get(URL)
        self._human_delay()

        # Fast-forward to current page
        if self.current_page > 1:
            print(f"Reinitializing to page {self.current_page}")
            for _ in range(self.current_page - 1):
                if not self._force_page_turn():
                    raise RuntimeError("Recovery failed during fast-forward")

    def run(self):
        """Main execution flow"""
        try:
            # Initialization
            self.driver = self._create_driver()
            self.driver.get(URL)
            time.sleep(INITIAL_DELAY)

            # Load existing data
            all_data = self._load_resume_data()
            self.total_rows = len(all_data)

            # Main scraping loop
            while True:
                try:
                    # Scrape current page
                    start_time = time.time()
                    new_rows = self._scrape_page()

                    # Update data
                    all_data.extend(new_rows)
                    self.total_rows += len(new_rows)

                    # Save progress
                    self._save_progress(all_data)
                    print(f"Page {self.current_page} completed | "
                          f"Rows: {len(new_rows)} | "
                          f"Total: {self.total_rows} | "
                          f"Time: {time.time() - start_time:.1f}s")

                    # Pagination
                    if not self._force_page_turn():
                        print("Reached last page")
                        break

                    self.current_page += 1
                    self.attempt_count = 0
                    self._human_delay()

                except Exception as e:
                    self.attempt_count += 1
                    print(f"Attempt {self.attempt_count} failed: {str(e)}")

                    if self.attempt_count >= MAX_RETRIES:
                        self._emergency_recovery()
                        self.attempt_count = 0

                    self._human_delay()

        finally:
            if self.driver:
                self.driver.quit()
            if os.path.exists(CHECKPOINT_FILE):
                os.remove(CHECKPOINT_FILE)
            print(f"Scraping completed. Total rows: {self.total_rows}")


# ======================
# EXECUTION
# ======================
if __name__ == "__main__":
    scraper = NHISScraper()
    scraper.run()
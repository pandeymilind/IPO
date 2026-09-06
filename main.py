from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import re
import json
import logging
import subprocess
from datetime import datetime

# --- 1. CONFIGURE LOGGING ---
logging.basicConfig(
    filename='scraper.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
)

# --- 2. HELPER FUNCTIONS ---
def get_headless_driver():
    """Helper function to configure and return a headless Chrome driver."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--log-level=3')
    return webdriver.Chrome(options=chrome_options)

def is_company_match(name1, name2):
    """Checks if two company names match after cleaning common suffixes."""
    clean1 = name1.lower().replace('ipo', '').replace('ltd', '').replace('limited', '').strip()
    clean2 = name2.lower().replace('ipo', '').replace('ltd', '').replace('limited', '').strip()
    return clean1 in clean2 or clean2 in clean1

def push_to_github():
    """Automatically commits and pushes data.js to GitHub."""
    try:
        logging.info("Attempting to upload to GitHub...")
        subprocess.run(['git', 'add', 'data.js'], check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Auto-update IPO data'], check=True, capture_output=True)
        subprocess.run(['git', 'push'], check=True, capture_output=True)
        logging.info("✅ Successfully pushed to GitHub.")
        print("✅ Successfully pushed to GitHub.")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode().strip() if e.stderr else "Unknown Git Error"
        # If there's nothing to commit, Git throws an error, which we can safely ignore
        if "nothing to commit" in error_msg or "working tree clean" in error_msg:
            logging.info("No new data to commit. GitHub is already up to date.")
            print("GitHub is already up to date.")
        else:
            logging.error(f"GitHub upload failed: {error_msg}")
            print(f"❌ GitHub Upload Error. Check scraper.log for details.")

# --- 3. SCRAPING FUNCTIONS ---
def get_mainboard_ipos_groww():
    """Scrapes open Mainboard IPOs and their starting/ending dates from Groww."""
    print("Fetching Open IPOs from Groww...")
    logging.info("Fetching Open IPOs from Groww...")
    driver = get_headless_driver()
    mainboard_companies = []

    try:
        driver.get("https://groww.in/ipo/open")
        
        # Wait for the table to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//tbody//tr"))
        )
        
        rows = driver.find_elements(By.XPATH, "//tbody//tr")
        for row in rows:
            try:
                company_name_element = row.find_element(By.XPATH, ".//span[@aria-label='Company name']")
                company_name = company_name_element.text.strip()

                ipo_type_element = row.find_element(By.XPATH, "./td[2]")
                ipo_type = ipo_type_element.text.strip()
                
                # Split columns for Starting and Ending Dates
                columns = row.find_elements(By.TAG_NAME, "td")
                open_date = "N/A"
                close_date = "N/A"
                
                if len(columns) >= 4:
                    open_date = columns[2].text.strip().replace('\n', ' ')
                    close_date = columns[3].text.strip().replace('\n', ' ')
                
                # Store only Mainboard IPOs
                if "Mainboard" in ipo_type:
                    mainboard_companies.append({
                        'Name': company_name,
                        'Starting': open_date,
                        'Ending': close_date
                    })
                    
            except Exception:
                continue
                
    except Exception as e:
        logging.error(f"Groww Scraper Error: {e}")
        print(f"Groww Scraper Error: {e}")
    finally:
        driver.quit()
        
    return mainboard_companies

def scrape_and_compare_ipos(groww_ipos):
    """Scrapes InvestorGain, cross-references with Groww data, and returns a dictionary."""
    print("Fetching GMP data from InvestorGain...")
    logging.info("Fetching GMP data from InvestorGain...")
    driver = get_headless_driver()
    url = "https://www.investorgain.com/report/ipo-gmp-live/331/"
    
    investorgain_data = []
    listed_on_groww = []
    other_mainboards = []
    
    try:
        driver.get(url)
        time.sleep(5)  # Wait for JavaScript table to render
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        table_body = soup.find('tbody', id='tableBody')
        
        if not table_body:
            logging.error("Could not find the table body on InvestorGain.")
            print("Error: Could not find the table body on InvestorGain.")
            return None

        rows = table_body.find_all('tr')
        
        for row in rows:
            if row.has_attr('class') and 'tbody-repeated-header' in row['class']:
                continue
                
            name_cell = row.find('td', {'data-label': 'Name'})
            gmp_cell = row.find('td', {'data-label': 'GMP'})
            
            if name_cell and gmp_cell:
                name_tag = name_cell.find('a')
                ipo_name = name_tag.text.strip() if name_tag else "Unknown Name"
                
                type_badge = name_cell.find('span', class_='bg-secondary')
                ipo_type = type_badge.text.strip() if type_badge else "Unknown"
                
                if ipo_type == "IPO":
                    full_gmp_text = gmp_cell.text
                    match = re.search(r'\((.*?%)\)', full_gmp_text)
                    gmp_percentage = match.group(1) if match else "N/A"
                    
                    investorgain_data.append({
                        'Name': ipo_name,
                        'GMP_Percentage': gmp_percentage
                    })

        # --- CROSS-REFERENCING ---
        matched_ig_names = set()

        for g_item in groww_ipos:
            matched_gmp = "Not found"
            
            for ig_item in investorgain_data:
                if is_company_match(g_item['Name'], ig_item['Name']):
                    matched_gmp = ig_item['GMP_Percentage']
                    matched_ig_names.add(ig_item['Name'])
                    break  
            
            listed_on_groww.append({
                'Name': g_item['Name'],
                'Starting': g_item['Starting'],
                'Ending': g_item['Ending'],
                'GMP_Percentage': matched_gmp
            })

        other_mainboards = [
            ig for ig in investorgain_data 
            if ig['Name'] not in matched_ig_names
        ]

    finally:
        driver.quit()
        logging.info("Browsers closed successfully.")
        
    return {
        "groww_open_ipos": listed_on_groww,
        "other_mainboard_ipos": other_mainboards,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# --- 4. MAIN EXECUTION BLOCK ---
if __name__ == "__main__":
    logging.info("--- Scraper Started ---")
    try:
        # Step 1: Fetch Groww
        groww_active_ipos = get_mainboard_ipos_groww()
        logging.info(f"Found {len(groww_active_ipos)} open Mainboard IPO(s) on Groww.")
        print(f"Found {len(groww_active_ipos)} open Mainboard IPO(s) on Groww.\n")
        
        # Step 2: Cross-reference with InvestorGain
        final_ipo_data = scrape_and_compare_ipos(groww_active_ipos)
        
        # Step 3: Save to JavaScript variable
        if final_ipo_data:
            file_name = "data.js"
            with open(file_name, "w", encoding="utf-8") as js_file:
                js_file.write("const ipoData = ")
                json.dump(final_ipo_data, js_file, indent=4)
                js_file.write(";")
            
            logging.info("Data successfully saved to data.js")
            print(f"✅ Process completed. Data successfully saved to {file_name}")
            
            # Step 4: Automate GitHub Push
            push_to_github()

    except Exception as e:
        logging.error("A critical error occurred during execution.", exc_info=True)
        print("❌ Script crashed. Check scraper.log for details.")
    
    finally:
        logging.info("--- Scraper Finished ---\n")
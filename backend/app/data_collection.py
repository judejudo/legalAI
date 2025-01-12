import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import os

PATH = "C:/Program Files (x86)/chromedriver.exe"
KENYA_LAW = "https://new.kenyalaw.org"
DOWNLOAD_FOLDER = "data"
URL = "https://new.kenyalaw.org/judgments/court-class/environment-and-land-tribunals/"

service = Service(PATH)
driver = webdriver.Chrome(service=service)

def get_pdf_links_from_current_page():
    """
    Extract PDF links from the current page using BeautifulSoup.
    """
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    pdf_links = []

    for link in soup.find_all('a', href=True):
        
        if "judgment/" in link['href'] and "/20" in link['href']:
            full_link = KENYA_LAW + link['href']
            pdf_links.append(full_link)

    return pdf_links

def navigate_year(year):
    """
    Navigate to the specified year and get PDF links for all pages.
    """
    url = URL + str(year) + '/'
    driver.get(url)

    all_pdf_links = []

    while True:
        try:
            
            all_pdf_links.extend(get_pdf_links_from_current_page())
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'page-link') and text()='Next']"))
            )

            driver.execute_script("arguments[0].scrollIntoView();", next_button)
            time.sleep(2)  
            driver.execute_script("arguments[0].click();", next_button)

            time.sleep(4)  # Wait for the page to load
        except Exception as e:
            print(f"Reached the end for year {year} or error: {e}")
            break

    # Return the collected PDF links
    return list(set(all_pdf_links))

def navigate_years(start_year, end_year):
    """
    Navigate through multiple years, from start_year to end_year (decreasing).
    """
    all_pdf_links = []
    
    for year in range(start_year, end_year - 1, -1):
        print(f"Navigating year: {year}")
        # Get PDF links for the current year
        pdf_links = navigate_year(year)
        all_pdf_links.extend(pdf_links)
        print(len(all_pdf_links))

        # Scroll to the top of the page once we've finished a year
        driver.execute_script("window.scrollTo(0, 0);")
        
        # Find the link for the next year (the year before the current year)
        next_year_link = driver.find_element(By.XPATH, f"//a[contains(@href, '{year - 1}')]")
        driver.execute_script("arguments[0].click();", next_year_link)

        # Wait for the page to load before continuing
        time.sleep(4)

    return all_pdf_links

def download_pdf(pdf_url, file_name):
    """
    Downloads the PDF from the given URL and saves it to the specified file path.
    """
    try:
        response = requests.get(pdf_url)
        response.raise_for_status()  # Check if the request was successful
        file_path = os.path.join(DOWNLOAD_FOLDER, file_name)

        with open(file_path, 'wb') as f:
            f.write(response.content)
        print(f"Downloaded: {file_name}")
    except Exception as e:
        print(f"Error downloading {file_name}: {e}")

def get_download_link_from_redirected_page():
    """
    After opening the redirected page, extract the actual PDF download link.
    """
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    download_link_tag = soup.find('a', class_='btn btn-primary btn-shrink-sm', href=True)
    
    if download_link_tag:
        return KENYA_LAW + download_link_tag['href']
    else:
        print("Download link not found.")
        return None
    
def follow_pdf_links_and_get_download(pdf_links):
    """
    Follow each PDF link, open the redirected page, and extract the download link.
    """
    all_download_links = []

    for link in pdf_links:
        try:
            print(f"Following link: {link}")
            driver.get(link)
            time.sleep(3)  # Allow the page to load

            # Get the actual PDF download link from the redirected page
            download_link = get_download_link_from_redirected_page()
            if download_link:
                all_download_links.append(download_link)
        except Exception as e:
            print(f"Error processing link {link}: {e}")

    return all_download_links

def download_pdfs(pdf_urls):
    """
    Given a list of PDF URLs, download each PDF and save it locally.
    """
    for i, pdf_url in enumerate(pdf_urls):
        # Generate a unique file name for each PDF
        file_name = f"pdf_new{i+1}.pdf"
        download_pdf(pdf_url, file_name)

# Run the scraper
try:
    start_year = 2023
    end_year = 2023
    all_pdf_links = navigate_years(start_year, end_year)
    download_links = follow_pdf_links_and_get_download(all_pdf_links)
    download_pdfs(download_links)

finally:
    driver.quit()


# Contains code for scraping(selenium) and downloading (FastDL.app) posts/reels.

# ===================================================================================================================================================================================================================
#                                                                                                     :For Downloading Posts(Simple/Carousel):
# ===================================================================================================================================================================================================================

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


from utils import open_and_login_instagram, wait_for_download_trial, remove_ads, sort_downloaded_media, get_instagram_links, USERNAME

def download_from_fastdl_allclicks(post_links, target_profile):

    if not post_links:
        return

    start_time = time.time()
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    download_folder = f"{target_profile}_{timestamp}"
    os.makedirs(download_folder, exist_ok=True)
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("prefs", {
        "profile.default_content_settings.popups": 0,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.content_settings.exceptions.automatic_downloads.*.setting": 1,
        "download.default_directory": os.path.abspath(download_folder)
    })
    
    driver = webdriver.Chrome(options=options)
    driver.get("https://fastdl.app/carousel")
    time.sleep(5)

    total_buttons = 0
    successful_downloads = 0
    
    for count, post_url in enumerate(post_links):
        print(f"📥 Processing {count + 1}: {post_url}")
        try:
            wait = WebDriverWait(driver, 10)
            
            if count > 0:
                driver.refresh()
                time.sleep(3)
            
            input_xpath = '//*[@id="search-form-input"]'
            input_box = wait.until(EC.presence_of_element_located((By.XPATH, input_xpath)))
            input_box.send_keys(Keys.CONTROL + "a")
            input_box.send_keys(Keys.DELETE)
            input_box.send_keys(post_url)
            input_box.send_keys(Keys.RETURN)
            
            time.sleep(3)  # Adjust based on internet speed
            
            first_image_xpath = "//section[2]//ul[1]//li//div[1]//img"
            try:
                wait.until(EC.visibility_of_element_located((By.XPATH, first_image_xpath)))
                print("✅ First image loaded successfully.")
            except:
                print("⚠️ First image took too long to load.")
                time.sleep(3)
            
            # Scroll down to ensure all buttons are visible
            for _ in range(5):
                driver.execute_script("window.scrollBy(0, 300);")
                time.sleep(1)
            
            download_button_xpath =  "//section[2]//ul[1]//li//div[2]//a"
            download_buttons = wait.until(EC.presence_of_all_elements_located((By.XPATH, download_button_xpath)))
            total_buttons += len(download_buttons)
            print(f'{len(download_buttons)} download buttons found.')
            
            # Click all download buttons at once using JavaScript
            for btn in download_buttons:
                remove_ads(driver=driver)
                # Making sure we are trying JS as well as Selenium to click buttons in case one fails. Ensures all media downloads.
                try:
                    btn.click()
                except:
                    driver.execute_script("arguments[0].click();", btn)
            
            print("🖱️ Attempted to click all download buttons simultaneously.")

            # Wait to let downloads start
            time.sleep(10)

        except Exception as e:
            print(f"⚠️ Error downloading {post_url}: {e}")
    
    sort_downloaded_media(download_folder)

    print("✅ Downloading posts completed!")
    print(f"📊 Total buttons found: {total_buttons}")
    
    end_time = time.time()
    print(f"⏱ Total time taken: {end_time - start_time:.2f} seconds.")

post_links = get_instagram_links(profile_username=USERNAME, media_type="posts")
download_from_fastdl_allclicks(post_links=post_links, target_profile=USERNAME)

# ===================================================================================================================================================================================================================
#                                                                                                     :For Downloading Reels:
# ===================================================================================================================================================================================================================

def download_reels_from_fastdl_2(post_links, target_profile):
    """Downloads an Instagram reel from fastdl.app."""
    start_time = time.time()
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    download_folder = f"{target_profile}_{timestamp}"
    os.makedirs(download_folder, exist_ok=True)
    
    options = Options()
    # options.add_argument("--headless")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("prefs", {
        "profile.default_content_settings.popups": 0,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.content_settings.exceptions.automatic_downloads.*.setting": 1,
        "download.default_directory": os.path.abspath(download_folder)
    })
    driver = webdriver.Chrome(options=options)
    driver.get("https://fastdl.app/instagram-reels-download")

    for count, post_url in enumerate(post_links):
        print(f"📥 Processing {count + 1}: {post_url}")
        try:
            wait = WebDriverWait(driver, 10)
            
            # This refreshes the driver after first post wwhich is quivlent of gettig to home page for another url insertion 
            if count > 0:
                driver.refresh()
                time.sleep(3)
            
            input_xpath = '//*[@id="search-form-input"]'
            input_box = wait.until(EC.presence_of_element_located((By.XPATH, input_xpath)))
            input_box.send_keys(Keys.CONTROL + "a")
            input_box.send_keys(Keys.DELETE)
            input_box.send_keys(post_url)
            input_box.send_keys(Keys.RETURN)
            time.sleep(3)

            # Scroll down to load all images in the carousel
            for _ in range(3):  # Adjust number of scrolls if needed
                driver.execute_script("window.scrollBy(0, 300);")  # Scroll step by step
                time.sleep(1)
            
            download_button_xpath = "//section[2]//ul[1]//li//div[2]//a"
            download_button = wait.until(EC.presence_of_element_located((By.XPATH, download_button_xpath)))
            
            try:
                remove_ads(driver=driver)
                # download_button.location_once_scrolled_into_view
                # driver.execute_script("window.scrollBy(0, -200);")
                time.sleep(5)
                try:
                    download_button.click()
                    print("Clicking button normal")
                except:
                    driver.execute_script("arguments[0].click();", download_button)
                    print("Clicking button JS")
                
                print(f'✅ Clicked the download button.')

                wait_for_download_trial(download_folder=download_folder)

            except Exception as e:
                print(f"❌ Failed to click the button: {e}")
        except Exception as e:
            print(f"⚠️ Error downloading {post_url}: {e}")

    sort_downloaded_media(main_folder=download_folder)
    print("✅ Download completed.")

    driver.quit()

post_links = get_instagram_links(profile_username=USERNAME, media_type="reels")
download_reels_from_fastdl_2(post_links=post_links, target_profile=USERNAME)



import os
import re
import glob
import wget
import time
import shutil
import base64
import random 
import pickle
import requests
import instaloader
import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC

USERNAME = "YOUR INSTAGRAM USERNAME"
PASSWORD = "YOUR INSTAGRAM PASSWORD"
TARGET_PROFILE = "TARGET PROFILE USERNAME"

# After first loging data will be saved in .pkl file to avoid repetative logings.
COOKIES_FILE = "instagram_cookies.pkl"

# ==============================================================================================================================================================================================================
#                                                                                                   :HELPER FUCTIONS:
# ==============================================================================================================================================================================================================

def save_cookies(driver, file_path):
    """ Save cookies to a file """
    cookies = driver.get_cookies()
    if cookies:
        with open(file_path, "wb") as file:
            pickle.dump(cookies, file)
        print("✅ Cookies saved successfully!")
    else:
        print("❌ No cookies found!")

def load_cookies(driver, file_path):
    """ Load cookies from a file """
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        driver.get("https://www.instagram.com/")  # Open Instagram before adding cookies
        with open(file_path, "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                driver.add_cookie(cookie)
        return True
    return False

def login_instagram(driver):
    """ Automate Instagram login using Selenium """
    driver.get("https://www.instagram.com/accounts/login/")
    wait = WebDriverWait(driver, 15)  # Wait up to 15 seconds for elements to load

    # Find and enter username
    username_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
    username_input.send_keys(USERNAME)

    # Find and enter password
    password_input = driver.find_element(By.NAME, "password")
    password_input.send_keys(PASSWORD)
    time.sleep(1)  # Short delay to mimic human typing

    # Click login button
    login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
    login_button.click()
    print("🔑 Logging in...")

    time.sleep(5)

    # Click "Save Info" button if it appears
    try:
        save_info_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Save Info')]")))
        save_info_button.click()
        print("✅ 'Save Info' clicked.")
    except:
        print("ℹ️ 'Save Info' not found, skipping.")

    time.sleep(5)  # Wait for full login completion
    save_cookies(driver, COOKIES_FILE)  # Save cookies after login
    print("✅ Login successful! Cookies saved.")

def open_and_login_instagram():
    """ Open Instagram with Selenium & handle login automatically """
    options = Options()
    # options.add_argument("--headless")
    options.add_argument("--start-maximized")
    options.add_argument("--enable-unsafe-swiftshader")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get("https://www.instagram.com/")
    time.sleep(5)

    if load_cookies(driver, COOKIES_FILE):
        print("✅ Loaded cookies successfully.")
        driver.refresh()
        print("✅ Login successful! Ready to scrape.")
        time.sleep(5)
    else:
        print("❌ No saved cookies found. Logging in...")
        login_instagram(driver)

    return driver

# Function to convert image to Base64 for inline display:
def get_base64_image(image_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(image_url, headers=headers)

    if response.status_code == 200:
        image_data = base64.b64encode(response.content).decode("utf-8")
        return f"data:image/jpeg;base64,{image_data}"
    return None  # Return None if image fetch fails

# Cleanes bio info in case of extra spaces:
def clean_bio(bio):
    if bio:
        bio = re.sub(r'<[^>]+>', '', bio)  # Remove HTML tags
        return bio.strip()
    return ""

# Formates the follower count in thousand format (10,100 ==> 10.1k):
def format_followers_count(count):
    """Formats followers count like '10.1k' for numbers above 10,000."""
    return f"{count / 1000:.1f}k" if count >= 10_000 else f"{count}"

# Loads CSS from styles.css:
def load_css():
    with open("styles.css", "r") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# Loads Profile data:
def load_html(profile_data):
    # Profile Layout
    profile_pic_base64 = get_base64_image(profile_data['profile_pic_url'])

    profile_html = f"""
    <div class="profile-container">
        <img src="{profile_pic_base64}" class="profile-pic">
        <div class="profile-details">
            <div class="profile-name">
                {profile_data['username']}
    """
    if profile_data["is_verified"]:
        profile_html += """<img src='https://www.flaticon.com/free-icon/verified_7641727?term=verified&page=1&position=4&origin=tag&related_id=7641727' width='20'>"""
    
    profile_html += "</div>" #!Important
    profile_html += f"""
            <div class="profile-stats">
                <span><strong>{profile_data['total_posts']}</strong> <span class="label">posts</span></span>
                <span><strong>{format_followers_count(profile_data['followers'])}</strong> <span class="label">followers</span></span>
                <span><strong>{profile_data['following']}</strong> <span class="label">following</span></span>
            </div>
            <div class="profile-bio">
                <strong>{profile_data['name']}</strong><br>
            </div>
    """
    return profile_html

# Cleanup function use after download_instaloader() to delete extra(metadata) files: 
def cleanup_non_image_files(download_folder):
    """Remove all non-image and non-video files from the given folder."""
    for file in glob.glob(os.path.join(download_folder, "*")):
        if not file.endswith((".jpg", ".png", ".jpeg", ".mp4")):  
            os.remove(file)
            print(f"🗑 Deleted: {file}")

# Waits for reels/videos to completely download, removing chances of getting half downloaded corrupted files.
def wait_for_download_trial(download_folder, check_interval=3, max_wait_time=15, stuck_threshold=10):
    """
    Waits until a new file starts downloading, then waits until it is fully downloaded.
    Handles stuck downloads by monitoring file size.
    
    - check_interval: How often to check for new files (in seconds).
    - max_wait_time: Maximum allowed time per download (in seconds).
    - stuck_threshold: Time limit (in seconds) to detect a stuck download.
    """
    existing_files = set(os.listdir(download_folder))  # Track initial files
    elapsed_time = 0

    while elapsed_time < max_wait_time:
        current_files = set(os.listdir(download_folder))
        new_files = current_files - existing_files  # Detect new downloads

        if new_files:
            print(f"📂 New download detected: {new_files}")
            start_time = time.time()

            while True:
                downloading_files = [f for f in os.listdir(download_folder) if f.endswith((".crdownload", ".tmp", ".temp"))]
                
                # ✅ If no more partial files, download is complete
                if not downloading_files:
                    print("✅ Download complete.")
                    return

                # ⏳ Check for stuck downloads
                stuck_start_time = None
                for file in downloading_files:
                    file_path = os.path.join(download_folder, file)
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)

                        # If file size hasn't changed for `stuck_threshold`, assume it's stuck
                        if "last_size" not in locals():
                            last_size = file_size
                        if file_size == last_size:
                            if stuck_start_time is None:
                                stuck_start_time = time.time()
                            if time.time() - stuck_start_time > stuck_threshold:
                                print(f"❌ Stuck download detected. Removing: {file}")
                                os.remove(file_path)  # Delete stuck file
                                return
                        else:
                            stuck_start_time = None  # Reset stuck timer if progress is made
                        last_size = file_size

                        print(f"⏳ Downloading... {file_size / (1024 * 1024):.2f} MB")

                # ❌ Timeout check
                if time.time() - start_time > max_wait_time:
                    print(f"❌ Timeout: Download taking too long. Skipping file: {downloading_files}")
                    return
                
                time.sleep(2)  # Wait before checking again

        print("⏳ No new downloads yet, checking again...")
        time.sleep(check_interval)
        elapsed_time += check_interval

    print(f"❌ Timeout: Failed downloading {new_files}")

# Removes any JS ads
def remove_ads(driver):
    try:
        driver.execute_script("""
            // Remove all iframes (ads often use iframes)
            let iframes = document.getElementsByTagName('iframe');
            for (let i = iframes.length - 1; i >= 0; i--) {
                iframes[i].parentNode.removeChild(iframes[i]);
            }

            // Remove all overlay divs with IDs starting with 'aswift_'
            let overlayDivs = document.querySelectorAll("[id^='aswift_'], [class*='overlay'], [class*='popup']");
            for (let div of overlayDivs) {
                div.parentNode.removeChild(div);
            }

            // Remove fixed elements (ads that stay on screen)
            let fixedElems = document.querySelectorAll("*[style*='fixed']");
            for (let elem of fixedElems) {
                elem.parentNode.removeChild(elem);
            }

            console.log("🛑 Removed ad iframes, overlays, and fixed elements.");
        """)
    except Exception as e:
        print(f"⚠️ Could not remove iframes/ads: {e}")

def sort_downloaded_media(main_folder):
    posts_folder = os.path.join(main_folder, "Posts")
    videos_folder = os.path.join(main_folder, "Reels")

    # Create subfolders if they don't exist
    os.makedirs(posts_folder, exist_ok=True)
    os.makedirs(videos_folder, exist_ok=True)

    # Define file extensions
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
    video_extensions = ('.mp4', '.mov', '.avi', '.mkv')

    # Loop through files in the main folder
    for file in os.listdir(main_folder):
        file_path = os.path.join(main_folder, file)

        if os.path.isfile(file_path):  # Ensure it's a file, not a folder
            if file.lower().endswith(image_extensions):
                shutil.move(file_path, os.path.join(posts_folder, file))
            elif file.lower().endswith(video_extensions):
                shutil.move(file_path, os.path.join(videos_folder, file))

    print(f"✅ Media sorted successfully in {main_folder}")

def download_images(image_urls, target_profile):
    """
    Downloads images from a list of URLs.

    :param image_urls: List of image URLs
    :param folder_name: Folder to save images (default: "downloaded_images")
    """
    # Create a unique folder name using timestamp and target profile
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    folder_name = f"{target_profile}_images_{timestamp}"
    save_folder = os.path.join(os.getcwd(), folder_name)
    
    os.makedirs(save_folder, exist_ok=True)

    print(f"Downloading {len(image_urls)} images...")
    
    for idx, img_url in enumerate(image_urls):
        save_path = os.path.join(save_folder, f"image_{idx}.jpg")

        if os.path.exists(save_path):
            print(f"Skipping {save_path}, already exists.")
            continue
        
        wget.download(img_url, save_path)
        print(f"Downloaded: {save_path}")

    print("Download complete!")

def get_instagram_profile_data(username, password, target_profile):
    # ✅ Initialize Instaloader
    L = instaloader.Instaloader()

    # ✅ Login to Instagram
    try:
        L.load_session_from_file(username)  # Load session if available
        print("✅ Session loaded successfully!")
    except:
        print("🔑 Logging in to Instagram...")
        L.login(username, password)  # Login manually
        L.save_session_to_file()  # Save session for future use
        print("✅ Login successful!")

    # ✅ Load Profile
    profile = instaloader.Profile.from_username(L.context, target_profile)

    # ✅ Extract Profile Details
    profile_data = {
        "name": profile.full_name,
        "username": profile.username,
        "bio": profile.biography,
        "followers": profile.followers,
        "following": profile.followees,
        "total_posts": profile.mediacount,
        "profile_pic_url": profile.profile_pic_url,
        "is_verified": getattr(profile, "is_verified", False)  # Fix here
    }
    return profile_data

def get_instagram_links(profile_username, media_type):
    """
    Scrapes Instagram post/reel links from a given profile.

    Args:
        profile_username (str): The Instagram username of the profile.
        media_type (str): "posts", "reels", or "both".

    Returns:
        list: A list of Instagram post/reel links.
    """
    start_time = time.time()
    
    driver = open_and_login_instagram()  # Assuming this function logs in and returns the driver
    
    media_types = {
        "posts": "p",
        "reels": "reel"
    }

    all_links = set()  # Stores all links (posts + reels)
    post_links = set()  # Stores only post links
    reel_links = set()  # Stores only reel links

    def scrape_links(content_type):
        """Helper function to scrape links based on media type."""
        profile_url = f"https://www.instagram.com/{profile_username}/{content_type}"
        driver.get(profile_url)
        time.sleep(5)  # Wait for content to load

        post_xpath = f"//a[contains(@href, '/{media_types[content_type]}/')]"

        last_height = driver.execute_script("return document.body.scrollHeight")

        temp_links = set()  # Temporary set to track this type only

        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)

            try:
                posts = WebDriverWait(driver, 5).until(
                    EC.presence_of_all_elements_located((By.XPATH, post_xpath))
                )
                for post in posts:
                    link = post.get_attribute("href")
                    if link and link not in temp_links:  # Avoid duplicates within this type
                        temp_links.add(link)
            except Exception as e:
                st.error(f"⚠️ Error finding {content_type}: {e}")
                break

            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        return temp_links

    # Scrape based on user selection
    if media_type in ["posts", "both"]:
        post_links = scrape_links("posts")
        all_links.update(post_links)

    if media_type in ["reels", "both"]:
        reel_links = scrape_links("reels")
        reel_links -= post_links  # Remove duplicates
        all_links.update(reel_links)

    st.write(f'\n🔍 **Total:** {len(post_links)} posts + {len(reel_links)} reels found.')

    end_time = time.time()
    st.write(f"\n⏱ **Total time taken to extract links:** {end_time - start_time:.2f} seconds.")
    print(list(all_links))
    
    return list(all_links)


# ==============================================================================================================================================================================================================
#                                                                                          :POST / CARAOUSAL / REELS DOWNLOAD FUNCTIONS:
# ==============================================================================================================================================================================================================

# INSTALOADER APPROACH | Works for both posts/reels (BETTER AND FASTER FOR SMALLER SIZE PROFILE):
def download_instaloader(post_links, target_profile, username, password):

    start_time = time.time()

    target_profile = target_profile
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = target_profile + '_downloads_' + timestamp

    # ✅ Create folder for downloads
    os.makedirs(folder_name, exist_ok=True)

    # ✅ Initialize Instaloader
    L = instaloader.Instaloader(
        download_comments=False, 
        download_geotags=False, 
        download_video_thumbnails=False,
        save_metadata = False,
        compress_json = False 
    )

    # ✅ Login to Instagram
    try:
        L.load_session_from_file(username)  # Load session if available
        print("✅ Session loaded successfully!")
    except:
        print("🔑 Logging in to Instagram...")
        L.login(username, password)  # Login manually
        L.save_session_to_file()  # Save session for future use
        print("✅ Login successful!")

    for count, post_url in enumerate(post_links):
        print(f"📥 Processing {count + 1}: {post_url}")

        try:
            # ✅ Extract post shortcode from URL
            shortcode = post_url.split("/")[-2]

            # ✅ Load Post
            post = instaloader.Post.from_shortcode(L.context, shortcode)

            # ✅ Download Post
            L.download_post(post, target=folder_name)

            print(f"✅ Downloaded: {post_url}")

            # ✅ Dynamic Sleep to Avoid Rate Limit
            sleep_time = random.randint(1, 5)
            L.context.sleep(sleep_time)

            end_time = time.time()
            print(f"⏱ Total time taken: {end_time - start_time:.2f} seconds.")

        except Exception as e:
            pass

    print("✅ Download process completed!")

# ==============================================================================================================================================================================================================
#                                                                                       :FASTDL APPROACH (BETTER FOR BULK DOWNLOAD):
# ==============================================================================================================================================================================================================

#seperate_clicks==> 89.27s
def download_from_fastdl(post_links, target_profile):
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
        "download.default_directory": os.path.abspath(download_folder)  # Set download directory
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
            
            # This time.sleep() might depends on the internetspeed and local hardware,
                # if speed is slow or hardware is basic then increse sleep time.
            time.sleep(3) # Tweak this time to get faster results,but can get caught as bot if too low. default = 5 sec
            
            first_image_xpath = "//section[2]//ul[1]//li//div[1]//img"
            try:
                wait.until(EC.visibility_of_element_located((By.XPATH, first_image_xpath)))
                print("✅ First image loaded successfully.")
            except:
                print("⚠️ First image took too long to load.")
                time.sleep(3)
            
            # Scroll down to load all images in the carousel
            for _ in range(5):  # Adjust number of scrolls if needed
                driver.execute_script("window.scrollBy(0, 300);")  # Scroll step by step
                time.sleep(1)
            
            download_button_xpath =  "//section[2]//ul[1]//li//div[2]//a"
            download_buttons = wait.until(EC.presence_of_all_elements_located((By.XPATH, download_button_xpath)))
            total_buttons += len(download_buttons)
            print(f'{len(download_buttons)} posts found.')
            
            for btn in download_buttons:
                try:
                    remove_ads(driver)
                    btn.location_once_scrolled_into_view
                    time.sleep(1)
                    attempts = 3
                    # Makes 3 tries to het the download button to be clickable if that does not happen then it skpis that post
                    for attempt in range(attempts):
                        try:
                            wait.until(EC.element_to_be_clickable(btn)).click()
                            print(f'✅ Clicked the download button (Attempt {attempt + 1}).')
                            successful_downloads += 1
                            break
                        except Exception as e:
                            print(f"Retry attempt {attempt + 1} failed: {e}")
                            time.sleep(2) # Waiting 2 sec before another attempt to mimic human behaviour.
                    else:
                        print("❌ Unable to click the button after retries.")
                    
                    time.sleep(5)
                    try:
                        alert = driver.switch_to.alert
                        alert.dismiss()
                        print("🛑 Closed popup alert.")
                    except:
                        pass
                    
                    # Checks if there are multiple window opened due to ads, if yes then goes to other window and closes it.
                    if len(driver.window_handles) > 1:
                        driver.switch_to.window(driver.window_handles[1]) # That other window with ad.
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0]) # Main page 
                        print("🛑 Closed new tab.")
                        
                except Exception as e:
                    print(f"❌ Failed to click the button: {e}")
        except Exception as e:
            print(f"⚠️ Error downloading {post_url}: {e}")
    
    success_rate = (successful_downloads / total_buttons * 100) if total_buttons > 0 else 0
    print("✅ Download process completed!")
    print(f"📊 Total buttons found: {total_buttons}")
    print(f"📥 Total images downloaded: {successful_downloads}")
    print(f"🎯 Download success rate: {success_rate:.2f}%")
    
    end_time = time.time()
    print(f"⏱ Total time taken: {end_time - start_time:.2f} seconds.")

# This function saves carousel posts by clicking all the button simultaneously to save 50% time. allclicks==> 44.89s
# Working all clicks correctly ✅✅✅
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

# Works for reels correctly ✅✅✅:
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
# ==============================================================================================================================================================================================================
#                                                                                                   :LOCAL DOWNLOADS:
# ==============================================================================================================================================================================================================

# No caraousal but working✅✅✅:
def get_instagram_no_carousel_images_local(username, max_posts=10):
    """
    Extracts image URLs from an Instagram profile without opening each post.
    Filters out small images like profile pictures and highlights.

    :param username: Instagram username
    :param max_posts: Number of posts to extract
    :return: List of post image URLs
    """
    driver = open_and_login_instagram()  # Ensure this function logs in before proceeding
    driver.get(f"https://www.instagram.com/{username}/")
    time.sleep(5)  # Allow initial page load

    post_images = set()
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_attempts = 0
    max_scrolls = 15  # Increased number of scroll attempts

    while len(post_images) < max_posts and scroll_attempts < max_scrolls:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)  # Slightly reduced sleep time for efficiency

        new_height = driver.execute_script("return document.body.scrollHeight")

        # Extract images after scrolling
        img_elements = driver.find_elements("tag name", "img")
        for img in img_elements:
            img_url = img.get_attribute("src")
            if img_url:
                width = int(img.get_attribute("width") or 0)
                height = int(img.get_attribute("height") or 0)

                if width >= 300 and height >= 300:
                    post_images.add(img_url)

        if new_height == last_height:  # If no new content loads, break
            break

        last_height = new_height
        scroll_attempts += 1

    driver.quit()

    # Convert set to list and limit to max_posts
    post_images = list(post_images)[:max_posts]
    print(f"Extracted {len(post_images)} post images from the profile grid.")
    return post_images


# 🚨🚨🚨 Last Image not adding. 
def get_instagram_carousel_local(username, max_posts):
    start_time = time.time()

    driver = open_and_login_instagram()
    driver.get(f"https://www.instagram.com/{username}/")
    time.sleep(5)

    # Scroll dynamically to load posts
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_attempts = 0

    while scroll_attempts < 5:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        scroll_attempts += 1

    # Extract all post links from profile grid
    anchors = driver.find_elements(By.TAG_NAME, "a")
    post_links = {a.get_attribute("href") for a in anchors if "/p/" in str(a.get_attribute("href"))}
    
    # Limit to max_posts
    post_links = list(post_links)[:max_posts]
    print(f"Found {len(post_links)} posts")

    all_images = set()

    # Visit each post and extract images (including carousel)
    for post in post_links:
        driver.get(post)
        time.sleep(5)

        while True:
            try:
                # Get the currently visible image
                img_element = driver.find_element(By.XPATH, "//img[@style and not(ancestor::div[contains(@style, 'display: none')])]")
                img_url = img_element.get_attribute("src")

                if img_url and img_url not in all_images:
                    all_images.add(img_url)  # ✅ Always add the current image

                # Try clicking the "Next" button if it exists
                next_button = driver.find_element(By.XPATH, "//button[@aria-label='Next']")
                next_button.click()
                time.sleep(2)  # Wait for next image to load

            except NoSuchElementException:
                # 🚀 **FIX: Extract last image BEFORE breaking the loop**
                img_element = driver.find_element(By.XPATH, "//img[@style and not(ancestor::div[contains(@style, 'display: none')])]")
                last_img_url = img_element.get_attribute("src")

                if last_img_url and last_img_url not in all_images:
                    all_images.add(last_img_url)  # ✅ Capture last image before breaking
                
                break  # No more images, exit loop

    driver.quit()

    print(f"Extracted {len(all_images)} unique images from {len(post_links)} posts.")
    
    end_time = time.time()
    print(f'⏱ Time taken to get {len(all_images)} images is {end_time - start_time:.2f} seconds.')

    print(all_images)
    return list(all_images)
    

# ==============================================================================================================================================================================================================
#                                                                                                    :HASHTAG SCRAPER LOCAL:
# ==============================================================================================================================================================================================================

# Works correctly for hashtag scraping. ✅✅✅
def get_instagram_hashtag_local(hashtag, max_posts=10):
    driver = open_and_login_instagram()
    driver.get(f"https://www.instagram.com/explore/search/keyword/?q=%23{hashtag}")
    time.sleep(5)  

    post_images = set()
    last_height = driver.execute_script("return document.body.scrollHeight")
    base_sleep_time = 2  # Start with 2 seconds
    max_sleep_time = 10  # Cap max wait time at 10 seconds

    while len(post_images) < max_posts:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(10)  # Shorter sleep for faster scrolling

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:  # No more content to load
            break  
        last_height = new_height  

        # Extract images dynamically
        img_elements = driver.find_elements(By.TAG_NAME, "img")

        for img in img_elements:
            img_url = img.get_attribute("src")
            if img_url:
                post_images.add(img_url)
            if len(post_images) >= max_posts:  # Stop if enough images
                break
        base_sleep_time = min(base_sleep_time + 1, max_sleep_time)

    driver.quit()
    print(f"Extracted {len(post_images)} post images for #{hashtag} from the hashtag grid.")
    print(list(post_images))
    return list(post_images)

# ==============================================================================================================================================================================================================
#                                                                                                  :PROFILE STREAMLIT:
# ==============================================================================================================================================================================================================

# def show_sidebar():

#     # Add FontAwesome CDN to load icons
#     st.markdown("""
#         <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
#     """, unsafe_allow_html=True)

#     # ✅ Inject custom CSS to style the sidebar width
#     st.markdown(
#         """
#         <style>
#             section[data-testid="stSidebar"] {
#                 width: 300px !important; /* Set the width */
#             }
            
#             /* Style input fields */
#             [data-testid="stTextInput"] input {
#                 padding-left: 40px !important; /* Shift text inside input */
#                 background-repeat: no-repeat;
#                 background-position: 10px center;
#                 background-size: 18px;
#             }

#             /* Specific icons for each input field */
#             div:has(> input[aria-label="Instagram Username"]) input {
#                 background-image: url("https://cdn-icons-png.flaticon.com/128/1077/1077114.png"); /* User icon */
#             }

#             div:has(> input[aria-label="Instagram Password"]) input {
#                 background-image: url("https://cdn-icons-png.flaticon.com/128/18994/18994227.png"); /* Lock icon */
#             }

#             div:has(> input[aria-label="Target Profile"]) input {
#                 background-image: url("https://cdn-icons-png.flaticon.com/128/15707/15707776.png"); /* Profile icon */
#             }
#         </style>
#         """,
#         unsafe_allow_html=True,
#     )

#     # ✅ Ensure session state variables are initialized
#     if "username" not in st.session_state:
#         st.session_state.username = ""

#     if "password" not in st.session_state:
#         st.session_state.password = ""

#     if "target_profile" not in st.session_state:
#         st.session_state.target_profile = ""

#     if "media_type" not in st.session_state:
#         st.session_state.media_type = "posts"  # Default to None

#     if "download_method" not in st.session_state:
#         st.session_state.download_method = "FastDL"  # Default selection

#     # ✅ Sidebar Inputs
#     st.sidebar.markdown("""
#         <style>
#             .sidebar-title {
#                 display: flex;
#                 align-items: center;
#                 gap: 8px;  /* Adjusts spacing between icon and text */
#                 padding-left: 5px;
#                 margin-left: 50px;
#             }
#             .sidebar-title i {
#                 font-size: 20px; /* Adjust icon size */
#             }
#             .sidebar-title h2 {
#                 font-size: 20px; /* Adjust text size */
#             }
#         </style>
#         <div class="sidebar-title">
#             <i class="fas fa-cog"></i>  
#             <h2>Settings</h2>
#         </div>
#     """, unsafe_allow_html=True)
    
#     # Reduces extra padding on the sidebar header:
#     st.markdown(
#         """
#         <style>
#             [data-testid="stSidebarHeader"] {
#             padding: 0px;
#             }
#         </style>
#         """,
#         unsafe_allow_html=True,
#     )

#     # Getting data from inputs and saving them into st.session_state:
#     username = st.sidebar.text_input("Instagram Username", 
#                                      placeholder="Username", 
#                                      value=st.session_state.username)
#     st.session_state.username = username  # Always update session state

#     password = st.sidebar.text_input("Instagram Password", 
#                                      type="password", 
#                                      placeholder="Password", 
#                                      value=st.session_state.password)
#     st.session_state.password = password

#     target_profile = st.sidebar.text_input("Target Profile", 
#                                            placeholder="Target profile username", 
#                                            value=st.session_state.target_profile)
#     st.session_state.target_profile = target_profile

#     st.sidebar.markdown("---")

#     # ✅ Media Type Selection
#     st.sidebar.markdown("##### Media Type: ")
#     col1, col2 = st.sidebar.columns([1, 1])

#     with col1:
#         posts_selected = st.toggle("Posts", value=True, key="posts_selected")

#     with col2:
#         reels_selected = st.toggle("Reels", value=False, key="reels_selected")

#     # ✅ Determine media type based on selection
#     if posts_selected and reels_selected:
#         st.session_state["media_type"] = "both"
#     elif posts_selected:
#         st.session_state["media_type"] = "posts"
#     elif reels_selected:
#         st.session_state["media_type"] = "reels"
#     else:
#         st.session_state["media_type"] = None  # This case shouldn't normally occur

#     # ✅ Download Method Selection
#     st.sidebar.markdown("##### Download Method: ")
#     st.session_state.download_method = st.sidebar.radio(
#         "Select Download Method: ",
#         ["Instaloader", "FastDL"],
#         horizontal=True,  # Keep buttons in one row
#         label_visibility="collapsed" #Important seting "collapsed" in order to make title of media-type and download method look same.
#     )

# def load_profile(username, password, target_profile):
#     # Initialize session state variables
#     if "fetch_clicked" not in st.session_state:
#         st.session_state.fetch_clicked = False
#     if "last_loaded_profile" not in st.session_state:
#         st.session_state.last_loaded_profile = None  # Track last loaded profile
#     if "profile_info" not in st.session_state:
#         st.session_state.profile_info = None  # Ensure profile data persists

#     # Sidebar button to fetch profile
#     if st.sidebar.button("Fetch Profile"):
#         st.session_state.fetch_clicked = True  # Button clicked flag

#     # Only fetch if button clicked AND target_profile changed
#     if st.session_state.fetch_clicked and target_profile != st.session_state.last_loaded_profile:
#         if not target_profile:
#             st.sidebar.error("⚠️ Target profile is missing!")
#             return  # Stop execution if no target profile

#         if username and password:
#             with st.spinner("Fetching profile..."):
#                 profile_info = get_instagram_profile_data(username, password, target_profile)

#                 if profile_info:
#                     st.session_state["profile_info"] = profile_info
#                     st.session_state.profile_loaded = True  # ✅ Mark as loaded
#                     st.session_state.last_loaded_profile = target_profile  # ✅ Update last loaded profile
#                 else:
#                     st.error("❌ Failed to load profile data. Please try again.")

#     # ✅ Ensure profile remains visible after sidebar changes
#     if "profile_info" in st.session_state and st.session_state["profile_info"]:
#         load_css()
#         profile_html = load_html(st.session_state["profile_info"])

#         if profile_html:  # Ensure valid HTML before rendering
#             st.markdown(profile_html, unsafe_allow_html=True)
#         else:
#             st.error("⚠️ HTML conversion failed! Check `load_html()`.")


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

# ===============================================================================================================================================================================================================
#                                                                                                   :HELPER FUCTIONS:
# ===============================================================================================================================================================================================================

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

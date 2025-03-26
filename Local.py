# Contains code for scraping (selenium) and downloading (wget) posts/reels. 

# =================================================================================================================================================================================================================
#                                                                              :Gets Post (Simple onle/ No Carousel) urls and downloads them locally:
# =================================================================================================================================================================================================================

from utils import download_images, open_and_login_instagram, USERNAME

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

image_urls = get_instagram_no_carousel_images_local(username= USERNAME, max_posts=10)
download_images(image_urls=image_urls, target_profile=USERNAME)


# =================================================================================================================================================================================================================
#                                                                                   :Gets Post (Carousel) urls and downloads them locally:
# =================================================================================================================================================================================================================

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

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

image_urls = get_instagram_carousel_local(username= USERNAME, max_posts=10)
download_images(image_urls=image_urls, target_profile=USERNAME)

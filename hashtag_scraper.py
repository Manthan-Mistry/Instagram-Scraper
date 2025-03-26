from selenium.webdriver.common.by import By

from utils import open_and_login_instagram, download_images

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

# Example Usage:
hashtag = "cat"
hashtag_images = get_instagram_hashtag_local(hashtag=hashtag, max_posts=10)
download_images(image_urls=hashtag_images, target_profile=hashtag)


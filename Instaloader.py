# Contains code for downloading posts/reels using Instaloader package.
from utils import get_instagram_links, USERNAME, PASSWORD

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
  
# Example Usage:

post_links = get_instagram_links(profile_username= USERNAME, media_type='posts') # Change media_type = "reels" to download reels.
download_instaloader(post_links=post_links, target_profile= USERNAME, username= USERNAME, password= PASSWORD)

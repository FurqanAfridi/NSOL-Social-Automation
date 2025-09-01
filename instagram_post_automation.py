import os
import re
import time
import json
import tempfile
import platform
import datetime
import subprocess
import traceback
from seleniumbase import SB
import requests
from selenium.common.exceptions import *
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec


COMMON_EXCEPTIONS = (NoSuchElementException, TimeoutException,
                     StaleElementReferenceException, ElementClickInterceptedException,
                     WebDriverException, ElementNotInteractableException,
                     NoSuchAttributeException)



TEMP_PROFILES = {
    "WINDOWS": os.path.expanduser("~/AppData/Local/Temp/ProfileTemp"), 
    "LINUX": "/tmp/ProfileTemp"
}

class GoogleDriveDownloader:
    """Handle Google Drive file downloads"""
    @staticmethod
    def extract_file_id(drive_url):
        """Extract file ID from various Google Drive URL formats"""
        patterns = [
            r'(?:drive\.google\.com/file/d/|drive\.google\.com/open\?id=)([a-zA-Z0-9_-]+)',
            r'id=([a-zA-Z0-9_-]+)',
            r'/d/([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, drive_url)
            if match:
                return match.group(1)
        
        raise ValueError(f"Could not extract file ID from Google Drive URL: {drive_url}")
    
    @staticmethod
    def get_direct_download_url(file_id):
        """Convert file ID to direct download URL"""
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    
    @staticmethod
    def download_file(drive_url, download_path=None):
        """
        Download file from Google Drive URL
        
        Args:
            drive_url (str): Google Drive sharing URL
            download_path (str): Optional path to save file
            
        Returns:
            str: Path to downloaded file
        """
        try:
            # Extract file ID
            file_id = GoogleDriveDownloader.extract_file_id(drive_url)
            
            # Create session for handling cookies
            session = requests.Session()
            
            # Get direct download URL
            download_url = GoogleDriveDownloader.get_direct_download_url(file_id)
            
            # First request to get the file
            response = session.get(download_url, stream=True)
            
            # Handle large file warning page
            if 'confirm=' in response.text or 'virus scan warning' in response.text.lower():
                # Extract confirmation token
                for line in response.text.split('\n'):
                    if 'confirm=' in line:
                        confirm_match = re.search(r'confirm=([^&"\']+)', line)
                        if confirm_match:
                            confirm_token = confirm_match.group(1)
                            download_url = f"{download_url}&confirm={confirm_token}"
                            response = session.get(download_url, stream=True)
                            break
            
            # Check if request was successful
            response.raise_for_status()
            
            # Get filename from response headers or create one
            filename = None
            if 'content-disposition' in response.headers:
                content_disposition = response.headers['content-disposition']
                filename_match = re.search(r'filename="?([^"]+)"?', content_disposition)
                if filename_match:
                    filename = filename_match.group(1)
            
            if not filename:
                # Try to get filename from URL parameters or use file_id
                content_type = response.headers.get('content-type', '')
                if 'image/jpeg' in content_type:
                    filename = f"{file_id}.jpg"
                elif 'image/png' in content_type:
                    filename = f"{file_id}.png"
                elif 'image/gif' in content_type:
                    filename = f"{file_id}.gif"
                elif 'video/mp4' in content_type:
                    filename = f"{file_id}.mp4"
                else:
                    filename = f"{file_id}"
            
            # Create download path
            if download_path is None:
                temp_dir = tempfile.mkdtemp()
                download_path = os.path.join(temp_dir, filename)
            elif os.path.isdir(download_path):
                download_path = os.path.join(download_path, filename)
            
            # Download the file
            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Verify file was downloaded
            if not os.path.exists(download_path) or os.path.getsize(download_path) == 0:
                raise Exception("File download failed or file is empty")
            
            return download_path
            
        except Exception as e:
            raise Exception(f"Google Drive download failed: {str(e)}")
        



def exceptional_handler(func):
    def wrapper(*args, **kwargs):
        retry = kwargs.get("retry", 0)
        max_retries = kwargs.get("max_retries", 2)
        if retry >= max_retries:
            raise Exception("Maximum retries reached!")
        try:
            if "retry" in list(kwargs.keys()):
                kwargs.pop("retry")
            if "max_retries" in list(kwargs.keys()):
                kwargs.pop("max_retries")
            return func(*args, **kwargs)
        except COMMON_EXCEPTIONS:
            time.sleep(5)
            return wrapper(retry=retry + 1, max_retries=max_retries, *args, **kwargs)

    return wrapper


def wait_until(condition_func):
    def wrapper(*args, **kwargs):
        kwargs.get("before_loop", lambda: True)()
        max_attempts = kwargs.get("max_tries", -1)
        dots = 1
        attempt = 0
        not_completed = False
        while True:
            kwargs.get("in_loop_before", lambda: True)()
            if condition_func(*args):
                break
            if max_attempts != -1 and attempt >= max_attempts:
                not_completed = True
                break
            attempt += 1
            print(f"{kwargs.get('message', 'Waiting')}{'.' * dots}", end="\r")
            dots = 1 if dots > 2 else dots + 1
            kwargs.get("in_loop_after", lambda: True)()
            time.sleep(kwargs.get("sleep", 0.5))
            print(" " * 100, end="\r")
        kwargs.get("after_loop", lambda: True)()
        return not not_completed

    return wrapper


class BrowserHandler:
    """Handling Chrome browser."""

    def __init__(self, temp_profile: str = None) -> None:
        """Handling Chrome browser startup and all options for browser handling."""
        self.platform = platform.system().upper()
        self.temp_profile = temp_profile if temp_profile is not None \
            else TEMP_PROFILES.get(self.platform, os.path.abspath("ProfileIA"))
        self.driver = None
        self.wait = None
        self.seleniumbase_driver = None
        self.sb_init = None


    def get_element(self, css_selector: str, by_clickable: bool = False, multiple: bool = False) -> WebElement | list:
        condition = ec.presence_of_element_located if not multiple else ec.presence_of_all_elements_located
        if by_clickable:
            condition = ec.element_to_be_clickable
        return self.wait.until(condition((By.CSS_SELECTOR, css_selector)))

    def find_elements(self, css_selector: str):
        return self.driver.find_elements(By.CSS_SELECTOR, css_selector)

    @exceptional_handler
    def write(self, css_selector: str, data: str, enter=False, clickable=True, clear=True):
        input_el = self.get_element(css_selector, by_clickable=clickable)
        if clear:
            input_el.clear()
        input_el.send_keys(data)
        if enter:
            input_el.send_keys(Keys.ENTER)

    @exceptional_handler
    def click_element(self, css_selector: str = None, element=None):
        if css_selector is not None:
            element = self.get_element(css_selector, by_clickable=True)
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'})", element)
        time.sleep(1)
        element.click()

    @exceptional_handler
    def get_text(self, css_selector=None, element=None, multiple=False):
        if css_selector is not None:
            element = self.get_element(css_selector, multiple=multiple)
        if not multiple:
            return element.get_property("innerText")
        return [el.get_property("innerText") for el in element]

    @exceptional_handler
    def get_attribute(self, attr, css_selector=None, element=None, multiple=False):
        if css_selector is not None:
            element = self.get_element(css_selector, multiple=multiple)
        if not multiple:
            return element.get_attribute(attr)
        return [el.get_attribute(attr) for el in element]

    def start_chrome(self, headless: bool = False, **kwargs) -> None:
        """Start Chrome Browser."""
        sb_init = SB(uc=True, headed=not headless,
                     user_data_dir=self.temp_profile,
                     headless=headless, **kwargs
                     )
        self.seleniumbase_driver = sb_init.__enter__()
        self.sb_init = sb_init
        self.driver = self.seleniumbase_driver.driver
        self.wait = WebDriverWait(self.driver, 40)
        self.driver.maximize_window()
        self.driver.set_page_load_timeout(300)

    def exit_iframe(self):
        self.driver.switch_to.default_content()

    @exceptional_handler
    def enter_iframe(self, css_selector: str):
        iframe_element = self.get_element(css_selector)
        self.driver.switch_to.frame(iframe_element)

    def kill_browser(self, delete_profile: bool = True) -> None:
        """Kill browser and delete profile."""
        if not hasattr(self, "driver") or self.driver is None:
            return
        self.driver.quit()
        self.sb_init.__exit__(None, None, None)
        time.sleep(5)
        if not delete_profile:
            return
        if self.platform in ["LINUX", "DARWIN"]:
            subprocess.Popen(fr"rm -r {self.temp_profile}", shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL)
        elif self.platform == "WINDOWS":
            subprocess.Popen(fr'rmdir /S /Q {self.temp_profile}', shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL)

class InstagramBot(BrowserHandler):
    def __init__(self, username, password, headless=True, **kwargs):
        """
        Initialize Instagram Bot for n8n compatibility
        
        Args:
            username (str): Instagram username
            password (str): Instagram password
            headless (bool): Run browser in headless mode (default True for n8n)
        """
        super().__init__()
        self.username = username
        self.password = password
        self.start_time = datetime.datetime.now()
        self.start_chrome(headless=headless, **kwargs)
        
    def login(self):
        """Login to Instagram with detailed error handling"""
        try:
            # Navigate to Instagram
            self.driver.get("https://www.instagram.com/")
            time.sleep(3)
            if self.find_elements("svg[aria-label=Home]"):
                return True
            self.write("[name='username']", self.username)
            self.write("[name='password']", self.password)
            self.click_element("button[type=submit]")
            time.sleep(5)

            if not wait_until(lambda: self.find_elements("svg[aria-label=Home]"))(message="Waiting until login", max_tries=20):
                raise TimeoutException("No login confirmation")
            return True
        except Exception as e:
            raise Exception(f"Login failed: {str(e)}")
    
    def post_image(self, image_path, caption=""):
        """
        Post an image to Instagram with comprehensive error handling
        
        Args:
            image_path (str): Path to the image file
            caption (str): Caption for the post
        """
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            # Validate image file
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov']
            file_extension = os.path.splitext(image_path)[1].lower()
            if file_extension not in allowed_extensions:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            self.click_element("svg[aria-label='New post']")
            self.click_element("div[aria-hidden='false'] a:first-child")
            self.write("input[type=file]", image_path, clickable=False, clear=False)
            if not wait_until(lambda: self.find_elements("div[aria-label='Crop']"))(message="Waiting for crop dialog", max_tries=20):
                raise TimeoutException("Crop dialog not found")
            for button in self.find_elements("div[aria-label='Crop'] div[role=button]"):
                if self.get_text(element=button) == "Next":
                    self.click_element(element=button)
                    break

            if not wait_until(lambda: self.find_elements("div[aria-label='Edit']"))(message="Waiting for edit dialog", max_tries=20):
                raise TimeoutException("Edit dialog not found")
            for button in self.find_elements("div[aria-label='Edit'] div[role=button]"):
                if self.get_text(element=button) == "Next":
                    self.click_element(element=button)
                    break

            if not wait_until(lambda: self.find_elements("div[aria-label='Create new post']"))(message="Waiting for create new post dialog", max_tries=20):
                raise TimeoutException("Create new post dialog not found")
            
            self.write("div[role=textbox]", caption)
            for button in self.find_elements("div[aria-label='Create new post'] div[role=button]"):
                if self.get_text(element=button) == "Share":
                    self.click_element(element=button)
                    break
            
            if not wait_until(lambda: not self.find_elements("div[role=dialog]"))(message="Waiting for confirmation", max_tries=60):
                raise TimeoutException("Unexpected confirmation error")
            return True
        except Exception as e:
            raise Exception(f"Post failed: {str(e)}")
    
def create_response(success, message, data=None, error_details=None):
    """Create standardized n8n response"""
    response = {
        "success": success,
        "message": message,
        "timestamp": datetime.datetime.now().isoformat(),
        "data": data or {}
    }
    
    if not success and error_details:
        response["error"] = {
            "details": error_details,
            "traceback": traceback.format_exc()
        }
    
    return response

def main():
    """Main function for n8n execution"""
    bot = None
    
    try:
        # Get parameters from environment variables or command line arguments
        # username = os.environ.get('INSTAGRAM_USERNAME') or (sys.argv[1] if len(sys.argv) > 1 else None)
        # password = os.environ.get('INSTAGRAM_PASSWORD') or (sys.argv[2] if len(sys.argv) > 2 else None)
        # image_path = os.environ.get('IMAGE_PATH') or (sys.argv[3] if len(sys.argv) > 3 else None)
        # caption = os.environ.get('CAPTION') or (sys.argv[4] if len(sys.argv) > 4 else "")
        # username = 'dante6556645'
        # password = 'killerafridi'
        # image_path = r'C:\Wallpapers\1.jpeg'
        # caption = 'NCA'
        image_path = GoogleDriveDownloader.download_file(image_path)
        
        # Validate required parameters
        if not all([username, password, image_path]):
            missing_params = []
            if not username: missing_params.append('username')
            if not password: missing_params.append('password')
            if not image_path: missing_params.append('image_path')
            
            error_msg = f"Missing required parameters: {', '.join(missing_params)}"
            response = create_response(False, error_msg, error_details=error_msg)
            print(json.dumps(response, indent=2))
            return
        
        start_time = datetime.datetime.now()
        
        # Initialize bot
        bot = InstagramBot(username, password, headless=False)
        
        # Login
        login_success = bot.login()
        if not login_success:
            raise Exception("Login failed")
        
        # Wait before posting
        time.sleep(2)
        
        # Post image
        post_success = bot.post_image(image_path, caption)
        if not post_success:
            raise Exception("Post failed")
        
        # Calculate execution time
        execution_time = (datetime.datetime.now() - start_time).total_seconds()
        
        # Success response
        response = create_response(
            True, 
            "Instagram post published successfully",
            {
                "username": username,
                "image_path": image_path,
                "caption_length": len(caption),
                "execution_time_seconds": execution_time
            }
        )
        
        print(json.dumps(response, indent=2))
        
    except Exception as e:
        # Error response with traceback
        execution_time = (datetime.datetime.now() - start_time).total_seconds() if 'start_time' in locals() else 0
        
        response = create_response(
            False,
            f"Instagram posting failed: {str(e)}",
            {
                "execution_time_seconds": execution_time,
                "username": username if 'username' in locals() else None,
                "image_path": image_path if 'image_path' in locals() else None
            },
            str(e)
        )
        
        print(json.dumps(response, indent=2))
        
    finally:
        if bot:
            bot.kill_browser()

if __name__ == "__main__":
    main()
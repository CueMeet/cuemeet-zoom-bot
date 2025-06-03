import os
import sys
import time
import json
import uuid
import logging
import requests 
import platform
import subprocess
from datetime import datetime, timezone
from threading import Event
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from .cookies import manage_cookies
from .utils import extract_zoom_details, create_tar_archive, audio_file_path

from monitoring import init_highlight
from config import Settings


class JoinZoomMeet:
    def __init__(self, meetlink, start_time_utc, end_time_utc, min_record_time=3600, bot_name="Zoom Bot", presigned_url_combined=None, presigned_url_audio=None, max_waiting_time=1800, project_settings:Settings=None, logger:logging=None, is_video_record=False):
        self.meeting_id, self.meeting_pwd = extract_zoom_details(meetlink)
        self.start_time_utc = start_time_utc
        self.end_time_utc = end_time_utc
        self.min_record_time = min_record_time
        self.bot_name = bot_name
        self.browser = None
        self.recording_started = False
        self.recording_start_time = None
        self.stop_event = Event()
        self.recording_process = None
        self.presigned_url_combined = presigned_url_combined
        self.presigned_url_audio = presigned_url_audio
        self.id = str(uuid.uuid4())
        self.output_file = f"out/{self.id}"
        self.event_start_time = None
        self.need_retry = False
        self.thread_start_time = None
        self.max_waiting_time = max_waiting_time
        self.session_ended = False 
        self.project_settings = project_settings
        self.logger = logger
        self.highlight = init_highlight(self.project_settings.HIGHLIGHT_PROJECT_ID, self.project_settings.ENVIRONMENT_NAME, "zoom-bot")
        self.is_video_record = is_video_record
        self.video_output_file = f"out/{self.output_file}.mp4" if self.is_video_record else None

    def setup_browser(self):
        options = Options()
        if not self.is_video_record:
            options.add_argument('--headless')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-infobars')
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36')
        options.add_argument('--no-sandbox')
        options.add_argument("--disable-gpu")
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)

        options.add_argument("--use-fake-ui-for-media-stream")
        options.add_argument("--use-fake-device-for-media-stream")

        options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.media_stream_mic": 1,
            "profile.default_content_setting_values.media_stream_camera": 0,
            "profile.default_content_setting_values.geolocation": 0,
            "profile.default_content_setting_values.notifications": 0
        })
        options.add_argument("--auto-select-desktop-capture-source=Zoom Meet")
        options.add_argument(f"user-data-dir=CueMeet{self.id}")

        # Load the extensions
        options.add_argument('--load-extension=transcript_extension')
        options.add_experimental_option("prefs", {
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
        })

        browser_service = Service(ChromeDriverManager().install())

        try:
            self.browser = webdriver.Chrome(
                service=browser_service,
                options=options
            )
            self.browser.execute_script("""
                window.alert = function() { return; }
                window.confirm = function() { return true; }
                window.prompt = function() { return null; }
            """)
            logging.info("Headless browser launched successfully")
        except Exception as e:
            logging.error(f"Failed to launch the browser: {e}")
            self.end_session()


    def navigate_to_meeting(self):
        logging.info(f"Navigating to Zoom Meet ID: {self.meeting_id}")
        try:
            self.browser.get(f"https://zoom.us/wc/join/{self.meeting_id}")
            for cookie in manage_cookies(self.bot_name):
                self.browser.add_cookie(cookie)
            self.browser.refresh()
            logging.info("Successfully navigated to the Zoom Meet link.")
            logging.info("Cookies added successfully")
        except TimeoutException:
            pass
        except Exception as e:
            logging.error(f"Failed to navigate to the meeting link: {e}")
            self.end_session()
        time.sleep(2)
        try:
            meeting_invalid = WebDriverWait(self.browser, 10).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'This meeting link is invalid (3,001)')]")),
                    EC.presence_of_element_located((By.CLASS_NAME, "error-message"))
                )
            )
            if meeting_invalid:
                logging.info("Meeting link is invalid. Ending session.")
                self.end_session()
        except TimeoutException:
            pass
        except Exception as e:
            logging.error(f"Failed to check if meeting link is invalid: {e}")
            self.end_session()


    def join_meeting(self):
        logging.info("Connecting to audio...")
        try:
            join_audio_button = WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Join Audio"]'))
            )
            if join_audio_button: 
                join_audio_button.click()
            logging.info("Audio connected.")
        except Exception as e:
            logging.error(f"Failed to connect to audio")
        
        time.sleep(1)

        try:
            # Handle audio mute/unmute
            audio_button = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.XPATH, '//button[@aria-label="Mute" or @aria-label="Unmute"]'))
            )
            if audio_button:
                current_state = audio_button.get_attribute('aria-label')
                if current_state == "Unmute":
                    logging.info("Audio is already muted.")
                else:
                    audio_button.click()
                    logging.info("Audio muted successfully.")
        except Exception as e: 
            logging.error(f"Failed to handle audio: {str(e)}")
        try:
            # Handle video stop/start
            video_button = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.XPATH, '//button[@aria-label="Stop Video" or @aria-label="Start Video"]'))
            )
            if video_button:
                current_state = video_button.get_attribute('aria-label')
                if current_state == "Start Video":
                    logging.info("Video is already stopped.")
                else:
                    video_button.click()
                    logging.info("Video stopped successfully.")
        except Exception as e:
            logging.error(f"Failed to handle video: {str(e)}")

        time.sleep(1)

        try:
            logging.info("Attempting to join the meeting.") 
            password_input = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@id='input-for-pwd']"))
            )
            password_input.send_keys(self.meeting_pwd)
            logging.info(f"Entered the meeting password: {self.meeting_pwd}")
        except Exception as e:
            logging.error("Failed to enter the meeting password: {e}")
        try: 
            name_input = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@id='input-for-name']"))
            )
            name_input.send_keys(self.bot_name)
            logging.info(f"Entered the bot name: {self.bot_name}")
        except Exception as e:
            logging.error("Failed to enter the bot's name: {e}")
        
        time.sleep(2)
        
        try:
            join_button = WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Join")]'))
            )
            join_button.click()
            logging.info("Clicked the 'Join' button successfully.")
        except Exception as e:
            logging.error("Failed to click 'Join' button: {e}")
        time.sleep(4)


    def check_meeting_removal(self):        
        try:
            removed_text = WebDriverWait(self.browser, 5).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'You have been removed')]")),
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Leave meeting')]"))
                )
            )
            if removed_text:
                logging.info("Detected removal from meeting from the host. Ending session.")
                self.end_session()
        except TimeoutException:
            pass


    def check_meeting_end(self): 
        try:
            return_button = WebDriverWait(self.browser, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'This meeting has been ended by host')]"))
            )
            if return_button:
                logging.info("Detected 'Return to home screen' button. Meeting has ended.")
                self.end_session()
        except TimeoutException:
            pass
        try:
            ended_message = WebDriverWait(self.browser, 5).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'The call ended because everyone left')]"))
            )
            if ended_message:
                logging.info("Detected 'The call ended because everyone left' button. Meeting has ended.")
                self.end_session()
        except TimeoutException:
            pass


    def check_waiting_room(self):
        try:
            waiting_room = WebDriverWait(self.browser, 10).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//span[contains(text(), \"The host will admit you when they're ready\")]")),
                    EC.presence_of_element_located((By.XPATH, "//span[contains(text(), \"Waiting for the host to start the meeting.\")]")),
                    EC.presence_of_element_located((By.XPATH, "//span[contains(text(), \"Host has joined. We've let them know you're here.\")]")),
                )
            )
            if waiting_room:
                return True
        except TimeoutException:
            pass
        except Exception as e:
            logging.error(f"Failed to handle the waiting room: {e}")
        return False


    def check_unmute_request(self):
        try:
            unmute_request = WebDriverWait(self.browser, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'The host would like you to unmute')]"))
            )
            if unmute_request:
                logging.info("Detected unmute request. Attempting to mute audio...")
                mute_button = WebDriverWait(self.browser, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Mute')]"))
                )
                if mute_button:
                    mute_button.click()
                    logging.info("Audio muted.")
        except TimeoutException:
            pass
        except Exception as e:
            pass


    def check_admission(self):
        try:
            # Check if admitted to the meeting
            admitted = WebDriverWait(self.browser, 5).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Participants')]"))
            )
            if admitted and not self.recording_started:
                logging.info("Admitted to the meeting. Starting recording...")
                self.start_recording()
                self.recording_started = True
        except TimeoutException:
            pass
        try:
            # Check if join request was denied
            denied_message = WebDriverWait(self.browser, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), \"You can't join this call\")]"))
            )
            if denied_message:
                logging.error("Join request was denied 'User initialed'. Ending session...")
                self.need_retry = True
        except TimeoutException:
            pass
        try:
            # Check for any error messages
            error_message = WebDriverWait(self.browser, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "error-message"))
            )
            if error_message:
                logging.error(error_message.text)
                if "denied your request to join" in error_message.text:
                    logging.error("Join request was denied 'Platform initialed'. Ending session...")
                    self.end_session()
        except TimeoutException:
            pass


    def attendee_count(self):
        count = -1
        try: 
            element = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.XPATH, '//span[@class="footer-button__number-counter"]'))
            )
            count_text = element.get_attribute('textContent').strip()
            if count_text.isdigit():
                count = int(count_text)
        except TimeoutException:
            logging.error("Attendee count not found.")
        except NoSuchElementException:
            logging.info("Member count element not found. Likely the count is 0.")
        return count


    def start_recording(self):
        logging.info("Starting meeting recording with FFmpeg...")
        output_audio_file = f'{self.output_file}.opus'
        
        if self.is_video_record:
            if platform.system() == 'Linux':
                # Get display number from environment or default to :0
                display = os.environ.get('DISPLAY', ':0')
                
                command = [
                    "ffmpeg",
                    "-f", "x11grab", # Uses X11 screen capture
                    "-video_size", "1920x1080",  # Records at 1080p
                    "-framerate", "30", # 30 frames per second
                    "-i", f"{display}+0,0",  # Captures from display
                    "-f", "pulse", # Uses PulseAudio for audio
                    "-i", "virtual-sink.monitor", # Uses virtual-sink.monitor for audio
                    "-c:v", "libx264", # Video codec
                    "-preset", "ultrafast",
                    "-crf", "23", # Video quality
                    "-c:a", "libopus", # Audio codec
                    "-b:a", "128k",
                    "-ac", "1",
                    "-ar", "48000",
                    self.video_output_file
                ]
            else:
                logging.error("Video recording is only supported on Linux systems with X11")
                self.end_session()
                return
        else:
            if platform.system() == 'Darwin':
                command = [
                    "ffmpeg",
                    "-f", "avfoundation",
                    "-i", ":0",
                    "-acodec", "libopus",
                    "-b:a", "128k",
                    "-ac", "1",  
                    "-ar", "48000",
                    output_audio_file
                ]
            elif platform.system() == 'Linux':  
                command = [
                    "ffmpeg",
                    "-f", "pulse",
                    "-i", "virtual-sink.monitor",
                    "-af", "aresample=async=1000", # Help with audio synchronization
                    "-acodec", "libopus",
                    "-application", "audio", # Help with audio synchronization
                    "-b:a", "256k", # Higher bitrate for better quality
                    "-vbr", "on", # Variable bitrate for better quality/size balance
                    "-frame_duration", "60", # Longer frames for more stable encoding
                    "-ac", "1",
                    "-ar", "48000",
                    output_audio_file
                ]
            else:
                self.logger.error("Unsupported operating system for recording.")
                self.end_session()
                return

        try:
            self.logger.info(f"Executing FFmpeg command: {' '.join(command)}")
            
            self.event_start_time = datetime.now(timezone.utc)
            self.recording_process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.recording_started = True
            self.recording_start_time = time.perf_counter()
            logging.info(f"Recording started. Output will be saved to {self.video_output_file if self.is_video_record else output_audio_file}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Error starting FFmpeg: {e}")
            logging.error(f"FFmpeg output: {e.output}")


    def stop_recording(self):
        if self.recording_started and self.recording_process:
            logging.info("Stopping audio recording...")
            self.recording_process.terminate()
            try:
                self.recording_process.wait()
                logging.info("Recording stopped.")
            except subprocess.TimeoutExpired:
                logging.warning("Recording process did not terminate in time. Forcibly killing it.")
                self.recording_process.kill()
                logging.info("Recording process killed.")
        else:
            logging.info("No recording was started, nothing to stop.")


    def save_transcript(self):
        if not self.browser:
            logging.error("Browser is not available. Cannot save transcript.")
            return
        
        try:
            transcript_data = self.browser.execute_script("return localStorage.getItem('transcript');")
            chat_messages_data = self.browser.execute_script("return localStorage.getItem('chatMessages');")
            meeting_title = self.browser.execute_script("return localStorage.getItem('meetingTitle');")

            transcript = json.loads(transcript_data) if transcript_data else None
            chat_messages = json.loads(chat_messages_data) if chat_messages_data else None

            # Create a dictionary to hold all the data
            transcript_json = {
                'title': meeting_title if meeting_title else None,
                'meeting_start_time': self.event_start_time.isoformat() if self.event_start_time else None,
                'meeting_end_time': datetime.now(timezone.utc).isoformat(),
                'transcript': transcript,
                'chat_messages': chat_messages,
            }

            # Write the dictionary to a JSON file
            full_path = os.path.join(os.getcwd(), f"{self.output_file}.json")
            with open(full_path, 'w', encoding='utf-8') as file:
                json.dump(transcript_json, file, ensure_ascii=False, indent=2)
            logging.info(f"Transcript saved to {self.output_file}.json")
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON format in localStorage: {e}")
        except Exception as e:
            logging.error(f"Error downloading transcript: {e}")


    def upload_files(self):
        try: 
            if self.presigned_url_combined:
                full_path = create_tar_archive(f"{self.output_file}.json", f"{self.output_file}.opus", self.output_file)
                if full_path and os.path.exists(full_path):
                    logging.info(f"Attempting to upload the Tar file from path: {full_path}")
                    try:
                        logging.info(f"Uploading {f'{self.output_file}.tar'} to pre-signed URL...")
                        with open(full_path, 'rb') as file:
                            response = requests.put(self.presigned_url_combined, data=file, headers={'Content-Type': 'application/x-tar'})
                            response.raise_for_status()
                        logging.info("Tar file uploaded successfully.")
                    except Exception as e:
                        logging.error(f"Error uploading the Tar file: {e}")
                else:
                    logging.error(f"Tar file does not exist at: {full_path}")
            else:
                logging.info("No pre-signed Tar URL provided or no Tar file to upload.")
            
            if self.presigned_url_audio:
                full_path = audio_file_path(f"{self.output_file}.opus")
                if full_path and os.path.exists(full_path):
                    logging.info(f"Attempting to upload the Audio file from path: {full_path}")
                    try:
                        logging.info(f"Uploading {f'{self.output_file}.opus'} to pre-signed URL...")
                        with open(full_path, 'rb') as file:
                            response = requests.put(self.presigned_url_audio, data=file, headers={'Content-Type': 'audio/opus'})
                            response.raise_for_status()
                        logging.info("Audio file uploaded successfully.")
                    except Exception as e:
                        logging.error(f"Error uploading the Audio file: {e}")
                else:
                    logging.error(f"Audio file does not exist at: {full_path}")
            else:
                logging.info("No pre-signed Audio URL provided or no Audio file to upload.")
        except Exception as e:
            logging.error(f"Error during file upload: {e}")
    

    def end_session(self):
        if self.session_ended:
            logging.info("Session has already been ended. Skipping end_session method call.")
            return
        self.session_ended = True
        logging.info("Ending the session...")
        try:
            time.sleep(10)
            if self.browser and self.recording_started:
                logging.info("Initiating transcript save...")
                try:
                    self.save_transcript()
                    logging.info("Transcript is saved.")
                except Exception as e:
                    logging.error(f"Failed to save transcript: {e}")
            time.sleep(20)
            if self.browser:
                try:
                    self.browser.quit()
                    logging.info("Browser closed.")
                except Exception as e:
                    logging.error(f"Failed to close browser: {e}")
            self.stop_event.set()
            if self.recording_started:
                self.stop_recording()
                self.upload_files()
            else:
                logging.info("No recording was started during this session.")
        except Exception as e:
            logging.error("Error during session cleanup %s", str(e), exc_info=True)
        finally:
            logging.info("Session ended successfully.")
            sys.exit(0)


    def monitor_meeting(self, initial_elapsed_time=0):
        logging.info("Started monitoring the meeting.")
        start_time = time.perf_counter() - initial_elapsed_time

        low_member_count_end_time = None

        while not self.stop_event.is_set():
            current_time = time.perf_counter()
            elapsed_time = current_time - start_time
            # Before being admitted, check if max_waiting_time has been exceeded
            if not self.recording_started:
                if elapsed_time > self.max_waiting_time:
                    logging.info(f"Maximum waiting time ({self.max_waiting_time} seconds) exceeded. Ending session.")
                    break
            else: 
                recording_elapsed_time = current_time - self.recording_start_time
                if recording_elapsed_time > self.min_record_time:
                    logging.info(f"Minimum recording time ({self.min_record_time} seconds) reached. Ending session.")
                    break
            if self.need_retry:
                logging.info("Need to retry joining the meeting. Exiting monitoring loop.")
                break

            try:
                self.check_meeting_end()
                self.check_meeting_removal()
                self.check_admission()
                self.check_unmute_request()

                if self.check_waiting_room() is False:
                    # We are in the meeting
                    members = self.attendee_count()
                    if members > 1:
                        # Other participants are present; reset the low member count timer
                        if low_member_count_end_time is not None:
                            logging.info("Member count increased. Cancelling 5-minute timer.")
                            low_member_count_end_time = None
                    else:
                        # Only the bot is in the meeting
                        if low_member_count_end_time is None:
                            low_member_count_end_time = current_time + 300  # 5 minutes
                            logging.info("Member count is 1 or less. Starting 5-minute timer.")
                        else:
                            time_left = int((low_member_count_end_time - current_time) / 60)
                            if time_left <= 0:
                                logging.info("Member count has been 1 or less for 5 minutes. Ending session.")
                                break
                            else:
                                logging.info(f"Member count still low. {time_left} minutes left before ending session.")
                else:
                    # Waiting to be admitted to the meeting
                    logging.info("Waiting to be admitted to the meeting.")
            except WebDriverException:
                logging.error("Browser has been closed. Stopping monitoring.")
                break
            except Exception as e:
                logging.error(f"Error during monitoring: {e}")
            time.sleep(2)


    def retry_join(self):
        logging.info("Retrying to join the meeting...")
        time.sleep(12)
        try:
            self.browser.refresh()
            self.navigate_to_meeting()
            self.join_meeting()
        except Exception as e:
            logging.error("Error during retry join: %s", str(e), exc_info=True)
            self.end_session()


    def run(self):
        try:
            logging.info("Meeting bot execution started.")
            self.setup_browser()
            self.navigate_to_meeting()
            self.join_meeting()

            self.thread_start_time = time.perf_counter()
            total_elapsed_time = 0

            self.stop_event.clear()
            self.need_retry = False

            while True:
                self.monitor_meeting(initial_elapsed_time=total_elapsed_time)
                total_elapsed_time = time.perf_counter() - self.thread_start_time

                if self.need_retry:
                    logging.info("Retry flag is set. Proceeding to retry joining the meeting.")
                    self.need_retry = False
                    self.retry_join()
                else:
                    logging.info("Monitoring completed without retry. Exiting.")
                    break

        except Exception as e:
            logging.error("An error occurred during the meeting session. %s", str(e), exc_info=True)
        finally:
            logging.info("Finalizing the meeting session.")
            self.end_session()
        logging.info("Meeting bot has successfully completed its run.")
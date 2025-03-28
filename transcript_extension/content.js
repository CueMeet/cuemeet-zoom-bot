//*********** GLOBAL VARIABLES **********//
const extensionStatusJSON_bug = {
  "status": 400,
  "message": "CueMeet encountered a new error"
}

const mutationConfig = { childList: true, attributes: true, subtree: true }

// CSS for notification
const commonCSS = `background: rgb(255 255 255 / 10%); 
    backdrop-filter: blur(16px); 
    position: fixed;
    top: 5%; 
    left: 0; 
    right: 0; 
    margin-left: auto; 
    margin-right: auto;
    max-width: 780px;  
    z-index: 1000; 
    padding: 0rem 1rem;
    border-radius: 8px; 
    display: flex; 
    justify-content: center; 
    align-items: center; 
    gap: 16px;  
    font-size: 1rem; 
    line-height: 1.5; 
    font-family: 'Google Sans',Roboto,Arial,sans-serif; 
    box-shadow: rgba(0, 0, 0, 0.16) 0px 10px 36px 0px, rgba(0, 0, 0, 0.06) 0px 0px 0px 1px;`;

// Name of the person attending the meeting
let userName = "You"
overWriteChromeStorage(["userName"])
let transcript = []
let personNameBuffer = "", transcriptTextBuffer = "", timeStampBuffer = undefined
let beforePersonName = "", beforeTranscriptText = ""
let chatMessages = []
overWriteChromeStorage(["chatMessages"])

let lastProcessedMessage = {
  personName: "",
  timeStamp: "",
  chatMessageText: ""
};

let meetingStartTimeStamp = new Date().toISOString().toUpperCase();
let meetingTitle = document.title
overWriteChromeStorage(["meetingStartTimeStamp", "meetingTitle"])
let isTranscriptDomErrorCaptured = false
let isChatMessagesDomErrorCaptured = false
let hasMeetingStarted = false
let hasMeetingEnded = false
let lastStoredTranscript = null;

// Modified selectors for Zoom interface
const ZOOM_SELECTORS = {
  // Main transcript container
  transcriptContainer: '#full-transcription',
  transcriptItem: '.lt-full-transcript__item',

  transcriptPersonName: '.lt-full-transcript__display-name',
  transcriptText: '.lt-full-transcript__message',
  transcriptTime: '.lt-full-transcript__time',

  // Meeting end button
  endMeetingButton: '.footer__leave-btn-container button',
  // Username element
  userNameElement: '.participants-section-container',
  // Chat messages container
  chatContainer: '.chat-item-container',
  // Chat button
  chatButton: 'button[aria-label="open the chat panel"]',
  chatPersonName: '.chat-item__sender',
  chatMessageText: '.new-chat-message__text-box p',
  // Meeting title
  meetingTitleButton: '#meeting-info-indication',
  meetingTitleElement: '.meeting-info-icon__meeting-topic-text',
  // More button
  moreButton: 'button[aria-label="More meeting control"]',
  // Captions link in More menu
  captionsLink: 'a[aria-label="Captions"]',
  // Enable caption
  enableCaptionOption: '.zm-btn--primary',
  // Show Captions option
  showCaptionsOption: 'a[aria-label="Your caption settings grouping Show Captions"]',
  // View full transcript option
  viewFullTranscriptOption: 'a[aria-label="Your caption settings grouping View full transcript"]'
}

const checkElement = async (selector, text) => {
  if (text) {
    while (!Array.from(document.querySelectorAll(selector)).find(element => element.textContent === text)) {
      await new Promise((resolve) => requestAnimationFrame(resolve));
    }
  } else {
    while (!document.querySelector(selector)) {
      await new Promise((resolve) => requestAnimationFrame(resolve));
    }
  }
  return document.querySelector(selector);
}

// Shows a responsive notification of specified type and message
function showNotification(extensionStatusJSON) {
  // Banner CSS
  let html = document.querySelector("html");
  let obj = document.createElement("div");
  let text = document.createElement("p");

  // Remove banner after 5s
  setTimeout(() => {
    obj.style.display = "none";
  }, 5000);

  if (extensionStatusJSON.status == 200) {
    obj.style.cssText = `color: #2A9ACA; ${commonCSS}`;
    text.innerHTML = extensionStatusJSON.message;
  }
  else {
    obj.style.cssText = `color: orange; ${commonCSS}`;
    text.innerHTML = extensionStatusJSON.message;
  }

  obj.prepend(text);
  if (html)
    html.append(obj);
}

checkExtensionStatus();
let extensionStatusJSON = JSON.parse(localStorage.getItem('extensionStatusJSON'));
if (extensionStatusJSON) {
  console.log("Extension status " + extensionStatusJSON.status);

  if (extensionStatusJSON.status == 200) {
    // Capture username for Zoom
    checkElement(ZOOM_SELECTORS.userNameElement).then(() => {
      const captureUserNameInterval = setInterval(() => {
        const userNameElement = document.querySelector(ZOOM_SELECTORS.userNameElement);
        if (userNameElement) {
          userName = userNameElement.textContent.trim();
          if (userName || hasMeetingStarted) {
            clearInterval(captureUserNameInterval)
            if (userName != "")
              overWriteChromeStorage(["userName"])
          }
        }
      }, 100)
    })

    // Initialize Zoom meeting monitoring
    initZoomMeeting()
  } else {
    extensionStatusJSON = { status: 200, message: "<strong>CueMeet is running</strong> <br /> Do not turn off captions" };
    console.log("Extension status " + extensionStatusJSON.status);
  }
}

function checkExtensionStatus() {
  // Set default value as 200
  localStorage.setItem('extensionStatusJSON', JSON.stringify({
    status: 200,
    message: "<strong>CueMeet is running</strong> <br /> Do not turn off captions"
  }))
}

async function openCaptionsPopup() {
  try {
    const moreButton = await waitForElement(ZOOM_SELECTORS.moreButton);
    moreButton.click(); // Click the More button to open the dropdown

    const captionsLink = await waitForElement(ZOOM_SELECTORS.captionsLink);
    captionsLink.click(); // Click the Captions link to open the popup

    const showCaptionsOption = await waitForElement(ZOOM_SELECTORS.showCaptionsOption);
    showCaptionsOption.click();

    // Attempt to click the save button - Enable caption
    try {
      const saveButton = await waitForElement(ZOOM_SELECTORS.enableCaptionOption, 2000);
      saveButton.click();
    } catch (error) {
      console.warn('Save button not found, proceeding without clicking it.');
    }

    // Open the captions popup again to click on "View full transcript"
    moreButton.click();

    const captionsLink2 = await waitForElement(ZOOM_SELECTORS.captionsLink);
    captionsLink2.click();

    const viewFullTranscriptOption = await waitForElement(ZOOM_SELECTORS.viewFullTranscriptOption);
    viewFullTranscriptOption.click();

    console.log('Captions and transcript enabled successfully.');
  } catch (error) {
    console.error('Error in openCaptionsPopup:', error);
    showNotification({ status: 400, message: "Failed to enable captions and transcript." });
  }
}

function openZoomChat() {
  const findAndClickChatButton = () => {
    const chatButton = document.querySelector('button[aria-label="open the chat panel"]');
    
    if (chatButton) {
      chatButton.click();
      console.log("Chat button clicked successfully");
    } else {
      console.warn("Chat button not found. Retrying...");
      setTimeout(findAndClickChatButton, 2000);
    }
  };
  findAndClickChatButton();
}

function initZoomMeeting() {
  // Wait for meeting controls to appear
  checkElement(ZOOM_SELECTORS.endMeetingButton).then(() => {
    console.log("Meeting started")
    chrome.runtime.sendMessage({ type: "new_meeting_started" }, function (response) {
      console.log(response);
    });
    hasMeetingStarted = true

    try {
      updateMeetingTitle()

      // Handle captions
      let operationMode = localStorage.getItem('operationMode');
      if (operationMode == "manual") {
        console.log("Manual mode selected, leaving transcript off")
      } else {
        // Open captions popup and enable captions after a delay
        setTimeout(() => openCaptionsPopup(), 10000)
      }

      openZoomChat();
      checkElement(ZOOM_SELECTORS.chatContainer).then(() => {
        const chatTargetNode = document.querySelector(ZOOM_SELECTORS.chatContainer);
        const chatObserver = new MutationObserver(zoomChatRecorder);
        chatObserver.observe(chatTargetNode, mutationConfig);
        console.log("Chat monitoring initialized");
      }).catch((error) => {
        console.error("Chat container not found:", error);
      });

      // Wait for the transcript container to exist before observing
      checkElement(ZOOM_SELECTORS.transcriptContainer).then(() => {

        // **** TRANSCRIPT ROUTINES **** //
        const transcriptTargetNode = document.querySelector(ZOOM_SELECTORS.transcriptContainer);
        const transcriptObserver = new MutationObserver(zoomTranscriber);
        transcriptObserver.observe(transcriptTargetNode, mutationConfig);

        // Show status notification
        if (operationMode == "manual") {
          showNotification({ status: 400, message: "<strong>CueMeet is not running</strong> <br /> Turn on captions using the CC icon, if needed" })
        } else {
          showNotification(extensionStatusJSON)
        }

        //*********** MEETING END ROUTINES **********//
        document.querySelector(ZOOM_SELECTORS.endMeetingButton).addEventListener("click", () => {
          hasMeetingEnded = true
          lastStoredTranscript = null;

          if (transcriptObserver) transcriptObserver.disconnect()
          if (chatMessagesObserver) chatMessagesObserver.disconnect()

          if ((personNameBuffer != "") && (transcriptTextBuffer != "")) {
            pushBufferToTranscript()
          }
          overWriteChromeStorage(["transcript", "chatMessages"])
        })
      }).catch((error) => {
        console.error("Transcript container not found:", error);
        showNotification(extensionStatusJSON_bug);
      });
    } catch (error) {
      console.error(error)
      showNotification(extensionStatusJSON_bug)
    }
  })
}

function zoomTranscriber(mutationsList, observer) {
  mutationsList.forEach(mutation => {
    try {
      const transcriptItems = document.querySelectorAll(ZOOM_SELECTORS.transcriptItem);
      if (transcriptItems.length > 0) {

        // Get the index of the current transcript item
        const currentElementIndex = transcriptItems.length - 1;

        // Wait for the necessary delay
        setTimeout(() => {
          // Re-query the transcript items
          const updatedTranscriptItems = document.querySelectorAll(ZOOM_SELECTORS.transcriptItem);
          if (updatedTranscriptItems.length > currentElementIndex) {
            const updatedElement = updatedTranscriptItems[currentElementIndex];

            // Extract the transcript text
            const currentTranscriptTextElement = updatedElement.querySelector(ZOOM_SELECTORS.transcriptText);
            const currentTranscriptText = currentTranscriptTextElement ? currentTranscriptTextElement.textContent.trim() : '';

            // Extract the person name
            const currentPersonNameElement = updatedElement.querySelector(`${ZOOM_SELECTORS.transcriptPersonName} b`) || updatedElement.querySelector(ZOOM_SELECTORS.transcriptPersonName);
            const currentPersonName = currentPersonNameElement ? currentPersonNameElement.textContent.trim() : personNameBuffer;

            // Update buffers
            personNameBuffer = currentPersonName;
            timeStampBuffer = new Date().toISOString().toUpperCase();
            transcriptTextBuffer = currentTranscriptText;

            // Push to transcript
            pushBufferToTranscript();
          } else {
            console.error('Transcript item not found after delay');
          }
        }, 10000); // 10-second delay

      } else {
        // Handle no transcript items found
        console.log("No active transcript");
        if (personNameBuffer && transcriptTextBuffer) {
          pushBufferToTranscript();
          overWriteChromeStorage(["transcript"]);
        }
        beforePersonName = "";
        beforeTranscriptText = "";
        transcriptTextBuffer = "";
      }
    } catch (error) {
      console.error(error);
      if (!isTranscriptDomErrorCaptured && !hasMeetingEnded) {
        console.log("There is a bug in CueMeet.", error);
        showNotification(extensionStatusJSON_bug);
      }
      isTranscriptDomErrorCaptured = true;
    }
  });
}

function zoomChatRecorder(mutationsList, observer) {
  clearTimeout(window.chatRecorderTimeout);
  window.chatRecorderTimeout = setTimeout(() => {
    try {
      const chatItems = document.querySelectorAll('.chat-item-container');
      
      if (chatItems && chatItems.length > 0) {
        const recentMessages = Array.from(chatItems).slice(-5);
        
        recentMessages.forEach(messageItem => {
          const personNameElement = messageItem.querySelector(ZOOM_SELECTORS.chatPersonName);
          const chatMessageTextElement = messageItem.querySelector(ZOOM_SELECTORS.chatMessageText);
          
          if (personNameElement && chatMessageTextElement) {
            const personName = personNameElement.textContent;
            const timeStamp = messageItem.querySelector('.new-chat-item__chat-info-time-stamp')?.textContent || new Date().toISOString().toUpperCase();
            const chatMessageText = chatMessageTextElement.textContent;
            

            const messageUniqueId = messageItem.id || '';
            const messageFullId = messageItem.querySelector('.new-chat-message__text-box')?.id || '';
            
            const messageId = `${messageFullId || messageUniqueId || Math.random().toString(36).substring(2, 15)}`;
            
            if (!processedMessageIds.includes(messageId)) {
              const chatMessageBlock = {
                personName: personName,
                timeStamp: timeStamp,
                chatMessageText: chatMessageText
              };
              
              if (pushUniqueChatBlock(chatMessageBlock)) {
                console.log("New message:", chatMessageBlock);
                processedMessageIds.push(messageId);
                if (processedMessageIds.length > 100) {
                  processedMessageIds.shift();
                }
                overWriteChromeStorage(["chatMessages"]);
              }
            }
          }
        });
      }
    } catch (error) {
      console.error(error);
      if (isChatMessagesDomErrorCaptured == false && hasMeetingEnded == false) {
        console.log("There is a bug in CueMeet.", error);
        showNotification(extensionStatusJSON_bug);
      }
      isChatMessagesDomErrorCaptured = true;
    }
  }, 300);
}

let processedMessageIds = [];
// Existing helper functions remain the same
function pushBufferToTranscript() {
  const newTranscriptEntry = {
    "personName": personNameBuffer,
    "timeStamp": timeStampBuffer,
    "personTranscript": transcriptTextBuffer
  };

  // Check for duplicates
  const isDuplicate = transcript.some(entry => 
    entry.personName === newTranscriptEntry.personName &&
    entry.personTranscript === newTranscriptEntry.personTranscript &&
    Math.abs(new Date(entry.timeStamp) - new Date(newTranscriptEntry.timeStamp)) < 10000 // 10 second threshold
  );

  // Push only if it's not a duplicate
  if (!isDuplicate) {
    transcript.push(newTranscriptEntry);
    overWriteChromeStorage(["transcript"]); // Update local storage
  }
}

function pushUniqueChatBlock(chatBlock) {
  const isExisting = chatMessages.some(item =>
    item.personName == chatBlock.personName &&
    item.chatMessageText == chatBlock.chatMessageText &&
    Math.abs(new Date(item.timeStamp) - new Date(chatBlock.timeStamp)) < 5000 // 5 second threshold
  );
  
  if (!isExisting) {
    chatMessages.push(chatBlock);
    return true;
  }
  return false;
}
function overWriteChromeStorage(keys) {
  if (keys.includes("userName"))
    localStorage.setItem('userName', JSON.stringify(userName))
  if (keys.includes("transcript"))
    localStorage.setItem('transcript', JSON.stringify(transcript))
  if (keys.includes("meetingTitle"))
    localStorage.setItem('meetingTitle', JSON.stringify(meetingTitle))
  if (keys.includes("meetingStartTimeStamp"))
    localStorage.setItem('meetingStartTimeStamp', JSON.stringify(meetingStartTimeStamp))
  if (keys.includes("chatMessages"))
    localStorage.setItem('chatMessages', JSON.stringify(chatMessages))
}

async function updateMeetingTitle() {
  try {
    const infoClick = await waitForElement(ZOOM_SELECTORS.meetingTitleButton);
    infoClick.click();
    const meetingTitleElement = await waitForElement(ZOOM_SELECTORS.meetingTitleElement);

    if (meetingTitleElement) {
      const title = meetingTitleElement.textContent.trim();
      const invalidFilenameRegex = /[^\w\-_.() ]/g;
      meetingTitle = title.replace(invalidFilenameRegex, '_');
      overWriteChromeStorage(["meetingTitle"]);
    } else {
      console.warn('Meeting title element not found.');
    }
    infoClick.click();
  } catch (error) {
    console.error('Error updating meeting title:', error);
    setTimeout(updateMeetingTitle, 2000);
  }
}

function waitForElement(selector, timeout = 10000) {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    const interval = 100; // Check every 100ms

    const checkForElement = () => {
      const element = document.querySelector(selector);
      if (element) {
        resolve(element);
      } else if (Date.now() - startTime >= timeout) {
        reject(new Error(`Element not found: ${selector}`));
      } else {
        setTimeout(checkForElement, interval);
      }
    };
    checkForElement();
  });
}
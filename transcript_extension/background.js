chrome.runtime.onMessage.addListener(function (message, sender, sendResponse) {
    console.log(message.type);
    if (message.type == "new_meeting_started") {
        // Saving current tab id, to download transcript when this tab is closed
        chrome.tabs.query({active: true, currentWindow: true}, function (tabs) {
            const tabId = tabs[0].id;
            localStorage.setItem('meetingTabId', tabId);  // Store using localStorage
            console.log("Meeting tab id saved");
        });
    }
    return true;
});
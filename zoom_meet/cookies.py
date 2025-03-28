def manage_cookies(username):
    
    """Session cookies for automatic joining process - Zoom Web"""

    cookies = [{
        "domain": ".zoom.us",
        "hostOnly": False,
        "httpOnly": False,
        "name": "_zm_lang",
        "path": "/",
        "secure": True,
        "session": False,
        "storeId": "1",
        "value": "en-US",
        "id": 1
    },
    {
        "domain": ".zoom.us",
        "hostOnly": False,
        "httpOnly": True,
        "name": "_zm_wc_remembered_name",
        "path": "/",
        "secure": True,
        "session": False,
        "storeId": "1",
        "value": username,
        "id": 2
    },
    {
        "domain": ".zoom.us",
        "hostOnly": False,
        "httpOnly": False,
        "name": "OptanonAlertBoxClosed",
        "path": "/",
        "secure": False,
        "session": False,
        "storeId": "1",
        "value": "2021-12-09",
        "id": 3
    },
    {
        "domain": ".zoom.us",
        "hostOnly": False,
        "httpOnly": False,
        "name": "OptanonConsent",
        "path": "/",
        "secure": False,
        "session": False,
        "storeId": "1",
        "value": "isGpcEnabled=1&datestamp=0&version=6.21.0&isIABGlobal=false&hosts=&consentId=0&interactionCount=1&landingPath=NotLandingPage&groups=0&geolocation=0&AwaitingReconsent=false",
        "id": 4
    }]

    return cookies
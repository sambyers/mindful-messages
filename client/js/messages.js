// Run when the pages loads
window.onload = function() {
    // Check if on the message page with session in browser
    if (sessionStorage.getItem('session')) {
        let sessionId = sessionStorage.getItem('session')
        let username = sessionStorage.getItem('username')
        if (username) {
            setLogoutButton(sessionId, 'wbxLoginBtn')
            setUsername('loginIcon', 'loginText', username)
        } else { getUser(sessionId) }
        getMessages(sessionId)
    }
    // Otherwise, make login button
    else {
        wbxAuth()
        loaderHidden(true)
    }
}
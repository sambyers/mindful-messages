// Run when the pages loads
window.onload = function() {
    // Check if about page with session in browser
    if (sessionStorage.getItem('session')) {
        let sessionId = sessionStorage.getItem('session')
        let username = sessionStorage.getItem('username')
        if (username) {
            setLogoutButton(sessionId, 'wbxLoginBtn')
            setUsername('loginIcon', 'loginText', username)
            forgetMe(sessionId)
        } else { getUser(sessionId) }
    }
    // Otherwise, make login button
    else {
        wbxAuth()
    }
}
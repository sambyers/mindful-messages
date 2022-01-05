// Run when the pages loads
window.onload = function() {
    let url = window.location.href
    // Check if home page with session in browser
    if (sessionStorage.getItem('session')) {
        let sessionId = sessionStorage.getItem('session')
        let username = sessionStorage.getItem('username')
        if (username) {
            setLogoutButton(sessionId, 'wbxLoginBtn')
            setUsername('loginIcon', 'loginText', username)
            searchNameEventListener()
        } else { getUser(sessionId) }
        scheduleMessage(sessionId)
    }
    // Check if home with session in url
    else if (url.includes('session=')) {
        let session = url.split("?")[1]
        let sessionId = session.split("=")[1]
        sessionStorage.setItem('session', sessionId)
        getUser(sessionId)
        scheduleMessage(sessionId)
        searchNameEventListener()
    }
    // Otherwise, make login button
    else {
        wbxAuth()
        let msgBtn = document.getElementById('msgSubmitBtn')
        if (msgBtn) { msgBtn.classList.add('disabled') }
    }
}
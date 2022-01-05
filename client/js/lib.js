// Get Webex authorizer link
function wbxAuth() {
    let btn = document.getElementById('wbxLoginBtn')
    btn.onclick = function() {
        fetch(baseApiUrl + 'wbxauth', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.href = data.results.location
            }
        })
        return false
    }
}
// Get the user name to display on the log out button
function getUser(sessionId) {
    fetch(baseApiUrl + 'user?session=' + sessionId, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        },
        mode:'cors'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            sessionStorage.setItem('username', data.results.username)
            setLogoutButton(sessionId, 'wbxLoginBtn')
            setUsername('loginIcon', 'loginText', data.results.username)
        } else {
            errorMsg("Session doesn't exist.")
            sessionStorage.removeItem('session')
            sessionStorage.removeItem('username')
            window.location.href = rootUrl + 'index.html'
        }
    })
}
// Set username and logout icon
function setUsername(iconId, textId, username) {
    let icon = document.getElementById(iconId)
    icon.classList.remove('icon-sign-in')
    icon.classList.add('icon-sign-out')
    let text = document.getElementById(textId)
    text.innerText = username
}
// Set logout button event listener
function setLogoutButton(sessionId, buttonId) {
    let btn = document.getElementById(buttonId)
    btn.addEventListener('click',
        function() {
            Logout(sessionId)
        })
}
// Logout
function Logout(sessionId) {
    fetch(baseApiUrl + 'logout?session=' + sessionId, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        },
        mode: 'cors',
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // successMsg('Logged out successfully.')
            sessionStorage.removeItem('session')
            sessionStorage.removeItem('username')
            window.location.href = rootUrl + 'about.html'
        }
    })
}
// Forget user
function forgetMe(sessionId) {
    let btn = document.getElementById('forgetMe')
    btn.classList.remove('disabled')
    btn.onclick = function() {
        fetch(baseApiUrl + 'user?session=' + sessionId, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                Logout(sessionId)
            } else {
                errorMsg('Error: User not forgotten.')
            }
        })
    }
}
// Schedule a message
function scheduleMessage(sessionid) {
    
    let btn = document.getElementById('msgSubmitBtn')
    btn.onclick = function() {
        let person = document.getElementById('emailInput')
        let msg = document.getElementById('messageInput')
        let time = document.getElementById('datetimeInput')
        let timezone = document.getElementById('timeZoneSelect')
        if (!checkInputValidity()) {
            errorMsg('Please fill out all fields.')
            return false
        }
        let msgData = {
            'person': person.value,
            'msg': msg.value,
            'time': time.value, 
            'timezone': timezone.value
        }
        fetch(baseApiUrl + 'schedule?session=' + sessionid, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(msgData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                successMsg('This message will be sent to ' + person.value + '.')
                person.value = ''
                msg.value = ''
                time.value = ''
            } else {
                errorMsg('Oops! Something went wrong. Message was not scheduled.')
            }
        })
    }
}
// Get all messages and add them as msg cards
function getMessages(sessionId) {
    tz = Intl.DateTimeFormat().resolvedOptions().timeZone
    fetch(baseApiUrl + 'messages?session=' + sessionId + '&timezone=' + tz, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        },
        mode:'cors'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            loaderHidden(true)
            clearMsgCards()
            addMsgCards(sessionId, data.results)
        }
    })
}
// Get all messages and add them as cards on messages page
function addMsgCards(sessionId, data) {
    let msgRow = document.getElementById('msgRow')
    let msgCard = document.getElementById('msgCard')
    for (let i = 0; i < data.length; i++) {
        msg = data[i]
        let cln = msgCard.cloneNode(true)
        msgRow.appendChild(cln)
        cln.id = 'msgCard' + i
        cln.querySelector('#msgCardEmail').innerText = msg.person
        cln.querySelector('#msgCardTime').innerText = UtcToLocalDatetimeString(msg.time)
        cln.querySelector('#msgCardText').innerText = msg.msg
        cln.querySelector('#msgCardDelete').addEventListener('click',
            function() {
                deleteMessage(sessionId, msg.id)
            }
        )
        cln.hidden = false
    }
}
// Change ISO datetime format into local string format
function UtcToLocalDatetimeString(dt) {
    dt = dt + 'Z'
    return new Date(dt).toLocaleString()
}
// Delete all message cards on messages page
function clearMsgCards() {
    let msgRow = document.getElementById('msgRow')
    msgRow.innerHTML = ''
}
// Delete a message and call getMessages again to populate table with existing messages
function deleteMessage(sessionId, messageId) {
    fetch(baseApiUrl + 'message?session=' + sessionId + '&message=' + messageId, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        },
        mode:'cors'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // successMsg('Message deleted.')
            getMessages(sessionId)
        }
    })
}
// Modal for error messages
function errorMsg(msg) {
    let data = {
        'header': 'Error',
        'body': msg
    }
    openModal('modal-default', data)
}
// Modal for success messages
function successMsg(msg) {
    let data = {
        'header': 'Success',
        'body': msg
    }
    openModal('modal-default', data)
}
// Open a modal
function openModal(id, data) {
    let m = document.getElementById(id)
    m.querySelector('.modal__title').innerText = data.header
    m.querySelector('.subtitle').innerHTML = data.body
    m.hidden = false
}
// Close a modal
function closeModal(id) {
    let m = document.getElementById(id)
    m.hidden = true
}
function checkInputValidity() {
    elements = document.getElementsByClassName('msgInput')
    for (let i = 0; i < elements.length; i++) {
        if (elements[i].checkValidity()) {
            // pass
        } else {
            return false
        }
    }
    return true
}
// Set Name Search Event Listener
function searchNameEventListener(){
    searchField = document.getElementById('emailInput')
    searchField.addEventListener('input', searchName)

}
// Search API for user name
function searchName() {
    let sessionId = sessionStorage.getItem('session')
    input = document.getElementById('emailInput')
    input = input.value.toLowerCase()
    if (input.length > 7 && !input.includes('@')) {
        fetch(baseApiUrl + 'people?session=' + sessionId + '&q=' + input, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            },
            mode:'cors'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                fillInputSuggestionList(data.results)
            }
        })
    }
}

function fillInputSuggestionList(items) {
    let old_dl = document.getElementById('peopleSuggestions')
    if (old_dl) { old_dl.remove() }
    let dl = document.createElement('datalist')
    dl.setAttribute('id', 'peopleSuggestions')
    for (let i = 0; i < items.length; i++) {
        let option = document.createElement('option')
        option.value = items[i]['email']
        option.innerText = items[i]['displayname']
        dl.appendChild(option)
    }
    document.body.appendChild(dl)
}

function loaderHidden(state) {
    let loader = document.getElementById('loader')
    loader.hidden = state
}
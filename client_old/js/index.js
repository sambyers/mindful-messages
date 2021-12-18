const baseApiUrl = 'https://zc5qu39i8j.execute-api.us-east-1.amazonaws.com/v1/'
const rootUrl = 'https://mindful-messages.s3.amazonaws.com/'
// Run when the pages loads
window.onload = function() {
    let url = window.location.href
    // Check if on the message page with a session in the query params
    if (sessionStorage.getItem('session') && url.includes('message.html')) {
        let sessionid = sessionStorage.getItem('session')
        getUser(sessionid)
        scheduleMessage(sessionid)
        getMessages(sessionid)
    } else if (url.includes('message.html?session=')) {
        let session = url.split("?")[1]
        let sessionid = session.split("=")[1]
        sessionStorage.setItem('session', sessionid)
        getUser(sessionid)
        scheduleMessage(sessionid)
        getMessages(sessionid)
    } else if (sessionStorage.getItem('session')) {
        window.location.href = rootUrl + 'message.html'
    } else {
        wbxAuth()
    }
}
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
function getUser(sessionid) {
    let btn = document.getElementById('wbxLoginBtn')
    fetch(baseApiUrl + 'user?session=' + sessionid, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        },
        mode:'cors'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            btn.innerHTML = 'Log out ' + data.results.username + ' <img src="/images/cisco-webex-16x16.png" />'
            // Set the button to log out of the session
            btn.onclick = function() {
                fetch(baseApiUrl + 'logout?session=' + sessionid, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    mode: 'cors',
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        statusMsg('Logged out.')
                        sessionStorage.removeItem('session')
                        window.location.href = rootUrl + 'index.html'
                    }
                })
            }
        } else {
            statusMsg('No Session!')
            sessionStorage.removeItem('session')
            window.location.href = rootUrl + 'index.html'
        }
    })
}
// Schedule a message
function scheduleMessage(sessionid) {
    
    let btn = document.getElementById('msgSubmitBtn')
    btn.onclick = function() {
        let person = document.getElementById('emailInput')
        let msg = document.getElementById('messageInput')
        let time = document.getElementById('datetimeInput')
        let timezone = document.getElementById('timeZoneSelect')
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
                statusMsg('😎 Ok! The message will be sent to ' + person.value + ' at ' + time.value + '!')
                person.value = '';
                msg.value = '';
                time.value = '';
                getMessages(sessionid);
            } else {
                statusMsg('😅 Oops! Something went wrong.')
            }
        })
    }
}
// Get all messages and add them to the msg table
function getMessages(sessionId) {
    fetch(baseApiUrl + 'messages?session=' + sessionId, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        },
        mode:'cors'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            clearRows('msgTable')
            addMsgRows(sessionId, 'msgTable', data.results)
        }
    })
}
// Add messages to msg table as rows
function addMsgRows(sessionId, tableId, data) {
    let tableRef = document.getElementById(tableId).getElementsByTagName('tbody')[0];
    for (let i = 0; i < data.length; i++) {
        msg = data[i]
        let newRow = tableRef.insertRow(-1);
        let personCell = newRow.insertCell(0);
        personCell.innerHTML = msg.person;
        let timeCell = newRow.insertCell(1);
        timeCell.innerHTML = msg.time;
        let msgCell = newRow.insertCell(2);
        msgCell.innerHTML = msg.msg;
        // Make the delete button cell
        let delCell = newRow.insertCell(3);
        let newBtn = document.createElement('button');
        let btnTxt = document.createTextNode('Delete');
        newBtn.appendChild(btnTxt);
        newBtn.addEventListener('click', 
            function() {
                deleteMessage(sessionId, msg.id);
            }
        );
        delCell.appendChild(newBtn);
    }
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
            statusMsg('Message deleted.')
            getMessages(sessionId)
        }
    })
}
// Clear rows out of a table given an id
function clearRows(tableId) {
    let oldTbody = document.getElementById(tableId).getElementsByTagName('tbody')[0];
    let newTbody = document.createElement('tbody');
    oldTbody.parentNode.replaceChild(newTbody, oldTbody);
}
// Pop a dialog with a message
function statusMsg(msg) {
    document.getElementById('statusDialog').open = true;
    document.getElementById('statusDialogMsg').innerHTML = msg
}
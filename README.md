# Mindful Messages for Webex
_Proof of concept to demonstrate how to integrate with Webex and extend the platform using the excellent API._
#
Mindful Messages is a proof of concept Webex integration that provides a message scheduling service. It gives you an option to send a message to someone on the Webex platform at a time more in tune with their active hours. By scheduling a message for during someone's active hours, you are saving that person from a distracting notification and implicit expectations of working outside of their normal hours.

You can find the demo proof of concept [here](https://mindful-messages.s3.amazonaws.com/index.html).

## Features
- Authorize via OAuth 2 on Webex
  - The Mindful Messages service asks to read users in your organization and send messages on your behalf.
- Schedule messages to be sent later on Webex
- View scheduled messages
- Delete scheduled messages

## Solution Components

- [Cisco Webex](https://webex.com)
- [Cisco UI Kit](https://github.com/CiscoDevNet/CiscoUIKit)
- [Webexteamssdk](https://github.com/CiscoDevNet/webexteamssdk)
- [Epsagon](https://epsagon.com/)
- [Chalice](https://github.com/aws/chalice)
- AWS Lambda
- AWS API Gateway
- AWS DyanmoDB

### Cisco Products and Services
- Cisco Webex API
- Cisco UI Kit

### Demo Design

![Conceptual Diagram](/assets/images/mindful-messages-mindful-messages-sender-epsagon-map.png)

This demo was designed to be simple and yet still cover many technologies and platforms. The frontend is vanilla Javascript and Cisco UI Kit. JQuery and the myriad Javascript frameworks were ignored to keep things simple.

In the backend, the Chalice micro framework was used to simplify API Gateway and Lambda deployment. Chalice provides simple configuration and routing similar to Flask or FastAPI on top of API Gateway and Lambda. A simple, single table design was used in DynamoDB. Since this is a proof of concept, the database needs are minimal and this worked well. For interfacing with the Webex API, the excellent webexteamssdk was used.

## Usage

Mindful Messages is a simple Webex integration with only two features:
1. Schedule a message to someone for a later date and time
2. View and delete messages scheduled to be sent


### Login
When you navigate to the website, you'll see the page below. The message form is visible but disabled until you login with your Webex account. 
![Conceptual Diagram](/assets/images/mm-prelogin.png)


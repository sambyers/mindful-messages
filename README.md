[![Mindful Messages Tests](https://github.com/sambyers/mindful-messages/actions/workflows/mindful-messages.yml/badge.svg)](https://github.com/sambyers/mindful-messages/actions/workflows/mindful-messages.yml)
[![Mindful Messages Sender Tests](https://github.com/sambyers/mindful-messages/actions/workflows/mindful-messages-sender.yml/badge.svg)](https://github.com/sambyers/mindful-messages/actions/workflows/mindful-messages-sender.yml)

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
- Completely delete your account and scheduled messages from the service (Forget Me button on the About page)

## Solution Components

- [Cisco Webex](https://webex.com)
- [Cisco UI Kit](https://github.com/CiscoDevNet/CiscoUIKit)
- [Webexteamssdk](https://github.com/CiscoDevNet/webexteamssdk)
- [Epsagon](https://epsagon.com/)
- [Chalice](https://github.com/aws/chalice)
- AWS Lambda
- AWS API Gateway
- AWS DyanmoDB
- AWS S3
- AWS EventBridge

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
![Login Screenshot](/assets/images/mm-prelogin.png)

### Schedule a message
After logging in with your Webex account and authorizing the integration, you're redirected to the same page. Now scheduling a message is enabled. To schedule a message, fill out all of the inputs and click schedule.
![Schedule input screenshot](/assets/images/mm-postlogin.png)

### Viewing scheduled messages
To view your scheduled messages, navigate to Messages. Each message will display as a card. The card details who the message is to, when it's scheduled to send, and the message to be sent. To delete a message, simply click the delete link on a message card.
![Messages screenshot](/assets/images/mm-msglist.png)

## Setup, testing, and deployment
Before setting up Mindful Messages, make sure to have the AWS CLI installed and your AWS credentials configured by running the ```aws congigure``` command.

### Database setup
Set up the database by running the Cloud Formation template, ```dynamodb_cf_template.yml```.

```
aws cloudformation deploy help --template-file dynamodb_cf_template.yml --stack-name "mindful-messages"
```

### Mindful Messages backend
The primary backend app is a Lambda function called mindful-messages. It was created with Chalice. Repo location: ```/lambdas/mindful-messages/```.

Chalice is a serverless app framework. It's produced by AWS and is very simple to use. [Learn about Chalice.](https://aws.github.io/chalice/index.html)

#### Configuration
Chalice configuration lives in the ```.chalice``` directory and is not present in this repo. It is deployment specific. Make a ```.chalice``` directory to put Chalice configuration in. The Chalice configuration template used by this app is below.
```
{
  "version": "2.0",
  "app_name": "mindful-messages",
  "environment_variables": {
    "OAUTH_CLIENT_ID": "YOUR OAUTH CLIENT ID",
    "OAUTH_CLIENT_SECRET": "YOUR OAUTH CLIENT SECRET",
    "OAUTH_REDIRECT_URI": "YOUR_API_GW_URL/auth",
    "TABLE_NAME": "mindful-messages",
    "ALLOWED_DOMAINS": "YOUR ALLOWED DOMAINS, e.g. domain.com",
    "CORS_ALLOW_ORIGIN": "YOUR FRONT END ORIGIN, e.g. https://my.app.com",
    "EPSAGON_TOKEN": "YOUR EPSAGON TOKEN",
    "APP_NAME": "mindful-messages"
  },
  "stages": {
    "dev": {
      "api_gateway_stage": "v1",
      "autogen_policy": false
    }
  }
}
```
Read more about Chalice configuration [here](https://aws.github.io/chalice/topics/configfile.html).

#### IAM Policy
Chalice can deploy IAM policies in addition to provisioning Lambda and API Gateway. Below is the example policy used in this app. It allows the Lambda functions to log, access the DynamoDB table created earlier, and an index used to query messages with a sort key of datetime (more on this later).

```
{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource": "arn:aws:logs:*:*:*",
        "Effect": "Allow"
      },
      {
        "Action": [
          "dynamodb:PutItem",
          "dynamodb:DeleteItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query"
        ],
        "Resource": ["arn:aws:dynamodb:*:*:table/mindful-messages"],
        "Effect": "Allow"
      },
      {
        "Action": [
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query"
        ],
        "Resource": ["arn:aws:dynamodb:*:*:table/mindful-messages/index/messages-index"],
        "Effect": "Allow"
      }
    ]
  }
```
#### Testing
There are unit tests and some system tests you can run with the ```unittest``` module. The tests are offline and don't require AWS resources to run. It's a good idea to run these before deploying to make sure the basics work.
```
cd lambdas/mindful-messages
pip install -r test-requirements.txt
python -m unittest -v        
test_delete_message (tests.test_app.TestApp) ... ok
test_get_logout (tests.test_app.TestApp) ... ok
test_get_messages (tests.test_app.TestApp) ... ok
test_get_user (tests.test_app.TestApp) ... ok
test_get_wbxauth (tests.test_app.TestApp) ... ok
test_post_schedule (tests.test_app.TestApp) ... ok
test_message_create (tests.test_lib.TestMessageItem) ... ok
test_message_delete (tests.test_lib.TestMessageItem) ... ok
test_message_get (tests.test_lib.TestMessageItem) ... ok
test_message_to_dict (tests.test_lib.TestMessageItem) ... ok
test_session_create (tests.test_lib.TestSessionItem) ... ok
test_session_delete (tests.test_lib.TestSessionItem) ... ok
test_session_expired_false (tests.test_lib.TestSessionItem) ... ok
test_session_expired_true (tests.test_lib.TestSessionItem) ... ok
test_session_get (tests.test_lib.TestSessionItem) ... ok
test_session_redirect_resp (tests.test_lib.TestSessionItem) ... ok
test_user_add_message (tests.test_lib.TestUserItem) ... ok
test_user_add_session (tests.test_lib.TestUserItem) ... ok
test_user_create (tests.test_lib.TestUserItem) ... ok
test_user_delete (tests.test_lib.TestUserItem) ... ok
test_user_get (tests.test_lib.TestUserItem) ... ok
test_user_remove_message (tests.test_lib.TestUserItem) ... ok
test_user_remove_session (tests.test_lib.TestUserItem) ... ok

----------------------------------------------------------------------
Ran 23 tests in 5.667s

OK
```

#### Deploy
Once you have the configuration and IAM policies in the ```.chalice``` directory, you can simply issue ```chalice deploy```. Chalice will use your AWS credentials and provision the necessary resources (Lambda, API Gateway).

### Mindful Messages Sender function
This function is scheduled and evoked by EventBridge to run periodically to check for messages that are scheduled to be send. Repo location: ```/lambdas/mindful-messages-sender```.

There is a deployment script for this function that can be run to ease deployment.
```
./deploy.sh
```
This script will create a directory called packages, install all depdencies in the requirements.txt file, zip up the packages and function code, and finally deploy to AWS.

After deployment, there's a test script to test the live function and confirm it deployed without errors.
```
./test-lambda.sh
```
The output from the test can be read in the ```testoutput.json``` file. It should read: ```{"message count": 0}```.

There are additional offline tests that can be run via the ```unittest``` module. This assumes you've installed all dependencies using ```pip```.
```
pip install -r test-requirements.txt
cd lambdas/mindful-messages-sender
python -m unittest v
test_message_create (test_models.TestMessageItem) ... ok
test_message_delete (test_models.TestMessageItem) ... ok
test_message_get (test_models.TestMessageItem) ... ok
test_message_to_dict (test_models.TestMessageItem) ... ok
test_session_create (test_models.TestSessionItem) ... ok
test_session_delete (test_models.TestSessionItem) ... ok
test_session_expired_false (test_models.TestSessionItem) ... ok
test_session_expired_true (test_models.TestSessionItem) ... ok
test_session_get (test_models.TestSessionItem) ... ok
test_session_redirect_resp (test_models.TestSessionItem) ... ok
test_user_add_message (test_models.TestUserItem) ... ok
test_user_add_session (test_models.TestUserItem) ... ok
test_user_create (test_models.TestUserItem) ... ok
test_user_delete (test_models.TestUserItem) ... ok
test_user_get (test_models.TestUserItem) ... ok
test_user_remove_message (test_models.TestUserItem) ... ok
test_user_remove_session (test_models.TestUserItem) ... ok

----------------------------------------------------------------------
Ran 17 tests in 4.003s

OK
```

### Mindful Messages frontend
The frontend is a simple website with minimal vanilla Javascript. Repo location: ```/client2```. The Cisco UI kit is used for the webpage. It was very easy to use and looks good too.

There are two important variables to set at the top of the ```js/index.js``` file called ```baseApiUrl``` and ```rootUrl```. Set the former to the API Gateway URL without any routes appended and the latter to the root URL of the website itself.

In the demo deployment, the front end is hosted on AWS S3. There's a script that can help upload to an S3 bucket. The script copies all files and directories to an S3 bucket called ```mindful-messages```, with the exception of hidden files (i.e. dot files, e.g. ```.file```).

```
cd client2/
./s3upload.sh
```

**DISCLAIMER:**  
**Please note:** This script is meant for demo purposes only. All tools/scripts in this repo are released for use "AS IS" without any warranties of any kind, including, but not limited to their installation, use, or performance. Any use of these scripts and tools is at your own risk. There is no guarantee that they have been through thorough testing in a comparable environment and we are not responsible for any damage or data loss incurred with their use. You are responsible for reviewing and testing any scripts you run thoroughly before use in any non-testing environment.

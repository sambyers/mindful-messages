payload=`echo '{"input1": 100, "input2": 200 }' | openssl base64`
aws lambda invoke --function-name mindful-messages-sender --payload "$payload"  testoutput.json
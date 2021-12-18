rm deployment-package.zip
rm -rf packages
mkdir packages
pip3 install -r requirements.txt -t ./packages
cd packages
zip -r ../deployment-package.zip *
cd ../
zip -r ./deployment-package.zip models
zip -g ./deployment-package.zip lambda_function.py
aws lambda update-function-code --function-name mindful-messages-sender --zip-file fileb://deployment-package.zip
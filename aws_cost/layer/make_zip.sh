#!/bin/bash

sudo yum -y update
pip3 install selenium==3.141.0 -t python/lib/python3.7/site-packages
curl -SL https://github.com/adieuadieu/serverless-chrome/releases/download/v1.0.0-37/stable-headless-chromium-amazonlinux-2017-03.zip > headless-chromium.zip
unzip -o headless-chromium.zip -d .
rm headless-chromium.zip
curl -SL https://chromedriver.storage.googleapis.com/2.37/chromedriver_linux64.zip > chromedriver.zip
unzip -o chromedriver.zip -d .
rm chromedriver.zip
pip3 install pandas -t python/lib/python3.7/site-packages


mkdir -p headless/python/bin
mv chromedriver headless/python/bin/
mv headless-chromium headless/python/bin/

zip -r headless.zip headless
zip -r python.zip python

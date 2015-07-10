echo "Creating 'www' bundle for cordova app"

./generate_extension.sh

[ -d www ] || mkdir www
cp -r extension/static www
cp extension/timesheet.html www/index.html

cp -r www /home/odoo/phonegap/timesheets/hello2/
cp www/static/src/img/icon.png /home/odoo/phonegap/timesheets/hello2/

cd /home/odoo/phonegap/timesheets/hello2/
cordova build android
cordova run android

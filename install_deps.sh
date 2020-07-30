source venv3.6/bin/activate
rm -rf ./deps/*

pip uninstall -y mailru-im-async-bot
pip uninstall -y pypros

cd ./deps
git clone https://github.com/smirn0v/bot-python-async.git
cd bot-python-async
pip install -r requirements.txt
python setup.py install --force
cd ..
git clone git@gitlab.corp.mail.ru:icqdev/pypros.git
cd pypros
pip install -r requirements.txt
python setup.py install --force
cd ../..
rm -rf ./deps/*/.git*
pip install -r requirements.txt
#/bin/bash

sudo apt-get update
sudo apt-get upgrade

sudo apt remove python3 --purge
sudo apt autoremove

sudo apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev liblzma-dev tk-dev

cd /tmp/
wget https://www.python.org/ftp/python/3.10.11/Python-3.10.11.tgz
tar xzf Python-3.10.11.tgz
cd Python-3.10.11

sudo ./configure --prefix=/opt/python/3.10.11/ --enable-optimizations --with-lto --with-computed-gotos --with-system-ffi
sudo make -j "$(nproc)"
sudo make altinstall
sudo rm /tmp/Python-3.10.11.tgz

sudo /opt/python/3.10.11/bin/python3.10 -m pip install --upgrade pip setuptools wheel

sudo update-alternatives --install /usr/bin/python python /opt/python/3.10.11/bin/python3.10 1

curl -O https://bootstrap.pypa.io/get-pip.py
sudo /opt/python/3.10.11/bin/python3.10 get-pip.py

cd ~
git clone https://github.com/chris99plus/rotating-stage-control.git
cd rotating-stage-control

sudo raspi-config nonint do_serial 2

python -m pip install -r requirements.txt

reboot
# Deployment script for linux systems

# install necessary libraries
python -m pip install -r requirements.txt

# start REST API
python app.py &

# start reading from serial connection
python core.py
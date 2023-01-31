# Readme

The backend consists of two components:

1. The REST API (`app.py`)
It provides 3 endpoints:
* `\`: Message to check if the backend is running
* `current`: Json Response
  ```javascript
  {
    "currentVisitorCount": number,
    "currentQueueSize": number,
    "estimatedQueueTimeInMin": number
  }
  ```

* `full`: Json Response
  ```javascript
    {
      "currentVisitorCount": number,
      "currentQueueSize": number,
      "estimatedQueueTimeInMin": number,
      "stats":
      {
        "maxPerDayStat":  [{"day":  string, "count": number}, ...],
        "maxPerHourStat": [{"hour": string, "count": number}, ...]
      }
    }
  ```

2. The core logic (`core.py`)
This component reads values coming from the Arduino over a serial connections
and counts the number of customers present inside the cafeteria.
Current values are saved to a file, which can be read by the REST API.

Daily and weekly files are written once per week:
* For daily values, the average number of customers at the end of a 30 min interval is calculated over all previous days.
* For weekly values, the maximum number of customers of that day is saved. The REST API only returns weekly values for the current week

__Note:__ In order for the core to be able to read from serial connection, the serial port needs to
be specified in a [.env](https://pypi.org/project/python-decouple/#env-file) file located in the backend folder. The port name needs to be assigned to  
an `ARDUINO_PORT=` environment variable.

Executing `deploy_backend.bat` or `deploy_backend.sh` will install the necessary libraries and 
start the REST API as well as the core logic.

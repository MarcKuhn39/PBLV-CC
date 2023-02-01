# Readme

The backend consists of two components:

1. The REST API (`app.py`) which is created using the flask framework.
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
Current, daily and weekly values are read from the files `current.txt`, `daily.txt` and `weekly.txt`
which are being written by the core. 

2. The core logic (`core.py`)
This component reads values coming from the Arduino over a serial connection
and counts the number of customers present inside the cafeteria, as well as the estimated queue time.
Current values are saved to a file, which can be read by the REST API.

Reading from the serial connection as well as updating the current values is done in the core thread.
A scheduler is in place to send an event from Monday to Friday every midnight to the core thread to
stop its operation momentarily. Saved events coming from the serial connection will be used to calculate
new daily and weekly values. 
Daily and weekly values are being calculated in the following ways.
* For daily values, the average number of customers at the end of a 30 min interval is calculated over all previous days.
* For weekly values, the maximum number of customers of that day is saved. The REST API only returns weekly values for the current week

These values will be written to the aforementioned files. The state of the core thread also resets 
itself to prepare operation for the next day.


The core and REST API only interact via the text files holding the values. This makes them easier to
maintain and debug.

__Note:__ In order for the core to be able to read from serial connection, the serial port needs to
be specified in a [.env](https://pypi.org/project/python-decouple/#env-file) file located in the backend folder. The port name needs to be assigned to  
an `ARDUINO_PORT=` environment variable.

Executing `deploy_backend.bat` or `deploy_backend.sh` will install the necessary libraries and 
start the REST API as well as the core logic.

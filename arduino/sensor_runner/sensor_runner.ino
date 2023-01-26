
// Analog Sensor Input Pins
#define SENSOR_I 0
#define SENSOR_M 1
#define SENSOR_O 2

// Value Threshold
#define VALUE_THRESHHOLD 20
#define TIME_THRESHHOLD 100

int newValues[3];
int oldValues[3];
int lastSets[3];

void setup() {
  // put your setup code here, to run once:
  pinMode(A5,INPUT);
  pinMode(A1,INPUT);
  pinMode(A2,INPUT);
  Serial.begin(9600);
}

void loop() {
  // put your main code here, to run repeatedly:
  int timeNow = millis();
  processPin(timeNow,SENSOR_I,A5);
  processPin(timeNow,SENSOR_M,A1);
  processPin(timeNow,SENSOR_O,A2);
}

int mapToThreshold(int value){
  if(value > VALUE_THRESHHOLD)
    return 0;
  else
    return 1;
}



void notifySerial(int PORT){
  Serial.print("PORT");
  Serial.print(PORT);
  Serial.print("\n");
}

void processPin(int time,int LPORT,int PPORT){
   if(time - lastSets[LPORT] > TIME_THRESHHOLD){
      newValues[LPORT] = mapToThreshold(analogRead(PPORT));

      if(newValues[LPORT] == oldValues[LPORT])
        return;

      if(oldValues[LPORT] == 0 && newValues[LPORT] == 1)  
        notifySerial(LPORT);
      oldValues[LPORT] = newValues[LPORT];
      lastSets[LPORT] = time;
   }
}


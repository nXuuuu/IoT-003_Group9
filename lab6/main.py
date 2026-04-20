from machine import Pin, SPI, PWM
from mfrc522 import MFRC522
import time
import utime
import os
import sdcard


import network
import urequests
import ujson

SSID = "Robotic WIFI"
PASSWORD = "rbtWIFI@2025"

students_list = ['98902426204']

wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASSWORD)

print("Connecting WiFi", end="")
while not wifi.isconnected():
    print(".", end="")
    time.sleep(0.5)

print("\nConnected:", wifi.ifconfig())

PROJECT_ID = "group09-id-7ff16"
url = "https://firestore.googleapis.com/v1/projects/{}/databases/(default)/documents/rfid_logs".format(PROJECT_ID)

# SPI for SD card
spi_sd = SPI(1, baudrate=1000000,
             sck=Pin(14), mosi=Pin(15), miso=Pin(2))

sd = sdcard.SDCard(spi_sd, Pin(13))
vfs = os.VfsFat(sd)
os.mount(vfs, "/sd")

# SPI for RFID
spi_rfid = SPI(2, baudrate=1000000,
               sck=Pin(18), mosi=Pin(23), miso=Pin(19))

rdr = MFRC522(spi=spi_rfid, gpioRst=Pin(22), gpioCs=Pin(16))



students_list = {
    '98902426204':{
        'name':'james',
        'student_id': '1001',
        'major': 'computer science'
    }
}


buzzer = PWM(Pin(4))

def play_tone(frequency, duration):
    buzzer.freq(frequency)
    buzzer.duty(512) # 50% duty cycle
    time.sleep(duration)
    buzzer.duty(0)   # Stop sound

def send_to_firestore(dt):
    data = {
        "fields": {
            "uid": {"stringValue": dt['uid']},
            "time": {"stringValue": dt['time']},
            'name': {"stringValue": dt['name']},
            'student_id': {"stringValue": dt['student_id']},
            'major': {"stringValue": dt['major']}
        }
    }

    try:
        res = urequests.post(url, json=data)
        print("Sent:", res.text)
        res.close()
    except Exception as e:
        print("Error sending:", e)
        
print("Scan RFID...")

while True:
    (stat, tag_type) = rdr.request(rdr.REQIDL)

    if stat == rdr.OK:
        (stat, uid) = rdr.anticoll()

        if stat == rdr.OK:
            uid_str = "".join([str(i) for i in uid])
            print("UID:", uid_str)
            
            
            
            if uid_str in students_list.keys():
                print('Valid Student')
                play_tone(1000, 0.3)
                now = utime.localtime()

                formatted = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
                    now[0], now[1], now[2],
                    now[3], now[4], now[5]
                )
                student = students_list.get(uid_str)
                row = ''
                if student:
                    row = "{},{},{},{},{}\n".format(
                        uid_str,
                        student.get('name', ''),
                        student.get('student_id', ''),
                        student.get('major', ''),
                        formatted
                    )
                with open("/sd/students.csv", "a") as f:
                    # Construct the CSV row
                    
                        
                    f.write(row)
                    print('Sent to SD card')
                send_to_firestore({
                    'uid': uid_str,
                    'name': student.get('name', ''),
                    'major': student.get('major', ''),
                    'student_id':  student.get('student_id', ''),
                    'time': formatted
                    })
                
            else:
                print('Unknown Card')
                play_tone(1000, 3)
            time.sleep(1)
            
buzzer.deinit()
os.umount("/sd")
print("Unmounted")

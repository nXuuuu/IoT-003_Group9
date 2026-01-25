# 🤖LAB1: Temperature Sensor with Relay Control (Telegram) 
Lab instruction is [HERE](https://theara-seng.github.io/files/IOT/lab1.pdf)

## Task 1-Sensor Read & Print
• Read DHT22 every 5 seconds and print the temperature and humidity with 2 
decimals. </br>
<img width="784" height="609" alt="image" src="https://github.com/user-attachments/assets/1e218380-b00c-473e-81ee-0b8e87b89277" />

## Task 2-Telegram Send
• Implement send_message() and post a test message to group chat. </br>
<img width="1769" height="705" alt="image" src="https://github.com/user-attachments/assets/4abaf916-8a5c-43e4-b2ea-5fb682c2ebbc" />
<img width="1296" height="533" alt="image" src="https://github.com/user-attachments/assets/e6320625-f436-42aa-9ffa-2674bd04de08" />

## Task 3-Bot Command
• Implement /status to reply with current T/H and relay state.  </br>
• Implement /on and /off to control the relay. </br>
<img width="801" height="775" alt="image" src="https://github.com/user-attachments/assets/6a0dc36c-cc18-4d0a-9c59-58a7ee07328e" />

## Task 4-Bot Command
• No messages while T < 30 °C. </br>
•  If T ≥ 30 °C and relay is OFF, send an alert every loop (5 s) until /on is 
received.  </br>
• After /on, stop alerts. When T < 30 °C, turn relay OFF automatically and send 
a one-time “auto-OFF” notice.  </br>
• The demonstration video is [HERE](https://youtu.be/EPEahFAGosI?si=evPU2CnT-OClJXCK)







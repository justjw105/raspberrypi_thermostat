#!/usr/bin/python

import sys
import Adafruit_DHT
import time
import RPi.GPIO as gpio
import threading as thread
import socket, select
import json


old_temp = 0
old_humid = 0

sensor_pin = 2
sensor = 22
ac_pin = 14
heat_pin = 15
fan_pin = 18

fan_on = 0

temp_setting = 68

status = "off";

host = 'localhost'
port = 1337


def broadcast_data (message):
    #Do not send the message to master
    print(len(CONNECTION_LIST))
    for socket in CONNECTION_LIST:
        if socket != server_socket :
            try :
                socket.send(message.encode())
            except :
                print("socket exception")
                # broken socket connection may be, chat client pressed ctrl+c for example
                socket.close()
                try:
                    CONNECTION_LIST.remove(sock)
                except:
                    print("already removed")

                

def turnAllOff():
    global ac_pin
    global heat_pin
    global fan_pin
    
    gpio.output(ac_pin, 1)
    gpio.output(heat_pin, 1)
    gpio.output(fan_pin, 1)
    
def setSystem(temperature):
    print("set system")
    global ac_pin
    global heat_pin
    global fan_pin
    global temp_setting
    global status
    
    turnAllOff()
    if status == "heat" and temperature < temp_setting:
        print("heater set")
        gpio.output(heat_pin, 0)
    elif status == "cool" and temperature > temp_setting:
        print("AC set")
        gpio.output(ac_pin, 0)
        gpio.output(fan_pin, 0)


def jsonEncode(temp, humid):
    return json.JSONEncoder().encode({
        "current_temp": temp,
        "current_humid": humid,
        "temp_setting": temp_setting,
        "status": status
    })
    
def setNewValues(dataString):
    global temp_setting
    global status
    print(dataString)
    valDict = json.JSONDecoder().decode(dataString)
    temp_setting = valDict["temp_setting"]
    status = valDict["status"]


def readTemp():
    global old_temp
    global old_humid
    global gpio
    global sensor_pin
    global sensor
        
    interval = 5
    
    print("read temp started")
    
    while 1:
        humidity, temperature = Adafruit_DHT.read_retry(sensor, sensor_pin)
        temperature = ((temperature * 1.800000)+32)
        temperature = round(temperature,2)
        roundedTemp = round(temperature)
        roundedOldTemp = round(old_temp)
        absoluteDiff = abs(roundedOldTemp - roundedTemp)
        #see if rounded temp changed and make sure the jump wasnt dramatic
        if roundedOldTemp != roundedTemp and absoluteDiff < 2:
            print("temp Changed")
            setSystem(temperature)
        old_temp = temperature
        old_humid = humidity
        jsonstring = jsonEncode(temperature, humidity)
        broadcast_data(jsonstring)
        time.sleep(interval)
        
def socketServer():
    global CONNECTION_LIST
    # this has no effect, why ?
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("127.0.0.1", port))
    server_socket.listen(10)
    print ("Chat server started on port " + str(port))

    while 1:
        # Get the list sockets which are ready to be read through select
        read_sockets,write_sockets,error_sockets = select.select(CONNECTION_LIST,[],[])
    
        for sock in read_sockets:
            #New connection
            if sock == server_socket:
                # Handle the case in which there is a new connection recieved through server_socket
                sockfd, addr = server_socket.accept()
                CONNECTION_LIST.append(sockfd)
                print("Client connected")
                sockfd.send(jsonEncode(old_temp, old_humid).encode())
                 
             
            #Some incoming message from a client
            else:
                # Data recieved from client, process it
                try:
                    #In Windows, sometimes when a TCP program closes abruptly,
                    # a "Connection reset by peer" exception will be thrown
                    data = sock.recv(RECV_BUFFER)
                    if data:
						# here I need to take the data and update the appropriate settings.
                        print("data received")
                        setNewValues(data.decode())
                        setSystem(old_temp)
                 
                except:
                    print("Client is offline")
                    sock.close()
                    try:
                        CONNECTION_LIST.remove(sock)
                    except:
                        print("already removed")
                        continue
                    continue

        
gpio.setwarnings(False)
gpio.setmode(gpio.BCM)
gpio.setup(ac_pin, gpio.OUT)
gpio.setup(fan_pin, gpio.OUT)
gpio.setup(heat_pin, gpio.OUT)

turnAllOff()

# List to keep track of socket descriptors
CONNECTION_LIST = []

RECV_BUFFER = 4096 # Advisable to keep it as an exponent of 2
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
CONNECTION_LIST.append(server_socket)


temperature_thread = thread.Thread(name="temp", target=readTemp)
socket_thread = thread.Thread(name="sock", target=socketServer)
socket_thread.start()
temperature_thread.start()

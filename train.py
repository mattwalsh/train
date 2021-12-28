#!/usr/bin/python3
import time
import random
import threading
import signal
import sys

from enum import Enum

import time

from threading import Thread, Lock

import RPi.GPIO as GPIO

def log(msg):
   f = open("log.txt", "a", 1)
   f.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
   f.write(",")
   f.write(msg)
   f.write("\n")
   f.close()
   return

def signal_handler(signal, frame):
   GPIO.output(4,GPIO.LOW)
   GPIO.output(23,GPIO.LOW)
   GPIO.cleanup()
   sys.exit(0)

def playSound(fileName, bg = None):
   SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
   theFile = SCRIPT_PATH + "/" + fileName
   cmd = "/usr/bin/play -q " + theFile
   if bg:
      cmd = cmd + " &"
   os.system(cmd)

class LEDS(Enum):
   TRAIN_MOTOR = 4
   RIGHT_HOUSE_LED = 5
   LEFT_HOUSE_LED = 6
   HORIZON_LED = 22
   SKY_LED = 27
   CHURCH_LED = 23

class TrainState(Enum):
   RUN = 1
   DWELL = 2

class TrainLoop(threading.Thread):
   def __init__(self):
      self.amion = False
      threading.Thread.__init__(self)
# later      self.event = threading.Event()

   def run(self):
      state = TrainState.RUN
      dwell_cycles =100 
      run_cycles = 5 
      cycle = run_cycles

      while True:
         if state == TrainState.RUN:
            print("RUN")
            GPIO.output(LEDS.TRAIN_MOTOR.value,GPIO.HIGH)
            if cycle == 0:
               state = TrainState.DWELL
               cycle = dwell_cycles
            else:
               cycle = cycle - 1
         else:
            print("DWELL")
            GPIO.output(LEDS.TRAIN_MOTOR.value,GPIO.LOW)
            if cycle == 0:
               state = TrainState.RUN
               cycle = run_cycles
            else:
               cycle = cycle - 1

            
         time.sleep(.005)

#def configure_switches(switches):
#   for pin in switches:
#      GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
#
#def event_setup(switch, isRising, callback, bouncetime):
#   GPIO.add_event_detect(switch, GPIO.RISING if isRising else GPIO.FALLING, callback=callback, bouncetime=bouncetime)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGABRT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(23,GPIO.OUT)
GPIO.output(23,GPIO.LOW)
GPIO.setup(LEDS.SKY_LED.value, GPIO.OUT)
GPIO.output(LEDS.SKY_LED.value, GPIO.HIGH)

GPIO.setup(4,GPIO.OUT)

TRAIN_THREAD = TrainLoop()
TRAIN_THREAD.start()



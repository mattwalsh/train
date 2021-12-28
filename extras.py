import datetime
import sys
import os
import signal
from smbus import SMBus
import RPi.GPIO as GPIO

DEVICE1 = 0x20 # Device address (A0-A2)
DEVICE2 = 0x21 # Device address (A0-A2)
IODIRA = 0x00 # Pin direction register
IODIRB = 0x01 # Pin direction register

OLATA  = 0x14 # Register for outputs
OLATB  = 0x15 # Register for outputs

banks = [0,0,0,0]

g_smbus = SMBus(1) # Rev 2 Pi uses 1

def leds(list, on_off):
   for l in range(0, len(list)):
      led(list[l], on_off)

def led(num, on_off):
   global g_smbus
   dev = DEVICE1 if int(num / 16) == 0 else DEVICE2
   num = num % 16
   olat = OLATA if int(num / 8) == 0 else OLATB
   num = num % 8

   bank = dev - DEVICE1 + 2*(olat - OLATA)

   if on_off:
      banks[bank] |= 1 << num
   else:
      banks[bank] &= 0xff - (1 << num)

   g_smbus.write_byte_data(dev, olat, banks[bank])

def clear_leds():
   global g_smbus
   g_smbus.write_byte_data(DEVICE1,OLATA,0)
   g_smbus.write_byte_data(DEVICE1,OLATB,0)
   g_smbus.write_byte_data(DEVICE2,OLATA,0)
   g_smbus.write_byte_data(DEVICE2,OLATB,0)

def signal_handler(signal, frame):
   cleanup()

def playSound(fileName, bg = None):
   SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
   theFile = SCRIPT_PATH + "/" + fileName
   cmd = "/usr/bin/play -q " + theFile
   if bg:
      cmd = cmd + " &"
   os.system(cmd)

def setup_expander():
   global g_smbus
   g_smbus.write_byte_data(DEVICE1,IODIRA,0x00)
   g_smbus.write_byte_data(DEVICE1,IODIRB,0x00)
   g_smbus.write_byte_data(DEVICE2,IODIRA,0x00)
   g_smbus.write_byte_data(DEVICE2,IODIRB,0x00)

   signal.signal(signal.SIGINT, signal_handler)
   signal.signal(signal.SIGABRT, signal_handler)
   signal.signal(signal.SIGTERM, signal_handler)

   GPIO.setmode(GPIO.BCM)
   GPIO.setwarnings(True)

def configure_switches(switches):
   for pin in switches:
      GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def event_setup(switch, isRising, callback, bouncetime):
   GPIO.add_event_detect(switch, GPIO.RISING if isRising else GPIO.FALLING, callback=callback, bouncetime=bouncetime)

def cleanup():
   log("shutting down")
   print("GAME OVER")
   clear_leds()
   GPIO.cleanup()
   sys.exit(0)

def log(msg):
   f = open("log.txt", "a", 1)
   f.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
   f.write(",")
   f.write(msg)
   f.write("\n")
   f.close()
   return





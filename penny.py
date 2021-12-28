#!/usr/bin/python3

import time
import random
import threading

from enum import Enum

import time
from extras import *

from threading import Thread, Lock
mutex = Lock()
   
ATTRACT_THREAD = None

START = 13  
HEADS = 19
TAILS = 26

YOU_FIRST = None

def computerMove(old):
   outMove = [None] * 3
   outMove[0] = not old[1]
   outMove[1] = old[0]
   outMove[2] = old[1]
   return outMove

def playGame(theMove, impr, callback):
   global g_Board
   thePlay = [None] * 3

   thePlay[0] = None
   thePlay[1] = None
   thePlay[2] = None
   g_Board = thePlay
   drawBoard()

   done = False
   while not done:
      theLastPlay = thePlay[:]
      thePlay[0] = thePlay[1]
      thePlay[1] = thePlay[2]
      thePlay[2] = random.choice([True, False])

      if theLastPlay == thePlay:
         continue
      
      g_Board = thePlay
      drawBoard()
      playSound('sounds/ping1.wav' if thePlay[2] == True else 'sounds/ping2.wav')

      if thePlay[0] == theMove[0] and thePlay[1] == theMove[1] and thePlay[2] == theMove[2]:
         return True
      elif thePlay[0] == impr[0] and thePlay[1] == impr[1] and thePlay[2] == impr[2]:
         return False
      time.sleep(.1)

setup_expander()
configure_switches({START, HEADS, TAILS})

class State(Enum):
   GAME_OVER = 1
   PICKING = 2
   COMPUTER_PICKING = 3

class Who(Enum):
   PLAYER = 0
   COMPUTER = 1
   BOARD = 2

g_State = State.GAME_OVER
g_Moves = []
g_CPUMoves = []
g_Board = [] 
g_ledSets = []

g_grid = [
  [[26,29],[25,28],[24,27]],
  [[10,13],[9,12],[8,11]],
  [[2,5],[1,4],[0,3]]
]

for i in range(len(g_grid)):
   tpl = g_grid[i]
   g_ledSets.append([])
   for j in range(len(tpl)):
      g_ledSets[i].append(tpl[j][0])
      g_ledSets[i].append(tpl[j][1])

def slot(who, slot, state):
   global g_grid

   if state == None:
      led(g_grid[who.value][slot][0], False)
      led(g_grid[who.value][slot][1], False)
   else:
      led(g_grid[who.value][slot][0], state)
      led(g_grid[who.value][slot][1], not state)


def drawBoard():
   global g_Board
   global g_Moves
   global g_CPUMoves

   for i in range(0, len(g_Board)):
      slot(Who.BOARD, i, g_Board[i]) 

   for i in range(0, len(g_Moves)):
      slot(Who.PLAYER, i, g_Moves[i]) 

   for i in range(0, len(g_CPUMoves)):
      slot(Who.COMPUTER, i, g_CPUMoves[i]) 
       
class AttractMode(threading.Thread):
   def __init__(self, winner):
      global g_Moves
      global g_CPUMoves
      threading.Thread.__init__(self)
      self.event = threading.Event()
      self.winner = winner
      self.winningSet = g_Moves[:] if winner == Who.PLAYER else g_CPUMoves[:]

      if len(self.winningSet) == 0:
         self.winningSet = [True, False, True]
  
   def run(self):
      global g_ledSets

      _leds = g_ledSets[Who.PLAYER.value] if self.winner == Who.PLAYER else g_ledSets[Who.COMPUTER.value]
      last_led = None

      which = 0
      which_max = 6

      while True:
         if self.event.is_set():
            break;

         if which <= 2:
            slot(self.winner, which, self.winningSet[which])
            slot(Who.BOARD, which, self.winningSet[which])

         if which == which_max:
            leds(g_ledSets[self.winner.value], False)
            leds(g_ledSets[Who.BOARD.value], False)


         time.sleep(.2)
         which = (which + 1) % (which_max + 1)
         continue

class ComputerThink(threading.Thread):
   def __init__(self):
      threading.Thread.__init__(self)
      self.event = threading.Event()
  
   def run(self):
      global g_ledSets

      last_led = None
      _leds = g_ledSets[Who.COMPUTER.value]

      while True:
         leds(_leds, False)
         if self.event.is_set():
            break;
 
         if last_led != None:
            led(last_led, False)

         while True:
            this_led = _leds[random.randint(0, len(_leds) - 1)] 
            if this_led != last_led:
               break;
      
         led(this_led, True)
         last_led = this_led
         time.sleep(random.uniform(.001, .09))

class PlayerWait(threading.Thread):
   def __init__(self):
      threading.Thread.__init__(self)
      self.event = threading.Event()
  
   def run(self):
      global g_ledSets

      _leds = g_ledSets[Who.PLAYER.value]

      on = True
      while True:
         if self.event.is_set():
            leds(_leds, False)
            break;

         leds(_leds, on)
         time.sleep(.5)
         on = not on

def attract_mode_start(winner):
   global ATTRACT_THREAD
   ATTRACT_THREAD = AttractMode(winner)
   ATTRACT_THREAD.start()

def attract_mode_stop():
   global ATTRACT_THREAD
   global g_ledSets
   ATTRACT_THREAD.event.set()
   leds(g_ledSets[Who.BOARD.value], False)

g_playerWait = None

def pickButtons(which):
   millis = int(round(time.time() * 1000))

   locked = mutex.acquire(True)
   if not locked:  # never hits?
      return

   millis = int(round(time.time() * 1000)) - millis

   if (millis > 1000):
      mutex.release()
      return

   global g_State
   global g_Moves
   global g_CPUMoves
   global g_ledSets
   global g_playerWait
      
   global BOARD_LEDS
   global YOU_FIRST
   global ATTRACT_THREAD
   
   if g_State == State.GAME_OVER:
      mutex.release()
      return

   else:

      if g_playerWait:
         g_playerWait.event.set()
         g_playerWait.join()

      if len(g_Moves) == 0:
         leds(g_ledSets[Who.PLAYER.value], False)

      g_Moves.append(True if which == HEADS else False)
      drawBoard()
      playSound('sounds/ping1.wav' if which == HEADS else 'sounds/ping2.wav')

      if len(g_Moves) == 3:
         if g_State is State.COMPUTER_PICKING:
            if g_Moves == g_CPUMoves:
               g_Moves = []

               leds(g_ledSets[Who.PLAYER.value], False)
               playSound('sounds/die2.wav')
               g_playerWait = PlayerWait()
               g_playerWait.start()
               
               mutex.release()
               return

         if g_State is not State.COMPUTER_PICKING:
            t = ComputerThink()
            t.start()

            playSound('sounds/robot.wav')
            t.event.set()
            t.join()
            time.sleep(.5)

            leds(g_ledSets[Who.COMPUTER.value], False)
            g_CPUMoves = computerMove(g_Moves) 

            for i in range(0,3):
               slot(Who.COMPUTER, i, g_CPUMoves[i]) 
               playSound('sounds/ping1.wav' if g_CPUMoves[i] == True else 'sounds/ping2.wav')
               time.sleep(.3)

         leds(g_ledSets[Who.BOARD.value], False)
         result = True
         result = playGame(g_Moves, g_CPUMoves,
            lambda : 
               playSound('sounds/computer.wav'))

         attract_mode_start(Who.PLAYER if result else Who.COMPUTER)
         if result:
            playSound('sounds/TUNE5.WAV', True)
            led(30, True)
            writeResult(True, YOU_FIRST)
         else:
            playSound('sounds/clanky_things.wav', True)
            led(14, True)
            writeResult(False, YOU_FIRST)

         g_State = State.GAME_OVER
         g_Moves = []
   mutex.release()

def writeResult(playerWon, playerFirst):
   s = "player" if playerWon else "computer"
   s += ","
   s += "playerFirst" if playerFirst else "computerFirst"
   log(s)
   return

def initGame():
   global g_Board
   global g_Moves
   global g_CPUMoves
   global g_ledSets

   attract_mode_stop()

   led(14, False)
   led(30, False)

   leds(g_ledSets[Who.COMPUTER.value], False)
   leds(g_ledSets[Who.BOARD.value], False)
   
   g_Moves = []
   g_CPUMoves = []
   g_Board = []


def startButton(_which):
   global g_State
   global g_Board
   global g_Moves
   global g_CPUMoves
   global g_playerWait
   global g_ledSets
   global YOU_FIRST

   mutex.acquire()

   if g_State == State.GAME_OVER:
      playSound('sounds/COIN.WAV', True)
      YOU_FIRST = not YOU_FIRST if YOU_FIRST is not None else True

      initGame()
      g_State = State.PICKING if YOU_FIRST else State.COMPUTER_PICKING

      if g_State == State.COMPUTER_PICKING:

         clear_leds()
         t = ComputerThink()
         t.start()

         playSound('sounds/robot.mp3')
         t.event.set()
         t.join()
         time.sleep(.5)

         g_CPUMoves = [None] * 3
   
         g_CPUMoves[0] = random.choice([True, False])
         g_CPUMoves[1] = random.choice([True, False])
         g_CPUMoves[2] = random.choice([True, False])

         for i in range(0,3):
            slot(Who.COMPUTER, i, g_CPUMoves[i]) 
            playSound('sounds/ping1.wav' if g_CPUMoves[i] == True else 'sounds/ping2.wav')
            time.sleep(.3)

      g_playerWait = PlayerWait()
      g_playerWait.start()

   mutex.release()

event_setup(START, True, startButton, 1000)
event_setup(HEADS, True, pickButtons, 1000)
event_setup(TAILS, True, pickButtons, 1000)

attract_mode_start(Who.PLAYER)
log("booted")
clear_leds()
which = 0

while True:
   time.sleep(.01)
   
cleanup()
	

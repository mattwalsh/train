#include <map>
#include <iostream>
#include <bcm2835.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <sys/ioctl.h>
#include <sys/select.h>
#include <termios.h>
#include <stropts.h>

#include <termios.h>
#include <unistd.h>
#include <sys/types.h>

#include <signal.h>

#define TRAIN 4
#define MAGNET 17 

#define HORIZON_LED 22 
#define SKY_LED 27
#define CHURCH_LED 23
#define RIGHT_HOUSE_LED 5 
#define LEFT_HOUSE_LED 6

using namespace std;

class Output
{
public:
   Output(int outputIn, char keyIn) : output(outputIn), key(keyIn) 
   {
      output_map[key] = this;
      state = false;
      bcm2835_gpio_fsel(output, BCM2835_GPIO_FSEL_OUTP);
   }

   void toggle()
   {
      state = !state;
      bcm2835_gpio_write(output, state ? HIGH : LOW);
   }
   bool state;
   int output;
   char key;

   static map<char, Output*> output_map;
};

map<char, Output*> Output::output_map;


// simple curses example; keeps drawing the inputted characters, in columns
// downward, shifting rightward when the last row is reached, and
// wrapping around when the rightmost column is reached

#include <string.h>  // required
#include <stdio.h>  // required
#include <stdlib.h>  // required
#include <curses.h>  // required


void changemode(int dir)
{
  static struct termios oldt, newt;
 
  if ( dir == 1 )
  {
    tcgetattr( STDIN_FILENO, &oldt);
    newt = oldt;
    newt.c_lflag &= ~( ICANON | ECHO );
    tcsetattr( STDIN_FILENO, TCSANOW, &newt);
  }
  else
    tcsetattr( STDIN_FILENO, TCSANOW, &oldt);
}

void bail()
{
	changemode(0);
   bcm2835_gpio_write(TRAIN, LOW);
   bcm2835_gpio_write(HORIZON_LED, LOW);
   bcm2835_gpio_write(CHURCH_LED, LOW);
   exit(0);
}

void signal_callback_handler(int signum)
{
   printf("Caught signal %d\n",signum);
   // Cleanup and close up stuff here
   bail(); 
   exit(signum);
}

/*
int _kbhit() {
    static const int STDIN = 0;
    static bool initialized = false;

    if (! initialized) {
        // Use termios to turn off line buffering
        termios term;
        tcgetattr(STDIN, &term);
        term.c_lflag &= ~ICANON;
        tcsetattr(STDIN, TCSANOW, &term);
        setbuf(stdin, NULL);
        initialized = true;
    }

    int bytesWaiting;
    ioctl(STDIN, FIONREAD, &bytesWaiting);
    return bytesWaiting;
}
*/
int kbhit (void)
{
  struct timeval tv;
  fd_set rdfs;
 
  tv.tv_sec = 0;
  tv.tv_usec = 0;
 
  FD_ZERO(&rdfs);
  FD_SET (STDIN_FILENO, &rdfs);
 
  select(STDIN_FILENO+1, &rdfs, NULL, NULL, &tv);
  return FD_ISSET(STDIN_FILENO, &rdfs);
}

timespec diff(timespec start, timespec end)
{
   timespec temp;
   if ((end.tv_nsec-start.tv_nsec)<0) {
      temp.tv_sec = end.tv_sec-start.tv_sec-1;
      temp.tv_nsec = 1000000000+end.tv_nsec-start.tv_nsec;
   } else {
      temp.tv_sec = end.tv_sec-start.tv_sec;
      temp.tv_nsec = end.tv_nsec-start.tv_nsec;
   }
   return temp;
}

#define RUN_CYCLES   40000
#define DWELL_CYCLES 5000

enum STATE {RUN, DWELL};

struct duty
{
   int dwell;
   int run;
};

duty get_duty(float speed)
{

   duty d;
   d.dwell = DWELL_CYCLES;
   d.run = d.dwell*speed;
   return d;	
}

int main(int argc, char *argv[]) {
	changemode(1);

   signal(SIGINT, signal_callback_handler);
   signal(SIGTERM, signal_callback_handler);
   signal(SIGKILL, signal_callback_handler);
   signal(SIGSTOP, signal_callback_handler);

   if(!bcm2835_init()) {
      printf("Can't call bcm2835_init()\n");
      return 1;
   }

   Output(HORIZON_LED, 'h');
   Output(SKY_LED, 's');
   Output(CHURCH_LED, 'c');
   Output(RIGHT_HOUSE_LED, 'r');
   Output(LEFT_HOUSE_LED, 'l');

   bcm2835_gpio_fsel(HORIZON_LED, BCM2835_GPIO_FSEL_OUTP);
   bcm2835_gpio_fsel(CHURCH_LED, BCM2835_GPIO_FSEL_OUTP);

   bcm2835_gpio_fsel(MAGNET, BCM2835_GPIO_FSEL_INPT);
   bcm2835_gpio_set_pud(MAGNET, BCM2835_GPIO_PUD_UP);

   bcm2835_gpio_fsel(TRAIN, BCM2835_GPIO_FSEL_OUTP);

	int cycle = 0;
	int state = RUN;
   bool horizon_led = true;
   bool church_led = true;
   bool magnet_latch = false;
   float speed = 1.0f;
   duty duty_now = get_duty(speed);
	while(1)
	{ 
      volatile uint8_t magnetNow = bcm2835_gpio_lev(MAGNET);

      if (kbhit()) 
      {
         int c = getchar();
      
         Output* o = Output::output_map[c];
         if (o)
         {
            o->toggle();
         }

         if (c >= 48 && c <= 57)
         {
            speed = (c - 48)*10.f / 90.0f;
            std::cout << "SPEED: " << speed << std::endl;
            duty_now = get_duty(speed);
         }
      }

      //bcm2835_gpio_write(HORIZON_LED, horizon_led ? HIGH : LOW);
      // bcm2835_gpio_write(CHURCH_LED, church_led ? HIGH : LOW);

      if (!magnetNow)
      {
//          duty_now = get_duty(0);
//         continue;         
//         std::cout << "MAGNET!!|" << std::endl;
      }
		if (state == RUN)
		{
			bcm2835_gpio_write(TRAIN, HIGH);
			if (cycle == 0)
			{
				state = DWELL;
				cycle = duty_now.dwell;
			}
         else
         {
            cycle--;
         }  
		}
		else
		{
			bcm2835_gpio_write(TRAIN, LOW);
			if (cycle == 0)
			{
				state = RUN;
				cycle = duty_now.run;
			}
         else
         {
            cycle--;
         }  
		}
	}

    return 0;
}

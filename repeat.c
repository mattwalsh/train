#include <iostream>
#include <bcm2835.h>
#include <stdio.h>
#include <time.h>

#define EOSBUTT 27
#define FLIPBUTT 17
#define FLIPRELAY 4

using namespace std;

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

int main(int argc, char *argv[]) {

   if(!bcm2835_init()) {
      printf("Can't call bcm2835_init()\n");
      return 1;
   }

   bcm2835_gpio_fsel(FLIPBUTT, BCM2835_GPIO_FSEL_INPT);
   bcm2835_gpio_fsel(EOSBUTT, BCM2835_GPIO_FSEL_INPT);
   bcm2835_gpio_fsel(FLIPRELAY, BCM2835_GPIO_FSEL_OUTP);

   bcm2835_gpio_set_pud(FLIPBUTT, BCM2835_GPIO_PUD_DOWN);

   volatile bool triggered = false;
   volatile bool measuring = false;

   struct timespec start;
   struct timespec end; 

   cout << "READY!" << endl;
   
   while(1) { 
      volatile uint8_t flipButt = bcm2835_gpio_lev(FLIPBUTT);
      volatile uint8_t eosButt  = bcm2835_gpio_lev(EOSBUTT);

      if (flipButt) {
         bcm2835_gpio_write(FLIPRELAY, HIGH);
         if (!measuring)
         {
            clock_gettime(CLOCK_REALTIME, &start);
            measuring = true;
         }
      }
      else
      {
         bcm2835_gpio_write(FLIPRELAY, LOW);
         triggered = false;
         measuring = false;
      }

      if (eosButt && measuring && !triggered) {
         clock_gettime(CLOCK_REALTIME, &end);

         timespec delta = diff(start, end);
         if (delta.tv_nsec > 10000) {
            triggered = true;
            double dt = delta.tv_sec + delta.tv_nsec / 1e9;
            double spd = (3.0/12.0/5280.0)/(dt/3600.0);
            cout << "time: " << dt << ", " << spd << " mph" << std::endl;
         }
      }


//        delay(1000);
    }

    return 0;
}

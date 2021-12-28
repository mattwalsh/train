// simple curses example; keeps drawing the inputted characters, in columns
// downward, shifting rightward when the last row is reached, and
// wrapping around when the rightmost column is reached

#include <string.h>  // required
#include <stdio.h>  // required
#include <stdlib.h>  // required
#include <curses.h>  // required

#define NUM_TIMES 5
int times[NUM_TIMES];
int next_time = 0;
int stored_times = 0;


int r,c,  // current row and column (upper-left is (0,0))
nrows,  // number of rows in window
ncols;  // number of columns in window

void boxAround( int y, int x, int h, int w, int color = COLOR_RED) {
    attron(A_BOLD);
    start_color();            
    init_pair(1, color, COLOR_BLACK);

    attron(COLOR_PAIR(1));

    move( y, x );
    addch (ACS_ULCORNER);   // upper left corner
    int j;
    for (j = 0;  j < w;  ++j)
        addch (ACS_HLINE);
    addch (ACS_URCORNER);   // upper right



    for( j = 0; j < h; ++j ) {
            move(  y+1+j, x );
            addch (ACS_VLINE);
            move( y+1+j, x+w+1 );
            addch (ACS_VLINE);
    }

    move( y+h+1,x );
    addch (ACS_LLCORNER);   // lower left corner

    for (j = 0;  j < w;  ++j)
        addch (ACS_HLINE);
    addch (ACS_LRCORNER);   // lower right
    attroff(COLOR_PAIR(1));
    attroff(A_BOLD);
}

void draw(char dc)
{  
    clear();
    move(1, 1);  // curses call to move cursor to row r, column c
    addstr("FLIP-O-METER v0.1"); 

    char copyright[] = "(c) 2016 Matt Walsh";
    move(1, ncols - strlen(copyright) - 1);  // curses call to move cursor to row r, column c
    addstr(copyright); 

    boxAround(0, 0, 1, ncols - 2);

   
    char this_line[10]; 
    int first = 0;
    //if (stored_times == NUM_TIMES)
    {
        first = (NUM_TIMES + (next_time - 1)) % NUM_TIMES;
    }
    for (int i = 0; i < stored_times; i++)
    {
        move(3 + i, (ncols - 10)/2);  // curses call to move cursor to row r, column c
        snprintf(this_line, 10, "%d %d %d", next_time, first, times[(NUM_TIMES + (first - i)) % NUM_TIMES]);
        addstr(this_line); 
    }


//    delch();  
//    insch(dc);  // curses calls to replace character under cursor by dc

    refresh();  // curses call to update screen
    r++;  // go to next row

    // check for need to shift right or wrap around
    if (r == nrows)  {
        r = 0;
        c++;

        if (c == ncols) c = 0;
    }
}

void store_time(int t)
{
    times[next_time] = t;
    next_time = (next_time + 1) % NUM_TIMES;

    if (stored_times < NUM_TIMES)
    {
        stored_times++;
    }
}

int main()
{  
    int i;  
    char d;

    times[0] = 1;
    times[1] = 2;
    times[2] = 3;
    stored_times = 3;
    next_time = 3;

    WINDOW *wnd;
    wnd = initscr();  // curses call to initialize window

    cbreak();  // curses call to set no waiting for Enter key
    noecho();  // curses call to set no echoing
    getmaxyx(wnd, nrows, ncols);  // curses call to find size of window
    clear();  // curses call to clear screen, send cursor to position (0,0)

    refresh();  // curses call to implement all changes since last refresh

    r = 0; c = 0;

    while (1)  {
        d = getch();  // curses call to input from keyboard
        if (d == 'q') break;  // quit?
        store_time(d);
        draw(d);  // draw the character
    }

    endwin();  // curses call to restore the original window and leave
    return 0;
}
  

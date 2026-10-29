#include <ApplicationServices/ApplicationServices.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
// usage: post <pid> scroll <x> <y> <count> <dy> <hz> | post <pid> trace
int main(int argc,char**argv){
  pid_t pid=atoi(argv[1]);
  if(!strcmp(argv[2],"trace")){ // shift-cmd-T
    CGEventRef d=CGEventCreateKeyboardEvent(NULL,(CGKeyCode)17,true), u=CGEventCreateKeyboardEvent(NULL,(CGKeyCode)17,false);
    CGEventSetFlags(d,kCGEventFlagMaskCommand|kCGEventFlagMaskShift); CGEventSetFlags(u,kCGEventFlagMaskCommand|kCGEventFlagMaskShift);
    CGEventPostToPid(pid,d); usleep(30000); CGEventPostToPid(pid,u); return 0; }
  double x=atof(argv[3]),y=atof(argv[4]); int n=atoi(argv[5]); int dy=atoi(argv[6]); double hz=atof(argv[7]);
  for(int i=0;i<n;i++){
    CGEventRef e=CGEventCreateScrollWheelEvent(NULL,kCGScrollEventUnitPixel,1,dy);
    CGEventSetLocation(e,CGPointMake(x,y));
    CGEventPostToPid(pid,e); CFRelease(e); usleep((useconds_t)(1e6/hz)); }
  return 0; }

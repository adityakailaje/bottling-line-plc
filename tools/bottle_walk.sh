#!/bin/sh
# Walk one bottle through every station using mbpoll as a stand-in PLC.
# Usage: sh tools/bottle_walk.sh [HOST] [PORT] [pass|reject]
H=${1:-127.0.0.1}; P=${2:-5020}; MODE=${3:-pass}

coil() { mbpoll -m tcp -a 1 -0 -1 -t 0 -r "$1" -p "$P" "$H" "$2" > /dev/null; }
read_reg() { mbpoll -m tcp -a 1 -0 -1 -t "$1" -r "$2" -c 1 -p "$P" "$H" | grep "^\[" ; }
index() { coil 0 1; sleep 2.0; coil 0 0; sleep 0.3; }   # one pitch = 0.25 m/s x 2 s

echo "release one bottle";          coil 4 1; sleep 0.3; coil 4 0
echo "index to the fill station";   index
echo "fill for 3 s";                coil 1 1; sleep 3.0; coil 1 0
echo "index to the cap station";    index
echo "cap for 1.5 s";               coil 2 1; sleep 1.5; coil 2 0
echo "index to inspection";         index
printf "fill volume x10 (IR1): ";    read_reg 3 1
printf "cap present (DI5):     ";    read_reg 1 5
echo "index to the reject station"; index
if [ "$MODE" = "reject" ]; then
  echo "fire the reject pusher";    coil 3 1; sleep 0.6; coil 3 0
else
  echo "index to the outfeed sensor"; index
  echo "index off the belt";          index
fi
echo "done"

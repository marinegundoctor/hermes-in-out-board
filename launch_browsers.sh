#!/bin/bash
xset s off
xset s noblank
xset -dpms

unclutter -idle 0.5 -root &

URL="http://localhost:8000/"
OPTS="--kiosk --noerrdialogs --disable-infobars --disable-features=TranslateUI"

HDMI1_WIDTH=$(xrandr | grep -w "connected primary" | grep -oE "[0-9]+x[0-9]+\+[0-9]+\+[0-9]+" | awk -F 'x' '{print $1}')
if [ -z "$HDMI1_WIDTH" ]; then
    HDMI1_WIDTH=1920
fi

/usr/bin/chromium $OPTS --window-position=0,0 --user-data-dir=/home/margun/.config/chromium-display1 "$URL" &
PID1=$!

sleep 2

/usr/bin/chromium $OPTS --window-position=$HDMI1_WIDTH,0 --user-data-dir=/home/margun/.config/chromium-display2 "$URL" &
PID2=$!

wait $PID1 $PID2

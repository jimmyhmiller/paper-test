#!/bin/zsh
# Drive a background paper-transcript window with synthetic scrolling and print
# what reached the glass. Never takes focus: the app launches behind every other
# window and the events are posted straight to its pid.
#   tools/pacing/live.sh [binary] [dy] [hz] [count]
# Posted events carry no window, so AppKit reports their location in screen
# space and the app reads it as window space: (700, 839) lands mid-transcript.
HERE=${0:A:h}; ROOT=${HERE:h:h}
BIN=${1:-$ROOT/apps/paper-transcript/build/paper-transcript}; DY=${2:--8}; HZ=${3:-200}; N=${4:-700}
POST=/tmp/paper-pacing-post
[ -x $POST ] || clang -O1 $HERE/post.c -o $POST -framework ApplicationServices || exit 1
cd $ROOT/apps/paper-transcript || exit 1
rm -f /tmp/paper-transcript-trace.txt
(PAPER_BACKGROUND=1 $BIN --app ${APP:-26} >/dev/null 2>&1 &); sleep 7
PID=$(pgrep -f "$(basename $BIN) --app" | head -1)
$POST $PID scroll 700 839 60 $DY $HZ      # warm the caches
$POST $PID trace; sleep 0.6               # shift-cmd-T: resets the glass counters
$POST $PID scroll 700 839 $N $DY $HZ
$POST $PID trace; sleep 1.2
grep -E "^[0-9]+ fps|^display|^callback|^glass|^cadence|^gpu" /tmp/paper-transcript-trace.txt
kill $PID 2>/dev/null

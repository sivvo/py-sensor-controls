# simple script to turn my dakboard on when movement has been detected (pir)

# TODO allow new movement to reset/extend the time before the screen is turned off again
#

import sys
import time
import subprocess
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
SHUTOFF_DELAY = 60    # seconds
PIR_PIN = 25          # 22 on the board

def main():
    GPIO.setup(PIR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    turned_off = False
    previous_state = False
    last_motion_time = time.time()

    while True:
        currentHour = time.localtime().tm_hour
        # if it's 7-10am or 5-8pm, turn the screen on and poll less often
        if ((7 <= currentHour < 10) or (17 <= currentHour < 20)):
            print 'The current hour is {}, screen should remain on'.format(currentHour)
            sys.stdout.flush()
            if turned_off:
                turned_off = False
                turn_on()
            time.sleep(60)
        # if it's not during one of our 'busy hours', look for motion
        else:
            if GPIO.input(PIR_PIN) and previous_state == False:
                print "It's been {} seconds since the last motion\n".format(time.time()-last_motion_time)
                sys.stdout.flush()
                last_motion_time = time.time()
                previous_state = True
                if turned_off:
                    turned_off = False
                    turn_on()

            elif previous_state:
                if not turned_off and time.time() > (last_motion_time + SHUTOFF_DELAY):
                    turned_off = True
                    turn_off()
                previous_state = False

            time.sleep(.1)

def turn_on():
    subprocess.call("sh /home/pi/MotionSensor/monitor_on.sh", shell = True)

def turn_off():
    subprocess.call("sh /home/pi/MotionSensor/monitor_off.sh", shell = True)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        GPIO.cleanup()


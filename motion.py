import sys
import subprocess
import time
import logging
import datetime

from gpiozero import MotionSensor
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.FileHandler('/var/log/motion.log')
handler.setLevel(logging.DEBUG)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)

logger.debug("module import complete")
PIR_PIN = 4
SHUTOFF_DELAY = 60    # seconds - we're going to make this dynamic
logger.debug("listening on PIN %i", PIR_PIN)

def main():
    pir = MotionSensor(PIR_PIN)
    logger.debug("now listening on the pin")
    while True:
        if pir.motion_detected:
            if 5 <= datetime.datetime.today().hour <= 23:
                # don't turn the screen on between 11pm and 5am
                logger.info("motion detected at %s", time.ctime())
                turn_on()
                time.sleep(90)
                turn_off()
            else:
                time.sleep(90)

def turn_on():
    logger.debug("enabling the hdmi port at %s", time.ctime())
    subprocess.call("sh /home/pi/rpi-hdmi.sh on", shell = True)

def turn_off():
    logger.debug("Disabling the hdmi port at %s", time.ctime())
    subprocess.call("sh /home/pi/rpi-hdmi.sh off", shell = True)

def shutoff_delay():
    logger.info("shutoff time delay will vary based on time of day... maybe?")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        #GPIO.cleanup()
        logger.info("System shutting down")
        logger.warn("we need some kind of cleanup")


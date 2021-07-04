#in case your LEDs or buzzer gets stuck in the on position this turns LEDs and buzzer OFF

from gpiozero import Buzzer, LED
from time import sleep

buzzer = Buzzer(17)
red = LED(17)
green = LED(22)

buzzer.off()
red.off()
green.off()
sleep(1)
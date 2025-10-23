from ws2812 import WS2812
from machine import I2C,Pin,ADC
from time import sleep, ticks_us
import random

led = WS2812(18,1)
SOUND_SENSOR = ADC(1)

window = 10
noises = []
moyenne_glissante = 15
facteur = 2.0
last = ticks_us()

BPM_MAX = 128
ecart_max = 10**6 / BPM_MAX

while True:
    average = 0
    for i in range (100):
        noise = SOUND_SENSOR.read_u16()/256
        if noise > 5.0:
            average += noise
        else:
            i -= 1
    noise = average/100

    
    if noise > moyenne_glissante * facteur:
        if ticks_us() - last > ecart_max:
            rgb = [random.randint(0, 255) for i in range(3)]
            rgb = tuple(rgb)
            led.pixels_fill(rgb)
            led.pixels_show()
            print(f"{noise} > {moyenne_glissante * facteur}")

            last = ticks_us()
            noises.append(noise * 0.75)
    else:
        noises.append(noise)
            
    if len(noises) > 10:
        noises.pop(0)
    moyenne_glissante = sum(noises)/len(noises)
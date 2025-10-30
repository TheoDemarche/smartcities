from ws2812 import WS2812
from machine import I2C,Pin,ADC
from time import sleep, ticks_us, ticks_diff
import random

led = WS2812(18,1)
SOUND_SENSOR = ADC(1)

window = 10
noises = []
moyenne_noise = 15
facteur = 1.2
last = ticks_us()

BPM_MAX = 128
ecart_max = (60 * 10**6) / (BPM_MAX + 10) #Marge pour assurer la detection à la limite

def moyenne_glissante(values, window_size: int) -> int:
    if len(values) > window_size:
        values.pop(0)
    
    moyenne = sum(values) / len(values)
    return moyenne


ecarts = []
while True:
    average = 0
    moyenne_ecart = 0
    bpm = 0
    for i in range (100):
        noise = SOUND_SENSOR.read_u16()/256
        if noise > 5.0:
            average += noise
        else:
            i -= 1
    noise = average/100

    if noise > moyenne_noise * facteur:
        ecart = ticks_diff(ticks_us(), last)
        if ecart > ecart_max:
            last = ticks_us()
            rgb = [random.randint(0, 255) for i in range(3)]
            rgb = tuple(rgb)
            led.pixels_fill(rgb)
            led.pixels_show()
            print(f"{noise} > {moyenne_noise * facteur}")

            ecarts.append(ecart)
            # print(ecarts)
            moyenne_ecart = moyenne_glissante(ecarts, 20)
        noises.append(noise * 0.75)
    else:
        noises.append(noise)
            
    if len(noises) > 10:
        noises.pop(0)
    moyenne_noise = sum(noises)/len(noises)

    if moyenne_ecart > 0:
        bpm = 60 / (moyenne_ecart / 10**6)
        print(f"BPM = {bpm}")
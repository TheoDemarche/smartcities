import machine
import time

BUTTON = machine.Pin(16, machine.Pin.IN)
LED = machine.Pin(18, machine.Pin.OUT)

last_val = 0

count = 0
last = time.ticks_ms()

led_bool = False
led_bool_abs = False

last_pressed = time.ticks_ms()

# pressing = False

while True:
    val = BUTTON.value()

    if (val and not last_val) :
        # pressing = True
        last_pressed=time.ticks_ms()
    elif (not val and last_val):
        # pressing = False
        if time.ticks_ms() - last_pressed > 1000:
            led_bool_abs = not led_bool_abs
        else:
            count+=1
    
    now = time.ticks_ms()

    if count %3 == 0:
        if now - last > 2000:
            led_bool = not led_bool
            last = time.ticks_ms()
    elif count %3 == 1:
        if now - last > 500:
            led_bool = not led_bool
            last = time.ticks_ms()
    elif count %3 == 2:
        if now - last > 100:
            led_bool = not led_bool
            last = time.ticks_ms()

    if led_bool and led_bool_abs:
        LED.value(1)
    else:
        LED.value(0)
    
    last_val = val

from lcd1602 import LCD1602
from dht20 import DHT20
from machine import I2C,Pin,ADC,Timer, PWM
import time

i2c1 = I2C(1)#LCD
LCD = LCD1602(i2c1, 2, 16)
LCD.display()

i2c0_sda = Pin(8)
i2c0_scl = Pin(9)
i2c0 = I2C(0, sda=i2c0_sda, scl=i2c0_scl)
dht20 = DHT20(0x38, i2c0)

led = Pin(18, Pin.OUT)
timer_led = Timer(-1)

buzzer = PWM(Pin(27))

ROTARY_ANGLE_SENSOR = ADC(0)

def set_LCD(str1, str2):
    LCD.clear()
    LCD.setCursor(0,0)
    LCD.print(str1)
    LCD.setCursor(0,1)
    LCD.print(str2)

def toggle_led(timer):
    led.toggle()

def set_led_blink(frequence):
    global timer_led
    timer_led.deinit()
    if frequence > 0:
        timer_led.init(freq=frequence, mode=Timer.PERIODIC, callback=toggle_led)
    else:
        led.off()

#min value = 352/368,   max value = 65535
rot_min_value = 352
rot_max_value = 65535-352
set_min_value = 15
set_max_value = 35
set_plage = set_max_value - set_min_value
SET_temp = set_min_value

def normalize_rotation(rot):
    rot -= rot_min_value
    rot /= rot_max_value
    rot *= set_plage
    rot += set_min_value
    return round(rot)

start = time.ticks_ms()

while True:
    measurements = dht20.measurements
    print(f"Temperature: {measurements['t']} °C, humidity: {measurements['rh']} %RH")

    SET_temp = normalize_rotation(ROTARY_ANGLE_SENSOR.read_u16())

    set_LCD(f"Set: {int(SET_temp)} °C",
            f"Ambient: {measurements['t']:.2f} °C")



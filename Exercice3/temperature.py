from lcd1602 import LCD1602
from dht20 import DHT20
from machine import I2C,Pin,ADC,Timer, PWM
import time

i2c1 = I2C(1)#LCD
LCD = LCD1602(i2c1, 2, 16)
LCD.display()
first_row = ""
second_row = ""
row = 0
state = 0

timer_alarm = Timer(-1)

i2c0_sda = Pin(8)
i2c0_scl = Pin(9)
i2c0 = I2C(0, sda=i2c0_sda, scl=i2c0_scl)
dht20 = DHT20(0x38, i2c0)
timer_temp = Timer(-1)
temp = dht20.measurements['t']

led = Pin(18, Pin.OUT)
timer_led = Timer(-1)

buzzer = PWM(Pin(27))
buzzer.freq(440)

ROTARY_ANGLE_SENSOR = ADC(0)

def set_LCD(str1, str2):
    LCD.clear()
    LCD.setCursor(0,0)
    LCD.print(str1)
    LCD.setCursor(0,1)
    LCD.print(str2)

def read_temp(timer):
    global temp
    temp = dht20.measurements['t']
    print(temp)

def toggle_led(timer):
    led.toggle()

# def set_timer_freq(timer, frequence, fct):
#     timer.deinit()
#     timer.init(freq=frequence, mode=Timer.PERIODIC, callback=fct)

# def set_led_timer_freq(frequence):
#     global timer_led
#     if frequence > 0:
#         set_timer_freq(timer_led, frequence, toggle_led)
#     else:
#         led.off()

def set_led_timer_freq(frequence):
    global timer_led
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
    return round(rot * 2) / 2

last = time.ticks_ms()

timer_temp.init(freq=1, mode=Timer.PERIODIC, callback=read_temp)

# set_led_timer_freq(0.5)
# time.sleep(5)
# set_led_timer_freq(5)

# while True:
#     pass

def toggle_row(timer):
    global row
    row = not row



while True:
    SET_temp = normalize_rotation(ROTARY_ANGLE_SENSOR.read_u16())
    if time.ticks_ms() - last > 100:

        first_row = f"Set: {SET_temp:.1f} °C"
        second_row = f"Ambient: {temp:.2f} °C"
        
        if temp > (SET_temp + 3):
            if state != 0:
                state = 0
                buzzer.duty_u16(32767)
                set_led_timer_freq(5)
                timer_alarm.init(freq=1, mode=Timer.PERIODIC, callback=toggle_row)
        elif temp > SET_temp:
            if state != 1:
                state = 1
                set_led_timer_freq(0.5)
        elif state != 2:
            state = 2
            set_led_timer_freq(0)

        if state != 0:
            timer_alarm.deinit()
            buzzer.duty_u16(0)
        else:        
            if row == 0:
                first_row = "ALARM"
            else:
                second_row = "ALARM"

        print(first_row)
        print(second_row)
        set_LCD(first_row, second_row)

        last = time.ticks_ms()

    


# if __name__ == '__main__':
#     main()
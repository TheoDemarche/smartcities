from machine import Pin, PWM
import time

def inter_lin(x, xmin, xmax, ymin, ymax):
    if x < xmin or x > xmax:
        print("Erreur, la valeur n'est pas comprise dans la plage : %s pas dans %s-%s" % [x, xmin, xmax])
        x = max(xmin, min(x, xmax))

    pente = (ymax-ymin) / (xmax-xmin)
    y = x * pente + ymin
    return int(y)

def turn_to_deg(deg, pwm : PWM):
    duty = inter_lin(deg, 0, 180, 3277, 15400)
    pwm.duty_u16(duty)

def main():
    servo_pin = Pin(20)
    servo_pwm = PWM(servo_pin)
    servo_pwm.freq(100)

    deg = 50
    duty = inter_lin(deg, 0, 180, 3277, 15400)
    print(duty)
    servo_pwm.duty_u16(duty)
    time.sleep(2)

if __name__ == "__main__":
    main()

'''
0.5 ms => 500  / 10000 * 65535 = 3277
2.5 ms => 2500 / 10000 * 65535 = 16384
Angle trop grand => 2.35 ms => 15400
'''
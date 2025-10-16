from lcd1602 import LCD1602
from dht20 import DHT20
from machine import I2C,Pin,ADC,Timer, PWM
import time

# Variables globales
ECART_TEMP_ALARME = 3   # Ecart avec la température fixée au dela du quel l'alarme se déclenche
STATE_ALARME = 0        # Température trop haute (alarme)
STATE_HAUT = 1          # Température au-dessus du seuil
STATE_NORMAL = 2        # Température normale
state = STATE_NORMAL    # État du système

# Définition variable pour écran LCD
i2c1 = I2C(1)                        # Bus I2C utilisé pour l’écran LCD
LCD = LCD1602(i2c1, 2, 16)           # Initialisation de l’écran 2x16 caractères
LCD.display()
first_row = ""                       # Texte de la première ligne
second_row = ""                      # Texte de la seconde ligne

# Gestion de l’alternance d’affichage de l’alarme
row = 0                         #Ligne utilisé par le message d'alarme
timer_alarm = Timer(-1)         #Timer pour l'alternance de la ligne utilisée
frequence_alarme = 1            #Fréquence pour l'alternance de la ligne

#Variable pour le capteur de température DHT20
i2c0_sda = Pin(8)
i2c0_scl = Pin(9)
i2c0 = I2C(0, sda=i2c0_sda, scl=i2c0_scl)
dht20 = DHT20(0x38, i2c0)
timer_temp = Timer(-1)
frequence_mesure = 1            #Fréquence pour la prise de mesure
temp = dht20.measurements['t']

#Variables pour le LED
led = Pin(18, Pin.OUT)
timer_led = Timer(-1)

#Variables pour le Buzzer
buzzer = PWM(Pin(27))
buzzer.freq(440)                     # Fréquence du son de l'alarme (La = 440 Hz)

#Variables pour le potentiomètre
ROTARY_ANGLE_SENSOR = ADC(0)
rot_min_value = 352                  # Valeur min mesurée (calibration)
rot_max_value = 65535 - 352          # Valeur max mesurée
set_min_value = 15                   # Température minimale réglable
set_max_value = 35                   # Température maximale réglable
set_plage = set_max_value - set_min_value
SET_temp = set_min_value             # Consigne initiale

#Fonctions pour le LCD
def set_LCD(str1, str2):
    """Efface et écrit deux lignes sur l’écran LCD."""
    LCD.clear()
    LCD.setCursor(0,0)
    LCD.print(str1)
    LCD.setCursor(0,1)
    LCD.print(str2)

def toggle_row(timer):
    """Inverse la ligne utilisée pour afficher le message d’alarme."""
    global row
    row = not row

#Fonctions pour le DHT20
def read_temp(timer):
    """Lit la température actuelle depuis le DHT20."""
    global temp
    temp = dht20.measurements['t']
    print(temp)

#Fonctions pour la LED
def toggle_led(timer):
    """Inverse l’état de la LED (clignotement)."""
    led.toggle()

def set_led_timer_freq(frequence):
    """Configure la fréquence de clignotement de la LED."""
    global timer_led
    if frequence > 0:
        timer_led.init(freq=frequence, mode=Timer.PERIODIC, callback=toggle_led)
    else:
        led.off()

#Fonctions pour le potentiomètre
def normalize_rotation(rot):
    """
    Convertit la valeur analogique du potentiomètre
    en une température comprise entre 15 et 35 °C.
    """
    rot -= rot_min_value
    rot /= rot_max_value
    rot *= set_plage
    rot += set_min_value
    return round(rot * 2) / 2



last = time.ticks_ms()

# Démarre la lecture de température périodique
timer_temp.init(freq=frequence_mesure, mode=Timer.PERIODIC, callback=read_temp)

def update_set_temperature():
    """Lit la température de consigne à partir du potentiomètre et la normalise."""
    global SET_temp
    SET_temp = normalize_rotation(ROTARY_ANGLE_SENSOR.read_u16())

def determine_state():
    """Détermine le nouvel état du système en fonction de la température."""
    global state, temp
    if temp > (SET_temp + ECART_TEMP_ALARME):
        print("alarme")
        return STATE_ALARME
    elif temp > SET_temp:
        return STATE_HAUT
    else:
        return STATE_NORMAL

def has_state_changed(new_state):
    """Vérifie si l'état à changer"""
    global state

    # Si aucun changement, ne rien faire
    if new_state == state:
        return False
    else:
        state = new_state  # Met à jour l’état actuel
        return True

def apply_state_actions(state):
    """Applique les actions nécessaires lors d’un changement d’état."""
    if state == STATE_ALARME:
        buzzer.duty_u16(32767)
        set_led_timer_freq(5)
        timer_alarm.init(freq=frequence_alarme, mode=Timer.PERIODIC, callback=toggle_row)
        return
    
    buzzer.duty_u16(0)
    timer_alarm.deinit()

    if state == STATE_HAUT:
        set_led_timer_freq(0.5)
    else: # state == STATE_NORMAL
        set_led_timer_freq(0)


def update_display():
    """Met à jour le contenu affiché sur le LCD."""
    global first_row, second_row

    if state == STATE_ALARME:
        if row == 0:
            first_row = "ALARM"
            second_row = f"Temp: {temp:.1f}°C"
        else:
            first_row = f"Set: {SET_temp:.1f}°C"
            second_row = "ALARM"
    else:
        first_row = f"Set: {SET_temp:.1f}°C"
        second_row = f"Ambient: {temp:.1f}°C"

    set_LCD(first_row, second_row)

while True:
    # Lecture de la consigne via potentiomètre
    update_set_temperature()

    if time.ticks_ms() - last > 100:

        new_state = determine_state()
        if has_state_changed(new_state):
            apply_state_actions(state)
        update_display()

        last = time.ticks_ms()

# if __name__ == '__main__':
#     main()
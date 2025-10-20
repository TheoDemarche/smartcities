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
text_alarm = "ATTENTION"        #Texte afficher pour l'alarme

mode_alarm = MODE_DEFILEMENT = 1             #(1) Activation du défilement (0) Clignotement

#Défilement
scroll_index = 0
direction_alarm = 0             #Gauche vers droite, 1 pour inverser
frequence_defilement = 2            #Fréquence pour l'alternance de la ligne

#Clignotement
frequence_clignotement = 1

#Variable pour le capteur de température DHT20
i2c0_sda = Pin(8)
i2c0_scl = Pin(9)
i2c0 = I2C(0, sda=i2c0_sda, scl=i2c0_scl)
dht20 = DHT20(0x38, i2c0)
timer_temp = Timer(-1)
frequence_mesure = 1            #Fréquence pour la prise de mesure
temp = dht20.measurements['t']

#Variables pour le LED
led = PWM(Pin(18)) #Pin(18, Pin.OUT)
timer_led = Timer(-1)
led_state = 0                   # Définit l'état de la LED
led_duty = 0
min_lum = 0.1                   #Luminosité minimale de la led (0-max)
max_lum = 1.0                   #Luminosité maximale de la led (min-1)
led.freq(1000)                  #Definit la fréquence du signal PWM de la led

#Variables pour le Buzzer
buzzer = PWM(Pin(27))
buzzer.freq(440)                    # Fréquence du son de l'alarme (La = 440 Hz)
buzzer_ON = 0                       # (0) buzzer désactivé (1) buzzer activé
buzzer_vol = 100                    # volume du buzzer entre 0 et 65535

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

def update_alarm(timer):
    """Fait défiler le mot ALARM vers la droite et change de ligne après un passage complet."""
    global scroll_index, first_row, second_row, row, text_alarm

    display_text = ""

    if mode_alarm == MODE_DEFILEMENT:
        # Ajouter 16 espaces avant et après pour que le texte commence hors écran et disparaisse complètement
        long_text = " " * 16 + text_alarm + " " * 16  
        longueur = len(long_text)
        # Fenêtre de 16 caractères pour l'affichage
        fin = ""
        debut = ""
        if direction_alarm == 0:
            fin = longueur - scroll_index
            debut = fin - 16
        else:
            fin = scroll_index
            debut = scroll_index + 16
        display_text = long_text[debut:fin] #scroll_index:scroll_index + 16

        scroll_index += 1

        # Quand tout le texte est passé, on recommence et on change de ligne
        if scroll_index > len(long_text) - 16:
            scroll_index = 0
            row = not row  # Change de ligne seulement après passage complet
    else:
        espace = 16 - len(text_alarm)
        esp_gauche = espace//2
        esp_droite = espace - esp_gauche
        display_text = " "*esp_gauche + text_alarm + " "*esp_droite

        row = not row

    # Affichage sur la ligne active
    if row == 0:
        first_row = display_text
        second_row = f"Temp: {temp:.1f}°C"
    else:
        first_row = f"Set: {SET_temp:.1f}°C"
        second_row = display_text

    set_LCD(first_row, second_row)

#Fonctions pour le DHT20
def read_temp(timer):
    """Lit la température actuelle depuis le DHT20."""
    global temp
    temp = dht20.measurements['t']

#Fonctions pour la LED
def toggle_led(timer):
    global led_state, led_duty
    print(led_duty)
    print(led_state)
    """Inverse l’état de la LED."""
    if led_state:
        led.duty_u16(led_duty)
    else:
        led.duty_u16(0)
    
    led_state = not led_state
    print(led_duty)
    print(led_state)

def set_led_timer_freq(frequence):
    """Configure la fréquence de clignotement de la LED."""
    global timer_led
    if frequence > 0:
        timer_led.init(freq=frequence, mode=Timer.PERIODIC, callback=toggle_led)
    else:
        led.deinit()

def update_led_duty():
    global led_duty
    proportion = (temp - SET_temp) / ECART_TEMP_ALARME
    plage_lum = (max_lum-min_lum) * proportion
    led_duty = int((plage_lum + min_lum) * 65535)
    print(led_duty)

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


#Autre fonctions
def update_set_temperature():
    """Lit la température de consigne à partir du potentiomètre et la normalise."""
    global SET_temp
    SET_temp = normalize_rotation(ROTARY_ANGLE_SENSOR.read_u16())

def determine_state():
    """Détermine le nouvel état du système en fonction de la température."""
    global state, temp
    if temp > (SET_temp + ECART_TEMP_ALARME):
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
    global index_alarm, led_duty
    """Applique les actions nécessaires lors d’un changement d’état."""
    if state == STATE_ALARME:
        if buzzer_ON:
            buzzer.duty_u16(buzzer_vol) #32767
        set_led_timer_freq(5)
        led_duty = 65535
        index_alarm = 0
        if mode_alarm == MODE_DEFILEMENT:
            timer_alarm.init(freq=frequence_defilement, mode=Timer.PERIODIC, callback=update_alarm)
        else:
            timer_alarm.init(freq=frequence_clignotement, mode=Timer.PERIODIC, callback=update_alarm)
        return
    
    buzzer.duty_u16(0)
    timer_alarm.deinit()

    if state == STATE_HAUT:
        set_led_timer_freq(0.5)
    else: # state == STATE_NORMAL
        set_led_timer_freq(0)
        led_duty = 0

def update_display():
    """Met à jour le LCD pour les autres états que l'alarme."""
    global first_row, second_row

    if state == STATE_ALARME:
        # On laisse le timer scroll_alarm gérer l'affichage
        return

    # Sinon on affiche la consigne et la température normale
    first_row = f"Set: {SET_temp:.1f}°C"
    second_row = f"Ambient: {temp:.1f}°C"
    set_LCD(first_row, second_row)


def main():
    # global led_duty
    last = time.ticks_ms()

    # Démarre la lecture de température périodique
    timer_temp.init(freq=frequence_mesure, mode=Timer.PERIODIC, callback=read_temp)

    while True:
        # Lecture de la consigne via potentiomètre
        update_set_temperature()

        if time.ticks_ms() - last > 100:
            new_state = determine_state()

            if new_state == STATE_HAUT:
                update_led_duty()
            # elif new_state == STATE_ALARME:
            #     led_duty = 65535
            
            if has_state_changed(new_state):
                apply_state_actions(state)
            update_display()

            last = time.ticks_ms()

if __name__ == '__main__':
    main()
from lcd1602 import LCD1602
from dht20 import DHT20
from machine import I2C,Pin,ADC,Timer, PWM
import time

# Variables globales
ECART_TEMP_ALARME = 3               # Ecart avec la température fixée au dela du quel l'alarme se déclenche
STATE_ALARME = 0                    # Température trop haute (alarme)
STATE_HAUT = 1                      # Température au-dessus du seuil
STATE_NORMAL = 2                    # Température normale
state = STATE_NORMAL                # État du système

# Définition variable pour écran LCD
i2c1 = I2C(1)                       # Bus I2C utilisé pour l’écran LCD
LCD = LCD1602(i2c1, 2, 16)          # Initialisation de l’écran 2x16 caractères
LCD.display()
first_row = ""                      # Texte de la première ligne
second_row = ""                     # Texte de la seconde ligne

# Gestion de l’alternance d’affichage de l’alarme
row = 0                             #Ligne utilisé par le message d'alarme (0= première, 1 = seconde)
timer_alarm = Timer(-1)             #Timer pour l'alternance de la ligne utilisée
text_alarm = "ALARM"                #Texte afficher pour l'alarme

MODE_DEFILEMENT = 1
MODE_CLIGNOTEMENT = 0
mode_alarm = MODE_DEFILEMENT        # Activation du défilement ou du Clignotement

#Défilement de l'alarme
scroll_index = 0                    # Position courant dans le texte
direction_alarm = 0                 # 0 = Gauche vers droite, 1 = Droite vers gauche
frequence_defilement = 2            # Fréquence de mise à jour du défilement

#Clignotement de l'alarme
frequence_clignotement = 1          # Fréquence de clignotement

# Capteur de température DHT20
i2c0_sda = Pin(8)
i2c0_scl = Pin(9)
i2c0 = I2C(0, sda=i2c0_sda, scl=i2c0_scl)
dht20 = DHT20(0x38, i2c0)
timer_temp = Timer(-1)
frequence_mesure = 1                #Fréquence de lecture du capteur / prise de mesure
temp = dht20.measurements['t']      # Dernière température mesurée

# LED
led = PWM(Pin(18))
timer_led = Timer(-1)
led_state = 0                       # Etat courant de la LED (0=éteinte, 1= allumée)
led_duty = 0                        # Duty cycle du PWM
min_lum = 0.1                       # Luminosité minimale de la led (0-max)
max_lum = 1.0                       # Luminosité maximale de la led (min-1)
led.freq(1000)                      # Fréquence du PWM de la led

# Buzzer
buzzer = PWM(Pin(27))
buzzer.freq(440)                    # Fréquence du son de l'alarme (La = 440 Hz)
buzzer_ON = 1                       # Activation du buzzer (0=désactivé, 1=activé)
buzzer_vol = 500                    # Volume du buzzer (0-65535)

# Potentiomètre
ROTARY_ANGLE_SENSOR = ADC(0)
rot_min_value = 352                 # Valeur ADC minimale mesurée (calibration)
rot_max_value = 65535 - 352         # Valeur ADC maximale mesurée
set_min_value = 15                  # Température minimale réglable (°C)
set_max_value = 35                  # Température maximale réglable (°C)
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
    """
    Gère l'affichage de l'alarme selon le mode sélectionné (défilement ou clignotement).
    
    En mode défilement : fait défiler le texte 'ALARM' avec un effet de défilement continu
    En mode clignotement : alterne l'affichage entre les lignes à fréquence régulière
    """
    global scroll_index, first_row, second_row, row, text_alarm

    display_text = ""

    if mode_alarm == MODE_DEFILEMENT:
        # TECHNIQUE DU DÉFILEMENT :
        # On crée un texte long avec des espaces avant et après pour permettre
        # un défilement fluide depuis l'extérieur de l'écran
        long_text = " " * 16 + text_alarm + " " * 16  
        longueur = len(long_text)

        # Calcul de la fenêtre visible (16 caractères) selon la direction
        fin = ""
        debut = ""
        if direction_alarm == 0:
            # Défilement gauche → droite : on prend une fenêtre qui avance
            fin = longueur - scroll_index
            debut = fin - 16
        else:
            # Défilement droite → gauche : on prend une fenêtre qui recule 
            fin = scroll_index
            debut = scroll_index + 16
        display_text = long_text[debut:fin] #scroll_index:scroll_index + 16

        scroll_index += 1

        # Réinitialisation et changement de ligne après un cycle complet
        if scroll_index > len(long_text) - 16:
            scroll_index = 0
            row = not row  # Alterne entre ligne 0 et 1
    else:
        # MODE CLIGNOTEMENT : Centre le texte et alterne entre les lignes
        espace = 16 - len(text_alarm)
        esp_gauche = espace//2
        esp_droite = espace - esp_gauche
        display_text = " "*esp_gauche + text_alarm + " "*esp_droite

        row = not row # Alterne la ligne à chaque appel

    # Application de l'affichage selon la ligne active
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
    """
    Callback du timer LED : alterne entre allumé (avec luminosité PWM) et éteint.
    
    Cette fonction est appelée périodiquement par le timer pour créer l'effet de clignotement.
    """
    global led_state, led_duty
    if led_state:
        led.duty_u16(led_duty)      # Allume avec la luminosité courante
    else:
        led.duty_u16(0)             # Éteint complètement
    
    led_state = not led_state       # Alterne l'état pour le prochain appel

def set_led_timer_freq(frequence):
    """Configure la fréquence de clignotement de la LED."""
    global timer_led
    if frequence > 0:
        # Démarre le timer avec la fréquence spécifiée
        timer_led.init(freq=frequence, mode=Timer.PERIODIC, callback=toggle_led)
    else:
        # Arrête le timer et éteint la LED
        led.deinit()

def update_led_duty():
    """
    Calcule la luminosité PWM de la LED selon l'écart de température.
    
    Plus la température est proche du seuil d'alarme, plus la LED est brillante.
    Crée un effet de battement progressif (dimmer) comme demandé en bonus.
    """
    global led_duty
    
    # Calcul de la proportion (0 à 1) dans la plage d'alerte
    proportion = (temp - SET_temp) / ECART_TEMP_ALARME
    
    # Application de la plage de luminosité configurée
    plage_lum = (max_lum - min_lum) * proportion
    
    # Conversion en valeur PWM (0-65535)
    led_duty = int((plage_lum + min_lum) * 65535)

#Fonctions pour le potentiomètre
def normalize_rotation(rot):
    """
    Convertit la valeur analogique du potentiomètre en température de consigne.
    
    Processus de normalisation :
    1. Soustraction de la valeur minimale (offset)
    2. Normalisation entre 0 et 1
    3. Application de la plage température (15-35°C)
    4. Arrondi à 0.5°C près pour plus de précision
    
    Returns:
        float: Température de consigne entre 15 et 35°C
    """
    rot -= rot_min_value
    rot /= rot_max_value
    rot *= set_plage
    rot += set_min_value
    return round(rot * 2) / 2


#Autre fonctions
def update_set_temperature():
    """Lit et normalise la température de consigne à partir du potentiomètre."""
    global SET_temp
    SET_temp = normalize_rotation(ROTARY_ANGLE_SENSOR.read_u16())

def determine_state():
    """Détermine l'état du système selon l'écart entre température mesurée et consigne.
   - ALARME: > consigne + 3°C
   - HAUT: > consigne mais ≤ +3°C  
   - NORMAL: ≤ consigne
    """
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

    if new_state == state:
        return False             # Aucun changement détecté
    else:
        state = new_state        # Mise à jour de l'état global
        return True              # Changement détecté

def apply_state_actions(state):
    global scroll_index, led_duty
    """Applique les actions spécifiques à chaque état du système.
    
    Cette fonction est appelée uniquement lors d'un changement d'état."""
    if state == STATE_ALARME:
        # ÉTAT ALARME : Activation complète des alertes
        if buzzer_ON:
            buzzer.duty_u16(buzzer_vol)  # Démarre le buzzer
        set_led_timer_freq(5)            # LED rapide (5Hz)
        led_duty = 65535                 # Luminosité maximale
        scroll_index = 0                 # Réinitialise le défilement
        
        # Démarre l'affichage d'alarme selon le mode
        if mode_alarm == MODE_DEFILEMENT:
            timer_alarm.init(freq=frequence_defilement, mode=Timer.PERIODIC, callback=update_alarm)
        else:
            timer_alarm.init(freq=frequence_clignotement, mode=Timer.PERIODIC, callback=update_alarm)
        return
    
    # Désactivation des alertes pour les autres états
    buzzer.duty_u16(0)                   # Arrête le buzzer
    timer_alarm.deinit()                 # Arrête l'affichage d'alarme

    if state == STATE_HAUT:
        # ÉTAT HAUT : LED lente avec luminosité progressive
        set_led_timer_freq(0.5)          # LED lente (0.5Hz)
    else:  # state == STATE_NORMAL
        # ÉTAT NORMAL : Désactivation complète
        set_led_timer_freq(0)            # Arrête la LED
        led_duty = 0                     # Luminosité nulle

def update_display():
    """
    Met à jour l'affichage LCD pour les états normaux (non alarme).
    
    Pour l'état alarme, l'affichage est géré par le timer d'alarme.
    """
    global first_row, second_row

    if state == STATE_ALARME:
        # L'affichage d'alarme est géré par le timer → ne rien faire
        return

    # Affichage standard : consigne et température ambiante
    first_row = f"Set: {SET_temp:.1f}°C"
    second_row = f"Ambient: {temp:.1f}°C"
    set_LCD(first_row, second_row)


def main():
    last = time.ticks_ms()

    # Démarre la lecture périodique de température (1Hz)
    timer_temp.init(freq=frequence_mesure, mode=Timer.PERIODIC, callback=read_temp)

    while True:
        # Lecture continue de la consigne via potentiomètre
        update_set_temperature()

        # Vérification périodique de l'état (toutes les 100ms)
        if time.ticks_ms() - last > 100:
            new_state = determine_state()

            # Mise à jour de la luminosité LED si état HAUT (effet progressif)
            if new_state == STATE_HAUT:
                update_led_duty()
            
            # Vérification et application des changements d'état
            if has_state_changed(new_state):
                apply_state_actions(state)
            
            # Mise à jour de l'affichage (sauf en état alarme)
            update_display()

            last = time.ticks_ms()

if __name__ == '__main__':
    main()
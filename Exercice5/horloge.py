import time
import network
import urequests
import json
from machine import Pin, PWM, RTC
import gc
import sys
import io

SSID = "SSID"
PASSWORD = "mdp"

def connect_wifi(SSID, PASSWORD, timeout=10):
    '''
    Boucle while jusqu'à connection au wifi avec un timeout en secondes
    '''
    wlan = network.WLAN(network.STA_IF)     #Object : interface wifi (Wlan) en tant que client
    wlan.active(True)                       # Activation de l'interface
    try:
        if not wlan.isconnected():              # Si pas connecté à un réseau
            print("Connexion au Wi-Fi...")
            wlan.connect(SSID, PASSWORD)        # Etablissement de la connexion

            start_time = time.ticks_ms()
            while not wlan.isconnected():       # Delai entre les tests
                if time.ticks_diff(time.ticks_ms(), start_time) > timeout * 1000:
                    print("Erreur : impossible de se connecter au wifi après ", timeout, " secondes")
                    return None
                time.sleep(0.5)

        print("Connecté au Wi-Fi, adresse IP:", wlan.ifconfig()[0])
        return wlan
    except Exception as e:
        log_error(e, context="Fonction connect_wifi")
        return None

"""
Format de la réponse
{"utc_offset":"-01:00","timezone":"Etc/GMT+1","day_of_week":3,"day_of_year":309,"datetime":"2025-11-05T12:05:50.084920-01:00",
"utc_datetime":"2025-11-05T13:05:50.084920+00:00","unixtime":1762347950,"raw_offset":-3600,"week_number":45,"dst":false,
"abbreviation":"-01","dst_offset":0,"dst_from":null,"dst_until":null,"client_ip":"2a01:cc00:d160:1000:d96b:a0a5:fdef:7047"}
"""

def GET_request(url):
    global console_log
    '''Envoie une requète GET à l'URL spécifié'''
    try:
        response = urequests.get(url, timeout=10)   #Requète HTTP GET à l'API avec un timeout
        if response.status_code == 200:             #Si le code de status de la requète est de 200 alors c'est un succès
            text = response.text                    # Extraction du texte de la réponse
            response.close()                        #Fermeture de la connexion
            gc.collect()                            # Nettoie la mémoire RAM

            datetime_str = extract_response(text, '"datetime":"')
            if console_log:
                datetime_utc_str = extract_response(text, '"utc_datetime":"')
                datetime_utc_tuple = convert_datatime_to_tuple(datetime_utc_str)
                rtc.datetime((datetime_utc_tuple[0], datetime_utc_tuple[1], datetime_utc_tuple[2], 0, datetime_utc_tuple[3], datetime_utc_tuple[4], datetime_utc_tuple[5], 0))

            return datetime_str
        else:                                       #La requète à échouée
            print("Erreur : status code : ", response.status_code)
            response.close()                        #Fermeture de la connexion
            gc.collect()                            # Nettoie la mémoire RAM
            return None
            
    except Exception as e:
        if DEBUG:
            log_error(e, context="GET request")
        gc.collect()
        return None

def extract_response(text, cle_str):
    try:
        start = text.find(cle_str)         # Recherche de datetime
        if start != -1:                         # Si trouve une valeur
            start += len(cle_str)          # Incremente l'index de la taille de la clé
            end = text.find('"', start)         # Cherche la fin de la valeur à partir du début
            sortie = text[start:end]      # Extrait la valeur à l'aide des 2 index
            if DEBUG:
                print("extraction obtenu : ", sortie)
            return sortie
    except Exception as e:
        log_error(e, context="Fonction extract response")

def convert_datatime_to_tuple(datetime_str):
    '''
    Traitement du datetime string de Format : 2025-11-05T14:37:18.063121+01:00
    '''
    try:
        date_part, time_part = datetime_str.split('T')          # Sépare en 2025-11-05 et en 14:37:18.063121+01:00
        year, month, day = map(int, date_part.split('-'))       # Sépare l'année, le mois et le jour
        time_part = time_part.split('.')[0]                     # Enlève la partie après les secondes et le fuseau => 14:37:18 
        hour, minute, second = map(int, time_part.split(':'))   #Sépare les heures, les minutes et les secondes
        
        return [year, month, day, hour, minute, second]
    except Exception as e:
        log_error(e, context="Fonction convert datetime to tuple")
        return [0, 0, 0, 0, 0, 0]

def UTC_to_GMT(utc_offset=1):
    # inversion du signe pour passer du format utc au format GMT demandé par l'API
    if utc_offset >= 0:
        gmt_offset = f"-{utc_offset}" if utc_offset > 0 else ""
    else:
        gmt_offset = f"+{abs(utc_offset)}"
    return gmt_offset

def get_time(utc_offset):
    try:
        gmt_offset = UTC_to_GMT(utc_offset)
        url = f"http://worldtimeapi.org/api/timezone/Etc/GMT{gmt_offset}" #lien de requête
        if DEBUG:
            print(f"Requête: {url}")

        data = GET_request(url)

        if data:
            temps = convert_datatime_to_tuple(data)
            return temps
        return None
    except Exception as e:
        log_error(e, context="Fonction get time")
        return [0, 0, 0, 0, 0, 0]

def update_time(format, servo_pwm):
    global current_time
    temps = get_time(utc_offset)
    if temps:
        current_time = temps
        print(f"Heure : {temps[3]:02d}:{temps[4]:02d}:{temps[5]:02d}")
        minutes = 60 * temps[3] + temps[4]
        update_angle(minutes, format, servo_pwm)

def update_angle(minutes, format, servo_pwm):
    deg = hour_to_deg(minutes, format)
    if DEBUG:
        print("Angle : ", deg)
    turn_to_deg(deg, servo_pwm)

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

def hour_to_deg(minutes, format):
    minutes = minutes % (format*60)
    deg = minutes/(format * 60) * 180            #format 24h : 0 -> 180
    if format == 12:
        deg = 180 - deg                 #format 12h : 180 -> 0
    return deg

def button_pressed(PIN):
    global format, last_button, button_timer, servo_pwm, current_time
    try:
        if DEBUG:
            print("Button pressed")
            print("Delay depuis le dernier : ", time.ticks_diff(time.ticks_ms(), last_button))
        if time.ticks_diff(time.ticks_ms(), last_button) < 500:
            format = 12 if format == 24 else 24
            print("format mit à jour : ", format)
            button_timer = 0
            minutes = 60* current_time[3] + current_time[4]
            update_angle(minutes, format, servo_pwm)
        else:
            button_timer = 1
        last_button = time.ticks_ms()
    except Exception as e:
        log_error(e, context="Fonction irq button pressed")

def change_fuseau():
    global utc_offset, button_timer, current_time, format, servo_pwm
    if utc_offset < 12:
        utc_offset += 1
    else:
        utc_offset = -12

    offset_hour = (current_time[3] + 1) % 24
    minutes = 60* offset_hour + current_time[4]

    update_angle(minutes, format, servo_pwm)
    button_timer = 0

    print("Le fuseau horaire à changé : UTC ", utc_offset)

def get_local_time_str():
    """Retourne l'heure actuelle du système formatée."""
    try:
        t = time.localtime()
        return "%04d-%02d-%02d %02d:%02d:%02d" % (t[0], t[1], t[2], t[3], t[4], t[5])
    except:
        return "0000-00-00 00:00:00"

def log_error(e, context=""):
    """Affiche une erreur détaillée avec horodatage UTC"""
    ts = get_local_time_str()
    print("\n--- ERREUR ---")
    print("Heure UTC :", ts)
    if context:
        print("Contexte :", context)
    print("Type :", type(e).__name__)
    print("Message :", e)
    sys.print_exception(e)
    print("--------------\n")

DEBUG = True

rtc = RTC()
console_log = True

servo_pin = Pin(20)
servo_pwm = PWM(servo_pin)
servo_pwm.freq(100)

BUTTON = Pin(16, Pin.IN)
BUTTON.irq(trigger=Pin.IRQ_RISING, handler=button_pressed)

last_button = time.ticks_ms()
utc_offset = 1
format = 3
button_timer = 0
current_time = [0, 0, 0, 0, 0, 0]


connect_wifi(SSID, PASSWORD)

last = time.ticks_ms()
while True:
    try:
        if button_timer:
            if time.ticks_diff(time.ticks_ms(), last_button) > 500:
                change_fuseau()
                update_time(format, servo_pwm)
                last = time.ticks_ms()
        
        if time.ticks_diff(time.ticks_ms(), last) > 5000:
            update_time(format, servo_pwm)
            last = time.ticks_ms()
        
    except Exception as e:
        log_error(e, context="Boucle principale")
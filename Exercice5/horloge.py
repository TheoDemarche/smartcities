import time
import network
import urequests
from machine import Pin, PWM, RTC
import gc
import sys
import io
import uos

# CONFIGURATION

SSID = "SSID"                               # Nom du wifi
PASSWORD = "mdp"                            # Mot de passe du wifi

# Gestion de la connexion wifi
CONNECTION_MODE = 0                         # 0 = exception à la déconnexion, 1 = delai de reconnexion
CONNECTION_DELAI = 10                       # Delai en secondes avec la tentative de reconnexion (s)

DEBUG = True                                # Affiche différent message pour aider au debug
CONSOLE_LOG = True                          # Affiche les erreurs détaillées dans la console
FILE_LOG = True                             # Enregistre les erreurs dans un fichier du raspberry
LOG_FILE_NAME = "error_log.txt"             # Nom du fichier de log
MAX_LOG_SIZE = 10 * 1024                    # Limite de la taille du fichier de log (10*1024 = 10 ko)

DELAI_REQUETE = 5000                        # Intervalle entre deux mises à jour de l'heure (ms)
TIMEOUT_REQUETE = 10000                     # Timeout de la requète (ms)
DELAI_DOUBLE_CLICK = 1000                   # Durée maximale pour le double click (ms) (double-click sur intervalle inférieur)
DELAI_REBOND = 100                          # Anti-rebond pour le bouton

# Variables globales
rtc = RTC()                                 # Horloge interne

servo_pin = Pin(20)
servo_pwm = PWM(servo_pin)                  # Signal PWM du servo moteur controllant l'angle
servo_pwm.freq(100)                         # Fréquence du servo moteur utilisé

BUTTON = Pin(16, Pin.IN)                    # Bouton permettant de controllé le fuseau et le format

last_button = time.ticks_ms()               # Timestamp de la dernière pression
button_timer = 0                            # Timer pour double_click

utc_offset = 1                              # Fuseau horaire par défaut (UTC+1)
format = 12                                 # Format horaire (alternant entre 12 et 24 heures)

# Fonctions Mathématique et conversion

def inter_lin(x, xmin, xmax, ymin, ymax):
    """
    Interpolation linéaire : convertit x d'une plage [xmin, xmax] vers [ymin, ymax]
    """
    if x < xmin or x > xmax:
        print(f"Erreur, la valeur n'est pas comprise dans la plage : {x} pas dans {xmin}-{xmax}")
        x = max(xmin, min(x, xmax))

    pente = (ymax-ymin) / (xmax-xmin)
    y = round((x - xmin) * pente + ymin)
    return int(y)

def hour_to_deg(minutes, format):
    """
    Convertit les minutes depuis minuit en angle pour le servo.
    - format 24h : 0-180°
    - format 12h : inversion de l'angle (180-0°)
    """
    minutes = minutes % (format*60)
    deg = minutes/(format * 60) * 180           #format 24h : 0 -> 180
    if format == 12:
        deg = 180 - deg                         #format 12h : 180 -> 0
    return deg

def UTC_to_GMT(utc_offset=1):
    """
    Convertit un offset UTC en format GMT attendu par l'API worldtimeapi.org.
    Inversion de l'offset UTC+1 => GMT-1
    """
    return f"{'+' if utc_offset < 0 else '-'}{abs(utc_offset)}"

# Fonctions servo moteur

def turn_to_deg(deg, pwm : PWM):
    """
    Positionne le servo à l'angle spécifié.
    """
    duty = inter_lin(deg, 0, 180, 3277, 15400)  # interpolation de l'angle entre 0 et 180° vers les correspondances en duty_cyle
    pwm.duty_u16(duty)

def update_angle(minutes, format, servo_pwm, debug):
    """
    Calcule l'angle du servo selon l'heure et positionne le servo
    """
    deg = hour_to_deg(minutes, format)          # Transforme l'heure en angle
    if debug:
        print("Angle : ", deg)
    turn_to_deg(deg, servo_pwm)                 # Positionne le servo moteur

# Fonctions réseau et requête

def connect_wifi(SSID, PASSWORD, timeout=10, log=False):
    '''
    Connecte le microcontrôleur au Wi-Fi.
    Boucle jusqu'à connexion ou dépassement du timeout.
    '''
    wlan = network.WLAN(network.STA_IF)         # Object : interface wifi (Wlan) en tant que client
    wlan.active(True)                           # Activation de l'interface
    try:
        if not wlan.isconnected():              # Si pas connecté à un réseau
            print("Connexion au Wi-Fi...")
            wlan.connect(SSID, PASSWORD)        # Etablissement de la connexion

            start_time = time.ticks_ms()        # Début du timer de timeout
            while not wlan.isconnected():       # Delai entre les tests
                if time.ticks_diff(time.ticks_ms(), start_time) > timeout * 1000:       # retourne rien si le timeout est dépassé
                    print("Erreur : impossible de se connecter au wifi après ", timeout, " secondes")
                    return None
                time.sleep(0.5)

        print(f"Connecté au Wi-Fi : {SSID}, adresse IP:", wlan.ifconfig()[0])
        return wlan
    except Exception as e:
        if log:
            log_error(e, context="Fonction connect_wifi")
        return False

def extract_response(text, cle_str, log=False, debug=False):
    """
    Extrait la valeur d'une clé spécifique dans une chaîne JSON brute.
    """
    try:
        start = text.find(cle_str)              # Recherche de la clé (datetime)
        if start != -1:                         # Si trouve une valeur
            start += len(cle_str)               # Incremente l'index de la taille de la clé pour commencer au début de la valeur recherchée
            end = text.find('"', start)         # Cherche la fin de la valeur à partir du début
            sortie = text[start:end]            # Extrait la valeur à l'aide des 2 index
            if debug:
                print("extraction obtenu : ", sortie)
            return sortie
    except Exception as e:
        if log:
            log_error(e, context="Fonction extract response")

def GET_request(url, log=False, debug=False):
    '''
    Requête HTTP GET vers l'URL donnée.
    Retourne le texte de la réponse (JSON brut).
    '''
    response = None                                 # Initialisation de la réponse
    try:
        gc.collect()                                # Nettoie la mémoire RAM avant la requête
        response = urequests.get(url, timeout=10)   # Requête HTTP GET à l'API avec un timeout
        if response.status_code == 200:             # Si le code de status de la requête est de 200 alors c'est un succès
            data = response.text                    # Extraction du texte de la réponse
            response.close()                        # Fermeture de la connexion
            gc.collect()                            # Nettoie la mémoire RAM

            return data
        else:                                       # La requête à échouée
            print(f"Erreur HTTP: status code : {response.status_code}")
            response.close()                        # Fermeture de la connexion
            gc.collect()                            # Nettoie la mémoire RAM
            return None
            
    except Exception as e:
        if debug:
            print("La requête à échouée : ", e)
        if log:
            log_error(e, context="GET request")
        gc.collect()
        return None

    finally:
        if response:                                # Si il y a eu une réponse
            response.close()                        # Fermeture de la réponse

"""
Format de la réponse
{"utc_offset":"-01:00","timezone":"Etc/GMT+1","day_of_week":3,"day_of_year":309,"datetime":"2025-11-05T12:05:50.084920-01:00",
"utc_datetime":"2025-11-05T13:05:50.084920+00:00","unixtime":1762347950,"raw_offset":-3600,"week_number":45,"dst":false,
"abbreviation":"-01","dst_offset":0,"dst_from":null,"dst_until":null,"client_ip":"2a01:cc00:d160:1000:d96b:a0a5:fdef:7047"}
"""

# Fonctions gestion de l'heure

def convert_datetime_to_tuple(datetime_str, log=False, debug=False):
    """
    Convertit une chaîne datetime API : 2025-11-05T14:37:18.063121+01:00 en liste [année, mois, jour, heure, minute, seconde].
    """
    try:
        date_part, time_part = datetime_str.split('T')          # Sépare en 2 partie : partie jour : 2025-11-05 et partie heure 14:37:18.063121+01:00
        year, month, day = map(int, date_part.split('-'))       # Sépare l'année, le mois et le jour
        time_part = time_part.split('.')[0]                     # Enlève la partie après les secondes et le fuseau => 14:37:18 
        hour, minute, second = map(int, time_part.split(':'))   # Sépare les heures, les minutes et les secondes
        
        return [year, month, day, hour, minute, second]         # Retourne les différentes valeurs dans une liste
    except Exception as e:
        if log:
            log_error(e, context="Fonction convert datetime to tuple")
        return [0, 0, 0, 0, 0, 0]                               # Retourne une liste vide

def extract_datetimes(data, debug):
    """
    Extrait datetime et utc_datetime depuis le JSON brut
    """
    datetime_str = extract_response(data, '"datetime":"', debug)
    datetime_utc_str = extract_response(data, '"utc_datetime":"', debug)

    if debug:
        print(f"Datetime: {datetime_str}")
        print(f"UTC Datetime: {datetime_utc_str}")

    return datetime_str, datetime_utc_str

def get_time(utc_offset, log=False, debug=False):
    """
    Récupère l'heure depuis worldtimeapi.org et met à jour le RTC interne.
    """
    try:
        gmt_offset = UTC_to_GMT(utc_offset)
        url = f"http://worldtimeapi.org/api/timezone/Etc/GMT{gmt_offset}"       # URL de la requête
        if debug:
            print(f"Requête: {url}")

        data = GET_request(url, log, debug)                                     # Requete à l'API
        if not data:
            return None
        
        datetime_str, datetime_utc_str = extract_datetimes(data, debug)         # Extraction des datetimes depuis la réponse de l'API

        if datetime_utc_str:
            datetime_utc_tuple = convert_datetime_to_tuple(datetime_utc_str, log, debug)                        # Conversion en tuple
            rtc.datetime((datetime_utc_tuple[0], datetime_utc_tuple[1], datetime_utc_tuple[2]                   # Mise à joure de l'heure interne du microcontroller
                          , 0, datetime_utc_tuple[3], datetime_utc_tuple[4], datetime_utc_tuple[5], 0))
        if datetime_str:
            temps = convert_datetime_to_tuple(datetime_str, log, debug)                 # Conversion en tuple
            return temps                                                                # Renvoie l'heure demandé (avec offset)
        return None
    except Exception as e:
        if log:
            log_error(e, context="Fonction get time")
        return [0, 0, 0, 0, 0, 0]

def update_time(format, servo_pwm, log=False, debug=False) -> bool:
    """
    Met à jour l'heure et position du servo selon l'heure récupérée.
    Retourne True si la mise à jour a réussi, False sinon.
    """
    try:
        temps = get_time(utc_offset, log, debug)                                # Obtention du temps par l'API
        if temps:                                                               # Si une heure est obtenue
            print(f"Heure : {temps[3]:02d}:{temps[4]:02d}:{temps[5]:02d}")
            minutes = 60 * temps[3] + temps[4]                                  # Convertit l'heure obtenue en minutes depuis minuit
            update_angle(minutes, format, servo_pwm, debug)                     # Détermine l'angle correspondant et tourne le servo moteur
            return True
        else:
            if debug:
                print("Echec de la récupération de l'heure")
            return False
    except Exception as e:
        if log:
            log_error(e, context="Fonction update time : temps non obtenu")
        return False

# Fonctions de gestion des erreurs

def get_local_time_str():
    """
    Retourne l'heure locale du système formatée en chaîne 'YYYY-MM-DD HH:MM:SS'.
    """
    try:
        t = rtc.datetime()                      # Heure du système (mise à jour à l'heure UTC)
        return "%04d-%02d-%02d %02d:%02d:%02d" % (t[0], t[1], t[2], t[4], t[5], t[6])
    except:
        return "0000-00-00 00:00:00"

def log_error(e, context=""):
    """
    Si CONSOLE_LOG alors écris les erreurs dans la console
    Si FILE_LOG alors enregistre les erreurs dans un fichier : LOG_FILE_NAME de taille maximale MAX_LOG_SIZE
    """
    global CONSOLE_LOG, FILE_LOG, LOG_FILE_NAME, MAX_LOG_SIZE
    ts = get_local_time_str()
    msg = (                                                 # début du message d'erreur
        "\n--- ERREUR ---\n"
        f"Heure UTC : {ts}\n"                               # Heure du système (si l'heure actualisé correctement alors correspond à l'heure UTC)
        + (f"Contexte : {context}\n" if context else "")    # Ajout du contexte : Ou a eu lieu l'erreur
    )

    buf = io.StringIO()                             # Buffer mémoire temporaire
    sys.print_exception(e, buf)                     # Ecriture de l'erreur dans le buffer
    msg += buf.getvalue() + "--------------\n"      # Ajout de l'erreur et de démarcation

    # --- Console ---
    if CONSOLE_LOG:
        print(msg)                                  # Ecris l'erreur dans la console

    # --- Fichier ---
    if FILE_LOG:
        try:
            if LOG_FILE_NAME in uos.listdir():              # Vérifie que le fichier existe
                size = uos.stat(LOG_FILE_NAME)[6]           # Taille du ficher de log
                if size >= MAX_LOG_SIZE:                    # Si la taille est supérieur à la limite alors on n'écris plus
                    print("[LOG] Taille max atteinte, arrêt de l’écriture dans le fichier.")
                    return
            with open(LOG_FILE_NAME, "a") as f:             # Si la taille est inférieur
                f.write(msg)                                # Ecriture de l'erreur dans le fichier
        except Exception as err:
            print(f"[LOG ERROR] Échec d’écriture dans le fichier : {err}")

# Fonctions bouton

def button_pressed(Pin):
    """
    Interruption déclenchée par le bouton.
    Change le format horaire si pressé rapidement et met à jour l'angle du servo.
    """
    global format, last_button, button_timer, servo_pwm, CONSOLE_LOG, DEBUG, DELAI_DOUBLE_CLICK, DELAI_REBOND, BUTTON
    try:
        time_diff = time.ticks_diff(time.ticks_ms(), last_button)           # Intervalle de temps depuis la dernière pression
        if DEBUG:
            print("Button pressed")
            print("Delay depuis le dernier : ", time_diff)
        if time_diff < DELAI_REBOND:                                        # Si l'intervalle est trop courte alors il s'agit d'un rebond (plusieurs flan montant détecté au lieu d'un) => rien n'est fait
            if DEBUG:
                print("Rebond détecté")
            return
        if time_diff < DELAI_DOUBLE_CLICK:                                  # Si l'intervalle de temps est inférieur au delai de double click alors changement de format
            format = 12 if format == 24 else 24                             # Changement du format 12 - 24 heures
            print("format mis à jour : ", format)
            button_timer = 0                                                # Désactivation du timer pour ne pas activer le changement de fuseau
            offset_hour = (rtc.datetime()[4] + utc_offset) % 24             # Estimation de l'heure théorique a partir de l'heure système et de l'offset UTC
            minutes = 60* offset_hour + rtc.datetime()[5]                   
            update_angle(minutes, format, servo_pwm, DEBUG)                 # Changement de l'angle avec l'heure estimée
        else:
            button_timer = 1                                                # Sinon activation du timer de changement de fuseau
        last_button = time.ticks_ms()                                       # Mise à jour du timestamp de la dernière pression
    except Exception as e:
        if CONSOLE_LOG:
            log_error(e, context="Fonction irq button pressed")

def change_fuseau():
    """
    Incrémente le fuseau horaire (UTC offset) et ajuste l'angle du servo.
    Gère la boucle des fuseaux de -12 à +12.
    """
    global utc_offset, button_timer, format, servo_pwm, DEBUG, CONSOLE_LOG
    if utc_offset < 12:             # Incrementation et bouclage de l'offset UTC
        utc_offset += 1
    else:
        utc_offset = -12

    print("Le fuseau horaire à changé : UTC", utc_offset)
    try:
        offset_hour = (rtc.datetime()[4] + utc_offset) % 24                 # Estimation de l'heure théorique a partir de l'heure système et de l'offset UTC
        print(f"Heure approximée = {offset_hour}:{rtc.datetime()[5]}")
        minutes = 60* offset_hour + rtc.datetime()[5]

        update_angle(minutes, format, servo_pwm, DEBUG)                     # Changement de l'angle avec l'heure estimée

        button_timer = 0                                                    # Désactivation du timer
    except Exception as e:
        if CONSOLE_LOG:
            log_error(e, context="Fonction change fuseau")


def main():
    global last_button, button_timer, CONSOLE_LOG, DEBUG, DELAI_DOUBLE_CLICK, DELAI_REQUETE, TIMEOUT_REQUETE, CONNECTION_MODE, CONNECTION_DELAI

    try:
        BUTTON.irq(trigger=Pin.IRQ_RISING, handler=button_pressed)                  # Appel de la fonction de gestion à chaque flan montant du bouton

        while True:
            wlan = connect_wifi(SSID, PASSWORD)                                     # Connection au wifi
            if wlan:                                                                # Vérifiaction de la connection
                last_update = time.ticks_ms()                                       # Initialisation du timestamp de dernière mise à jour de l'heure
                while wlan.isconnected():                                           # Boucle tant que le raspberry est connecté au wifi
                    if button_timer:                                                # Si le timer du bouton est activé
                        if time.ticks_diff(time.ticks_ms(), last_button) > DELAI_DOUBLE_CLICK:      # Si l'intervalle de temps entre deux pression est supérieur au delai du double click alors changement de fuseau
                            change_fuseau()                                                         # Changement du fuseau
                            update_time(format, servo_pwm, CONSOLE_LOG, DEBUG)                      # Mise à jour de l'heure
                    
                    time_diff_update = time.ticks_diff(time.ticks_ms(), last_update)                # Intervalle de temps depuis la dernière mise à jour de l'heure
                    if time_diff_update > DELAI_REQUETE:                                            # Si l'intervalle est supérieur au delai alors mise à jour
                        if update_time(format, servo_pwm, CONSOLE_LOG, DEBUG):                      # Mise à jour de l'heure
                            last_update = time.ticks_ms()                                           # Si mise à jour de l'heure correctement éffectuée alors Mise à jour du timestamp de dernière mise à jour
                    elif time_diff_update > TIMEOUT_REQUETE:                                        # Si la mise à jour prend trop de temps
                        last_update = time.ticks_ms()                                               # Mise à jour forcée du temps de dernière mise à jour
            else:
                if CONNECTION_MODE == 0:                                            # Si mode 0 alors arret du programme
                    raise Exception("Connection au wifi échouée")
                else:
                    time.sleep(CONNECTION_DELAI)                                    # Sinon delai avant tentative de reconnexion
            
    except Exception as e:
        if CONSOLE_LOG:
            log_error(e, context="Fonction principale")


if __name__ == "__main__":
    main()
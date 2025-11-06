import time
import network
import urequests
import json

SSID = "SSID"
PASSWORD = "mdp"

def connect_wifi(SSID, PASSWORD):
    wlan = network.WLAN(network.STA_IF)     #Object : interface wifi (Wlan) en tant que client
    wlan.active(True)                       # Activation de l'interface
    if not wlan.isconnected():              # Si pas connecté à un réseau
        print("Connexion au Wi-Fi...")
        wlan.connect(SSID, PASSWORD)        # Etablissement de la connexion
        while not wlan.isconnected():       # Delai entre les tests
            time.sleep(0.5)
    print("Connecté au Wi-Fi, adresse IP:", wlan.ifconfig()[0])
    return wlan

"""{"utc_offset":"-01:00","timezone":"Etc/GMT+1","day_of_week":3,"day_of_year":309,"datetime":"2025-11-05T12:05:50.084920-01:00",
"utc_datetime":"2025-11-05T13:05:50.084920+00:00","unixtime":1762347950,"raw_offset":-3600,"week_number":45,"dst":false,
"abbreviation":"-01","dst_offset":0,"dst_from":null,"dst_until":null,"client_ip":"2a01:cc00:d160:1000:d96b:a0a5:fdef:7047"}"""

def GET_request(url):
    '''Envoie une requète GET à l'URL spécifié'''
    try:
        response = urequests.get(url, timeout=10)   #Requète HTTP GET à l'API avec un timeout
        if response.status_code == 200:             #Si le code de status de la requète est de 200 alors c'est un succès
            data = json.loads(response.text)        #Convertit la réponse (JSON) en dictionnaire python
            response.close()                        #Fermeture de la connexion
            return data
        else:                                       #La requète à échouée
            response.close()                        #Fermeture de la connexion
            return None
            
    except Exception as e:
        print(f"Erreur: {e}")
        return None

def convert_data_to_time(data):
    datetime_str = data['datetime']                         # Extrait le datetime du dictionnaire
    print(datetime_str)                                     # Format : 2025-11-05T14:37:18.063121+01:00

    date_part, time_part = datetime_str.split('T')          # Sépare en 2025-11-05 et en 14:37:18.063121+01:00
    year, month, day = map(int, date_part.split('-'))       # Sépare l'année, le mois et le jour
    time_part = time_part.split('.')[0]                     # Enlève la partie après les secondes et le fuseau => 14:37:18 
    hour, minute, second = map(int, time_part.split(':'))   #Sépare les heures, les minutes et les secondes
    
    return (year, month, day, hour, minute, second)

def UTC_to_GMT(utc_offset=1):
    # inversion du signe pour passer du format utc au format GMT demandé par l'API
    if utc_offset >= 0:
        gmt_offset = f"-{utc_offset}" if utc_offset > 0 else ""
    else:
        gmt_offset = f"+{abs(utc_offset)}"
    return gmt_offset

def get_time(utc_offset):
    gmt_offset = UTC_to_GMT(utc_offset)
    url = f"http://worldtimeapi.org/api/timezone/Etc/GMT{gmt_offset}" #lien de requête
    print(f"Requête: {url}")

    data = GET_request(url)
    while not data:
        time.sleep(1)
        data = GET_request(url)

    temps = convert_data_to_time(data)
    return temps

def main():
    # Connexion Wi-Fi
    connect_wifi(SSID, PASSWORD)

    # Utilisation simple
    print("Récupération de l'heure UTC+1...")
    utc_offset = 1

    temps = get_time(utc_offset)
    
    print(f"Heure : {temps[3]:02d}:{temps[4]:02d}:{temps[5]:02d}")


if __name__ == "__main__":
    main()
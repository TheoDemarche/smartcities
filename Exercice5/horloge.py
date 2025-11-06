import ntptime
import time
import network

SSID = "SSID"
PASSWORD = "mdp"

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connexion au Wi-Fi...")
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            time.sleep(0.5)
    print("Connecté au Wi-Fi, adresse IP:", wlan.ifconfig()[0])
    return wlan

connect_wifi()

ntptime.settime()
print("Local time after synchronization：%s" %str(time.localtime()))
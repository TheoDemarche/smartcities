from ws2812 import WS2812
from machine import ADC
from time import ticks_us, ticks_diff
import random

# Initialisation des composants
rgb_led = WS2812(18, 1)           # Bande LED RGB connectée au pin 18, avec 1 LED
sound_sensor = ADC(1)             # Capteur de son analogique connecté au canal ADC 1

# Paramètres de détection du son
sound_sliding_window_size = 10   # Taille de la fenêtre pour la moyenne glissante du bruit ambiant
sound_history = []               # Historique des niveaux sonores récents
average_noise_level = 15         # Niveau de bruit moyen initial
detection_threshold_factor = 1.5 # Facteur multiplicatif pour détecter un pic sonore (battement)
last_detection_time = ticks_us() # Timestamp de la dernière détection de battement

# Paramètres liés au rythme cardiaque (BPM)
MAX_BPM = 128                    # BPM maximal attendu (utilisé pour filtrer les détections trop rapides)
min_interval_between_beats = (60 * 10**6) / (MAX_BPM + 10)  # Intervalle minimal entre deux battements (en µs)
beat_sliding_window_size = 20   # Taille de la fenêtre pour la moyenne glissante des intervalles entre battements
beat_intervals = []             # Historique des intervalles entre battements détectés


# Fonctions

def read_filtered_noise(samples: int = 100, min_threshold: float = 5.0) -> float:
    """Lit le capteur sonore et retourne une moyenne filtrée."""
    total_noise = 0
    valid_samples = 0
    while valid_samples < samples:
        noise = sound_sensor.read_u16() / 256
        if noise > min_threshold:
            total_noise += noise
            valid_samples += 1
    return total_noise / samples

def moyenne_glissante(values: list, window_size: int) -> float:
    """Calcule la moyenne glissante sur une fenêtre donnée."""
    if len(values) > window_size:
        values.pop(0)
    return sum(values) / len(values)

def detect_beat(current_noise: float, average_noise_level: float, last_detection_time: int,
                threshold_factor: float, min_interval: float) -> tuple[bool, int | None]:
    """Détecte un battement si le bruit dépasse le seuil."""
    if current_noise > average_noise_level * threshold_factor:
        time_since_last = ticks_diff(ticks_us(), last_detection_time)
        if time_since_last > min_interval:
            print(f"Battement détecté : {current_noise} > {average_noise_level * threshold_factor}")
            return True, time_since_last
    return False, None

def update_led():
    """Allume la LED avec une couleur aléatoire."""
    random_color = tuple(random.randint(0, 255) for _ in range(3))
    rgb_led.pixels_fill(random_color)
    rgb_led.pixels_show()

def calcul_BPM(beat_intervals, beat_sliding_window_size):
    """Calcul du BPM."""
    if beat_intervals:
        average_interval = moyenne_glissante(beat_intervals, beat_sliding_window_size)
        bpm = 60 / (average_interval / 10**6)
        print(f"BPM = {bpm}")

# Fonction principale

def main():
    global last_detection_time, average_noise_level

    while True:
        current_noise = read_filtered_noise(samples=100, min_threshold=5.0)

        beat_detected, interval = detect_beat(
            current_noise, average_noise_level, last_detection_time,
            detection_threshold_factor, min_interval_between_beats)

        if beat_detected:
            last_detection_time = ticks_us()
            update_led()
            beat_intervals.append(interval)
            sound_history.append(current_noise * 0.75)              #Facteur 0.75 pour éviter une trop grande augmentation de la moyenne
            calcul_BPM(beat_intervals, beat_sliding_window_size)
        else:
            sound_history.append(current_noise)

        average_noise_level = moyenne_glissante(sound_history, sound_sliding_window_size)

        
if __name__ == "__main__":
    main()

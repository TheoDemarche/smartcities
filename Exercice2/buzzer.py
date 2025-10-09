import machine
import time

BUTTON = machine.Pin(16, machine.Pin.IN)        #PIN 16
buzzer = machine.PWM(machine.Pin(27))           #Pin A1

ROTARY_ANGLE_SENSOR = machine.ADC(0)            #PIN A0

# --- Frère Jacques ---
#Liste des différentes notes
notes_frere = [
    0,
    1046, 1175, 1318, 1046,
    1046, 1175, 1318, 1046,
    1318, 1397, 1568, 0,
    1318, 1397, 1568, 0
]
#Liste du temps entre chaque note
delays_frere = [
    0,
    400, 400, 400, 400,
    400, 400, 400, 400,
    400, 400, 800, 400,
    400, 400, 800, 400
]

# --- Star Wars (simplifié) ---
#Fréquence pour chaque note
freqs = {
    'C4': 262, 'D4': 294, 'E4': 330, 'F4': 349, 'G4': 392, 'A4': 440, 'B4': 494,
    'C5': 523, 'D5': 587, 'E5': 659, 'F5': 698, 'G5': 784, 'A5': 880, 'B5': 988
}

#Liste des différentes notes
notes_starwars = [
    freqs['A4'], freqs['A4'], freqs['F4'], freqs['C5'],
    freqs['A4'], freqs['F4'], freqs['C5'], freqs['A4'],
    freqs['E5'], freqs['E5'], freqs['E5'], freqs['F5'],
    freqs['C5'], freqs['G4'], freqs['F4']
]

#Liste du temps entre chaque note
delays_starwars = [
    400, 400, 400, 800,
    400, 400, 400, 800,
    400, 400, 400, 400,
    400, 400, 800
]

#Relie les notes et delay au mélodie et mise dans une liste de mélodies
frere = [notes_frere, delays_frere]
starwars = [notes_starwars, delays_starwars]
melodies = [frere, starwars]


last_note = time.ticks_ms()     #Tick du dernier changement de note
current_note = 0                #Note actuel de la mélodie
current_melodie = 0             #Numéro de la mélodie dans la liste
vol = 0                         #Variable représentant le duty cycle du PWM et donc le volume du buzzer

def play(note):                 #Fonction pour jouer une note
    if note == 0:               #Si note de 0 alors coupe le PWM / le buzzer
        buzzer.duty_u16(0)
    else:
        buzzer.freq(note)       #Sinon joue la note
        buzzer.duty_u16(vol)    #au volume actuel

#### GESTION du bouton et interuption #####

def change_melodie(PIN):                        #Handler lorsque le bouton est appuyer
    global current_melodie
    global current_note
    current_note = 0                            #Remet la première note de la mélodie
    current_melodie += 1                        #Passe à la mélodie suivante
    if current_melodie >= len(melodies):        #Remet la première mélodie à la fin de la liste
        current_melodie = 0

BUTTON.irq(trigger=machine.Pin.IRQ_RISING, handler=change_melodie)              #Interupteur appelant la fonction change melodie quand le bouton est activé (1 seule fois)



### Bouble principale ###
while True:
    vol = int(ROTARY_ANGLE_SENSOR.read_u16() // 4)                                          #Volume 

    if current_note >= len(melodies[current_melodie][0]):                                   #Recommence la mélodie en remettant la note à 0
        current_note = 0
    if time.ticks_ms() - last_note >= melodies[current_melodie][1][current_note]:           #Si le delay de la note est passé alors :
        play(melodies[current_melodie][0][current_note])                                    #On la joue
        last_note = time.ticks_ms()                                                         #On reprend le tick
        current_note += 1                                                                   #On passe à la note suivante

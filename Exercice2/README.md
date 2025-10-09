# Exercice 2

## Buzzer et capteur rotatif

---

### Objectif
L'objectif de cet exercice est de jouer différentes mélodies sur un buzzer et de contrôler le volume avec un capteur rotatif. Un bouton permet de changer de mélodie.

Le [pdf](./Exercice2.pdf) relatif à cet exercice contient plus d'explications sur les consignes et le matériel nécessaire.

---

### Logique

Le programme gère plusieurs mélodies et leur lecture sur un buzzer :
- **Mélodie Frère Jacques** : une suite de notes classiques.
- **Mélodie Star Wars (simplifiée)** : une version abrégée du thème.

Chaque mélodie est définie par :
1. Une liste de notes (fréquences en Hz, 0 = silence)
2. Une liste de durées entre chaque note (en millisecondes)

Le volume du buzzer est contrôlé par un capteur rotatif (potentiomètre analogique), converti en duty cycle pour le PWM.

---

### Fonctionnement

1. **Lecture des notes**  
   - La fonction `play(note)` joue la note demandée au volume actuel.
   - Si la note vaut `0`, le buzzer est coupé.

2. **Changement de mélodie avec le bouton**  
   - Une interruption est configurée sur le bouton : `BUTTON.irq`.
   - Lorsqu'on appuie sur le bouton, la fonction `change_melodie` :
     - Passe à la mélodie suivante
     - Remet la note courante à 0 pour recommencer la mélodie

3. **Volume via capteur rotatif**  
   - Dans la boucle principale, le capteur rotatif (`ROTARY_ANGLE_SENSOR`) est lu en continu.
   - La valeur lue est convertie en duty cycle PWM pour ajuster le volume du buzzer.

4. **Boucle principale**  
   - Vérifie si la mélodie est terminée et remet la note à 0 si nécessaire.
   - Vérifie si le délai de la note actuelle est écoulé pour passer à la note suivante.
   - Joue la note avec le volume courant.


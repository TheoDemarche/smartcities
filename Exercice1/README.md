#Exercice 1
##LED et bouton poussoir

###Objectif
L'objectif de cet exercice est de faire varier le clignotement d'une LED à partir d'un bouton poussoir.

###Logique

Tout d'abord, la LED peux varier entre 2 modes à l'aide d'une pression de plus d'une seconde:
1. Mode eteint : la LED est eteinte
2. Mode allumée : la LED fonctionne normalement et alterne entre 3 vitesse:
   1.Toutes les 2 secondes : 0,5 Hz
   2.Toutes les demi secondes : 2 Hz
   3.10 fois par seconde : 10 Hz


###fonctionnement
Dans une boucle while, la valeur du bouton est enregistrée et comparée à la dernière valeur (val et last_val) :
1. Si le bouton est pressé et qu'il ne l'était pas alors l'utilisateur a commencé à appuyer sur le bouton : Le temps en millisecondes est enregistré (last_pressed)
2. Si le bouton n'est pas pressé et qu'il l'était alors l'utilisateur à relaché le bouton :
   1. Si le temps depuis le début de la pression et le relachement est supérieur à 1 seconde, une variable booléenne est inversée (led_bool_abs) et définie le mode de fonctionnement
   2. Sinon un compteur est augmenté

le temps en millisecondes est enregistré (now) et en fonction de la valeur du compteur, est comparé au temps du dernier changement.
Si le delai est supérieur à celui demandé par la fréquence de clignotement alors la variable booléenne est inverse (led_bool) et le nouveau temps de dernier changement est enregistré (last)

Finalement :
1. Si la valeur des deux variables booléennes de mode (led_bool_abs) et de fréquence (led_bool) sont activée alors la LED est allumée
2. Sinon la led est eteinte

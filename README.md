# Étude statistique du jeu de la bataille

## 1. Introduction

Ce projet étudie par la simulation trois questions sur la bataille : combien de temps dure une partie, quelle part des donnes ne se termine jamais, et dans quelle mesure l'issue est déjà écrite dans la main distribuée. Le jeu ne comporte aucune décision : une fois les règles fixées, tout le hasard est dans le mélange initial.

Plusieurs travaux ont déjà abordé la terminaison et la durée des parties. [Spivey (2010)](https://math.colgate.edu/~integers/kg2/kg2.pdf) montre qu'un jeu de 52 cartes peut boucler indéfiniment, sur une version où toutes les cartes sont distinctes. [Lakshtanov et Roshchina (2012)](https://arxiv.org/abs/1007.1371) montrent que la durée espérée devient finie si l'ordre de ramassage est aléatoire. [Ben-Naim et Krapivsky (2002)](https://arxiv.org/abs/nlin/0108047) estiment la durée moyenne dans un modèle stochastique proche. Ces résultats portent sur des versions simplifiées du jeu. Ce projet étudie au contraire le jeu réel, avec quatre cartes par valeur, donc des batailles, et un ordre de ramassage fixe, pour mesurer empiriquement la fréquence des cycles et la distribution des durées.

La section 2 décrit les règles simulées, la section 3 la méthodologie. Les sections suivantes présentent les résultats par axe d'étude, puis les limites et la manière de reproduire l'étude.

## 2. Règles du jeu étudiées

La bataille n'a pas de règles officielles et presque chaque famille a sa variante. Les règles ci-dessous sont celles utilisées dans toutes les simulations, sauf mention contraire.

**Matériel et distribution**

- Un paquet de 52 cartes : 13 valeurs, 4 couleurs.
- Les couleurs n'ont aucune influence sur le jeu.
- Ordre des valeurs, de la plus faible à la plus forte : 2, 3, 4, 5, 6, 7, 8, 9, 10, Valet, Dame, Roi, As.
- Le paquet est mélangé uniformément puis distribué entièrement : 26 cartes pour chacun des deux joueurs.

**Déroulé d'un pli**

- Chaque joueur retourne la carte du dessus de son paquet.
- La carte la plus forte remporte le pli.
- Le gagnant place sous son paquet **d'abord sa propre carte, puis celle du perdant**. Cet ordre est fixe et ne varie jamais.

**Bataille**

- Si les deux cartes retournées ont la même valeur, il y a bataille.
- Chaque joueur pose une carte face cachée, puis une carte face visible.
- Les cartes visibles sont comparées. La plus forte remporte l'ensemble des cartes posées depuis le début du pli.
- En cas de nouvelle égalité, la bataille recommence de la même manière.
- Le gagnant ramasse d'abord ses propres cartes, dans l'ordre où il les a posées, puis celles du perdant, dans l'ordre où elles ont été posées.

**Fin de partie**

- Un joueur qui n'a plus de cartes perd la partie.
- Un joueur qui n'a pas assez de cartes pour terminer une bataille perd la partie.
- Une partie qui revient à un état déjà rencontré (même paquet pour chaque joueur, dans le même ordre) est déclarée **infinie** : le jeu étant déterministe, elle rejouerait la même séquence pour toujours.

## Références

- E. Ben-Naim, P. L. Krapivsky, [*Parity and ruin in a stochastic game*](https://doi.org/10.1140/epjb/e20020027), European Physical Journal B, 25, 2002, 239-243. Prépublication : [arXiv:nlin/0108047](https://arxiv.org/abs/nlin/0108047).
- J. Haqq-Misra, [*Predictability in the game of War*](https://www.scq.ubc.ca/?p=563), The Science Creative Quarterly, 2006.
- E. Lakshtanov, V. Roshchina, [*On Finiteness in the Card Game of War*](https://doi.org/10.4169/amer.math.monthly.119.04.318), American Mathematical Monthly, 119(4), 2012, 318-323. Prépublication : [arXiv:1007.1371](https://arxiv.org/abs/1007.1371).
- M. Z. Spivey, [*Cycles in War*](https://math.colgate.edu/~integers/kg2/kg2.pdf), Integers, 10, 2010, 747-764.
- [*Combinatorial Aspects of the Card Game War*](https://arxiv.org/abs/2202.00473), arXiv:2202.00473, 2022.

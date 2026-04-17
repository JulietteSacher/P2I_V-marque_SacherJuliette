# V-Marque

V-Marque est une application web de gestion de match de volley permettant de préparer une rencontre, suivre le match en direct, gérer les rotations et les changements, puis consulter les statistiques des équipes et des joueurs.


## Présentation du projet

Le projet est composé de deux parties :

- un backend en FastAPI qui gère la logique métier, les matchs, les équipes, les joueurs, les lineups, les rotations, les actions de jeu et les statistiques
- un frontend en Angular qui permet :
  - de créer la feuille de match
  - de suivre le match en direct
  - de visualiser le terrain
  - de saisir les actions
  - de consulter les statistiques

## Fonctionnalités principales

### Feuille de match
- création des deux équipes
- ajout des joueurs
- choix des couleurs d’équipe
- définition des positions initiales
- choix du nombre de sets gagnants
- choix de l’équipe qui sert au départ

### Match live
- affichage du score
- affichage du set en cours
- visualisation du terrain
- affichage des joueurs sur le terrain et sur le banc
- saisie des actions :
  - ace
  - faute de service
  - attaque gagnante
  - erreur d’attaque
  - contre gagnant
  - erreur de contre
- gestion des changements
- lancement du set suivant
- inversion des côtés à chaque changement de set

### Statistiques
- statistiques d’équipe
- statistiques individuelles
- recherche d’un joueur

## Installation et lancement 

git clone https://github.com/JulietteSacher/P2I_V-marque_SacherJuliette
cd P2I_V-marque_SacherJuliette

### Pour le backend
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
http://127.0.0.1:8000

### Pour les tests backend
cd backend
python -m pytest -vv

### Pour le frontend
cd frontend
npm install 
npm start
http://localhost:4200


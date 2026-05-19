# 🎮 Test Interactif - Guide d'Utilisation

## Lancement du Test

```bash
cd "/Users/val/Desktop/Pythoneries/DUNE Imperium Uprising"
python3 test/test_interactive_turn.py
```

## 📋 Ce que le Test Fait

Le test interactif te permet de jouer un tour complet de Dune Imperium Uprising avec tous les systèmes intégrés:

### 🎯 Systèmes Testés

1. **ActionGenerator** - Détermine quelles cartes et locations sont valides
2. **ActionExecutor** - Exécute les actions choisies
3. **EffectResolver** - Interprète et applique les effets JSON des cartes
4. **ContractManager** - Gère l'acquisition et la complétion des contrats

### 🎴 Cartes Disponibles

Tu commences avec 5 cartes différentes dans ta main:

1. **Fremen Scout** (Coût: 3)
   - Icône: Fremen
   - Agent: +1 eau, +2 troupes
   - Révélation: +2 persuasion

2. **Guild Banker** (Coût: 4)
   - Icône: Spacing Guild
   - Agent: +5 solari
   - Révélation: +3 persuasion

3. **Bene Gesserit Operative** (Coût: 3)
   - Icône: Bene Gesserit
   - Agent: +1 espion
   - Révélation: +1 persuasion (+2 bonus si 2+ espions placés)

4. **Emperor's Blade** (Coût: 5)
   - Icône: Emperor
   - Agent: +3 troupes, +2 solari
   - Révélation: +2 persuasion, +2 épées

5. **Spice Trader** (Coût: 2)
   - Icônes: Landsraad, Spacing Guild
   - Agent: +2 épice
   - Révélation: +1 persuasion

### 🗺️ Locations Disponibles

Le plateau contient 6 locations:

1. **Fremen Camp** (Fremen)
   - Bonus: +1 eau

2. **Carthag** (Emperor) ⚔️ COMBAT
   - Bonus: +2 troupes
   - Permet déploiement au conflit

3. **Spice Trade** (Spacing Guild)
   - Bonus: +1 épice, +2 solari

4. **Landsraad**
   - Bonus: +3 solari
   - Coût: -1 eau

5. **Sietch Tabr** (Fremen) ⚔️ COMBAT
   - Bonus: +2 eau, +1 troupe
   - Permet déploiement au conflit

6. **Truthsayer** (Bene Gesserit)
   - Bonus: +1 intrigue, +1 pioche

### 📜 Contrats Disponibles

3 contrats sont disponibles dans la rangée:

1. **Spice Production Contract** (Harvest)
   - Objectif: Récolter 5 épices au total
   - Récompenses: +3 solari, +1 PV

2. **Visit Carthag** (Location)
   - Objectif: Placer un agent à Carthag
   - Récompenses: +2 solari, +1 PV
   - Se complète automatiquement quand tu visites Carthag!

3. **Immediate Payment** (Immediate)
   - Objectif: Aucun (se complète à l'acquisition)
   - Récompenses: +5 solari

## 🎯 Flow du Test

### Phase 1: Tours d'Agent

Pour chaque agent disponible (tu en as 2):

1. **Affichage des cartes jouables**
   - Le système te montre uniquement les cartes que tu PEUX jouer
   - Avec leurs effets agent et révélation

2. **Choix de carte**
   - Tu choisis une carte dans ta main

3. **Affichage des locations valides**
   - Le système te montre où cette carte peut être placée
   - Avec les bonus de chaque location
   - Indique si c'est une zone de combat

4. **Choix de location**
   - Tu choisis où placer ton agent

5. **Déploiement de troupes** (si zone de combat)
   - Tu peux déployer 0-2 troupes de ta garnison au conflit
   - Le déploiement se fait APRÈS le recrutement (donc si ta carte recrute des troupes, tu peux les déployer immédiatement)

6. **Résolution**
   - Effets agent appliqués
   - Bonus de location appliqués
   - Contrats vérifiés et complétés si applicable
   - État du jeu affiché

### Phase 2: Tour de Révélation

Une fois que tu as joué tous tes agents (ou choisi de passer):

1. **Révélation de la main**
   - Toutes les cartes restantes sont révélées
   - Les cartes déjà jouées sont aussi comptées

2. **Calcul de la persuasion**
   - Tous les effets de révélation sont appliqués
   - Les effets conditionnels sont vérifiés
   - La persuasion totale est calculée

3. **Affichage des résultats**
   - Persuasion disponible
   - Épées pour le combat
   - Détail carte par carte

## 🔍 Ce que Tu Peux Tester

### Mécaniques Implémentées

✅ **Recrutement de troupes**
- Les troupes vont dans la garnison
- Peuvent être déployées immédiatement si zone de combat

✅ **Déploiement au combat**
- Maximum 2 troupes par tour
- Depuis la garnison vers le conflit
- APRÈS le recrutement

✅ **Effets conditionnels**
- Exemple: Bene Gesserit Operative donne +2 persuasion bonus si 2+ espions placés
- Les conditions sont vérifiées automatiquement

✅ **Contrats - 3 types**
- **Immediate**: Se complètent à l'acquisition
- **Location**: Se complètent quand tu visites la location
- **Harvest**: Se complètent quand tu récoltes assez d'épice

✅ **Coûts de location**
- Le Landsraad coûte 1 eau
- Les ressources sont déduites automatiquement

✅ **Zones de combat**
- Carthag et Sietch Tabr
- Te permettent de déployer des troupes

## 🎓 Exemple de Partie

### Tour 1
1. Joue **Emperor's Blade** à **Carthag**
   - Effets agent: +3 troupes, +2 solari
   - Bonus location: +2 troupes
   - Total: **5 troupes recrutées**
   - Déploie **2 troupes** au conflit
   - **Contrat "Visit Carthag" complété!** → +2 solari, +1 PV

### Tour 2
2. Joue **Spice Trader** à **Spice Trade**
   - Effets agent: +2 épice
   - Bonus location: +1 épice, +2 solari
   - Total: **3 épices** gagnées

### Révélation
3. Révèle ta main
   - Emperor's Blade: +2 persuasion, +2 épées
   - Spice Trader: +1 persuasion
   - 3 cartes restantes: persuasion additionnelle
   - **Total: Beaucoup de persuasion pour acheter des cartes!**

## 🐛 Debug et Vérification

Le test affiche l'état complet après chaque action:
- ✅ Ressources (eau, solari, épice)
- ✅ Points de victoire
- ✅ Troupes (garnison, conflit, réserve)
- ✅ Agents et espions
- ✅ Influence par faction
- ✅ Contrats actifs et complétés

## 📝 Notes Importantes

### Troupes et Combat
- Les troupes **recrutées** vont dans la **garnison**
- Les troupes **déployées** vont au **conflit**
- On peut déployer **max 2 troupes** par tour (depuis garnison)
- Le déploiement se fait **APRÈS** le recrutement

### Sandworms (non testé ici)
- Nécessitent le token Maker Hooks
- Vont directement au conflit (pas par la garnison)
- Bloqués si shield wall actif à une location critique
- Meurent à la fin du conflit

### Contrats
- **Location**: Se complètent automatiquement quand tu visites la location ciblée
- **Harvest**: Se complètent quand `player.total_spice_harvested >= required_spice`
- **Immediate**: Se complètent instantanément à l'acquisition

## 🚀 Pour Aller Plus Loin

Une fois ce test réussi, tu auras validé:
- ✅ Le flow complet d'un tour
- ✅ L'intégration de tous les systèmes
- ✅ La résolution des effets JSON
- ✅ Le système de contrats
- ✅ Le déploiement des troupes

Prochaines étapes possibles:
- Système de combat complet
- Résolution des conflits
- Phase Makers (gain d'épice)
- Système d'alliances (seuils d'influence)
- Gestion du deck (pioche/défausse)
- Interface utilisateur complète

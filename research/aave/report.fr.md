# Rapport de recherche Aave (AAVE)

**Recherche crypto DRLabs**  
**Date de publication / des données : 7 septembre 2026 (Asia/Shanghai, UTC+8 / PT local du lecteur)**  
**Position : neutre de recherche (pas un conseil en investissement)**

> **Synthèse en une ligne :** Aave reste le leader en taille et en marque du lending on-chain. V3 détient l'essentiel de la liquidité ; V4 (Hub & Spoke) est live sur le mainnet Ethereum depuis mars 2026 et reste dans une phase de caps conservateurs. Les fondamentaux reposent sur le cycle des taux, la part cross-chain et l'alignement DAO–Labs — pas sur une histoire de prix de jeton à court terme.

---

## 1. Présentation du projet

Aave est un protocole de liquidité décentralisé et non custodial : les utilisateurs déposent des actifs dans des pools pour gagner des intérêts, ou empruntent contre une surcollatéralisation. Les smart contracts apparient l'offre et la demande et liquident les positions risquées sans dépositaire. Le nom vient du finnois pour « ghost », un clin d'œil à une infrastructure transparente et invisible.

**Problème qu'il résout :** Le crédit traditionnel s'appuie sur des intermédiaires et la souscription. Les marchés on-chain ont longtemps fait face à une liquidité fragmentée et à des paramètres de collatéral/risque difficiles à étendre de façon modulaire. Aave a remplacé l'appariement peer-to-peer initial par un modèle de pool et a continué d'itérer sur l'isolation des risques, le déploiement multi-chaînes et un stablecoin natif (GHO).

**Positionnement :** Infrastructure « money market » DeFi de base. Sur DefiLlama, la famille Aave (surtout V3) mène depuis longtemps la TVL de lending. Les documents officiels revendiquent des originations cumulées au-dessus du seuil de $1 trillion et plus de la moitié du lending décentralisé (définition du blog officiel — à recouper avec la part de TVL tierce).

**Bref historique :** En 2017, Stani Kulechov (aujourd'hui CEO d'Aave Labs) a lancé le lending peer-to-peer sous le nom ETHLend ; le projet est ensuite passé aux pools de liquidité, a été rebrandé en Aave, et est allé live sur le mainnet Ethereum vers début 2020. En octobre 2020, LEND a migré 100:1 vers le jeton de gouvernance AAVE. Puis sont venus V2, V3 multi-chaînes, GHO, Safety Module→Umbrella, et le lancement mainnet de V4 en 2026.

---

## 2. Produit et mécanismes

### 2.1 Marchés de lending et modèle de taux

- **Offre / emprunt :** Les fournisseurs reçoivent des reçus portant intérêt. L'emprunt exige une surcollatéralisation. Les taux suivent une courbe d'utilisation (plus plate sous l'utilisation optimale, raide au-dessus). Les taux d'offre sont l'intérêt des emprunteurs moins les frais de protocole, partagés entre les fournisseurs.
- **Architecture V3 :** La liquidité est isolée par marché (p. ex. Ethereum Core / Prime). Les pools sur une même chaîne ne réutilisent pas les fonds entre marchés — meilleure isolation des risques, mais les nouveaux marchés doivent bootstraper leur liquidité seuls.
- **eMode (Efficiency Mode) :** Augmente le pouvoir d'emprunt pour les actifs fortement corrélés (paires stables, ETH/LST) et améliore l'efficacité du capital.
- **aToken :** Les reçus d'offre V3 sont surtout des aTokens rebasing ; les soldes croissent avec les intérêts et peuvent être composés ailleurs dans le DeFi.

### 2.2 Liquidations

Les positions dont le Health Factor est inférieur à 1 peuvent être liquidées. Les liquidateurs remboursent une partie de la dette et reçoivent du collatéral plus un bonus. Le protocole dépend des prix d'oracles ; la congestion des liquidations, la bad debt et le lag des oracles sont les risques de queue centraux en stress.

### 2.3 Aave V4 (statut selon les sources officielles)

**Lancement :** Blog officiel daté du **30 mars 2026** pour V4 sur le mainnet Ethereum.

**Changement central — Hub & Spoke :**

| Composant | Rôle |
|------|------|
| Liquidity Hub | Hub on-chain unifié de liquidité et de comptabilité ; fixe les limites crédit/débit pour les Spokes |
| Spoke | Point d'entrée utilisateur ; peut fixer son propre collatéral, ses paramètres de risque et ses règles de liquidation |
| Risk Premium | Prime d'emprunt supplémentaire au-dessus du taux d'utilisation, selon la qualité du collatéral |
| Liquidation engine | Un Target Health Factor remplace un close factor fixe ; bonuses variables ; règles de dust |

Note officielle : V4 a été lancée avec plusieurs Liquidity Hubs (Core / Prime / Plus et narratifs similaires). **Les caps d'offre et d'emprunt étaient délibérément conservateurs**, à relever par la DAO après observation en production. Côté UI, **Aave Pro** a été lancé pour V4. Sur la sécurité, les documents officiels citent environ 345 jours d'audit cumulés, plusieurs cabinets et un contest public Sherlock (voir le repo d'audit).

**Comptabilité :** Les notes communautaires et techniques décrivent généralement V4 comme allant vers une comptabilité de parts ERC-4626 (versus les aTokens rebasing de V3). L'UX produit suit les docs officielles et l'UI.

**Relation avec V3 :** Les documents officiels et de gouvernance sont explicites : **V3 continuera de fonctionner aussi longtemps que nécessaire**. V4 est la prochaine architecture de liquidité unifiée ; la migration et le glissement de parts sont un processus de moyen terme.

### 2.4 Déploiement multi-chaînes

Aave est live sur Ethereum plus plusieurs L2/sidechains et L1 plus récentes (mix de chaînes DefiLlama ci-dessous). La trajectoire officielle de V4 : la prouver sur le mainnet Ethereum, puis laisser la DAO ajouter des Spokes, relever les caps, et pousser d'autres réseaux.

### 2.5 GHO et produits d'épargne

**GHO** est le stablecoin natif d'Aave, surcollatéralisé et peggé sur l'USD : les utilisateurs mintent (empruntent) du GHO contre du collatéral et le brûlent au remboursement. L'intérêt d'emprunt va surtout à la trésorerie de la DAO. Les données stablecoins DefiLlama autour du **7 septembre 2026** placent la capitalisation circulante de GHO à environ **$698 million**, le prix à environ **$0.999**, proche de $1.

![Offre circulante de GHO](charts/05_gho_circulating.png)

**Lecture :** GHO a un flottant proche de $700 million et un peg stable jusqu'ici. Versus USDT/USDC et les stables yield-bearing plus récents, il reste de taille moyenne. La croissance dépend de la demande d'emprunt, de la compétitivité de sGHO et de la liquidité cross-chain.

**sGHO / Aave Savings Rate (ASR) :** La gouvernance déplace le volet épargne vers un vault ERC-4626 (sGHO). Dans une proposition GHO Stewards d'août 2026, l'ASR a été discuté autour de **4.50%** (avec certains taux d'emprunt GHO relevés en parallèle) pour matcher les taux d'épargne concurrents et la rétention. L'exécution suit les paramètres on-chain et l'UI.

**GSM et autres outils de stabilité :** Utilisés pour la défense du peg et les buffers de liquidité. Les depegs, le basis cross-chain et le décalage de taux restent des risques au niveau produit.

---

## 3. Économie du jeton (AAVE)

| Élément | Données (7 septembre 2026) | Source |
|------|----------------------|------|
| Offre max / totale | 16,000,000 AAVE | Params publiques du jeton / Etherscan |
| Circulante (implicite) | ~15.54M (~97.1%) | DefiLlama mcap ÷ spot |
| Prix | ~$134.55 | DefiLlama coins API |
| Mcap circulante | ~$2.09B | DefiLlama protocol mcap |
| FDV (à 16M) | ~$2.15B | Spot × max supply |
| Variation 30 jours | ~+49% (print CoinGecko draft ; non revérifié après throttle API) | CoinGecko (citation historique) |
| Variation 1 an | ~−55% (idem) | CoinGecko (citation historique) |

![Capitalisation et FDV d'AAVE](charts/04_aave_mcap_fdv.png)

**Lecture :** La circulation est proche du fully diluted ; l'écart mcap / FDV est petit (~3%). Le récit habituel d'« unlock overhang » est faible. L'élasticité du jeton vient davantage de la prime de gouvernance, des revenus DAO attendus et de l'appétit pour le risque que d'un squeeze d'offre.

**Usages :**

1. **Gouvernance :** La Aave DAO (forum → TEMP CHECK / ARFC → AIP) vote sur les paramètres, listings, frais et dépenses de trésorerie.  
2. **Sécurité et incentives :** Le Safety Module historique utilisait **stkAAVE** et des actifs similaires pour le risque de slashing plus des incentives. Il a été upgradé vers **Umbrella** (aTokens / actifs liés couvrant la bad debt, avec slashing automatisé). stkAAVE peut conserver une certaine utilité et des incentives dans la transition, mais le help center officiel indique qu'il n'est plus l'actif de couverture de bad debt privilégié.  
3. **Narratif de capture de valeur :** Le **cadre « Aave Will Win »** adopté vers avril 2026 oriente les revenus des produits de marque Aave vers la trésorerie de la DAO, renforçant « détenir AAVE ≈ droits économiques sur le protocole et la marque ». Les chemins des revenus de couche applicative (Aave Pro / App et similaires) vers la trésorerie suivent l'exécution de la gouvernance.

**Unlocks :** Offre fixe de 16 million, presque entièrement circulante ; le reliquat surtout dans des contrats de réserve/incentives de l'écosystème. **Aucun cliff unlock matériel identifié.** La pression d'offre de court terme vient davantage des émissions d'incentives et des ops de trésorerie que d'un vesting classique.

---

## 4. Marché et fondamentaux

> Note : les fournisseurs de données définissent « TVL » différemment. La TVL protocole DefiLlama est en général proche du « net locked » (offre moins emprunts et ajustements similaires). Aavescan affiche aussi l'offre, les emprunts et la TVL nette. Les graphiques ici utilisent **l'API auditable de DefiLlama**. Aavescan est rendu côté front-end et n'a pas pu être scrapé de façon stable cette fois, donc il n'est pas utilisé pour des graphiques autonomes.

### 4.1 Échelle

| Indicateur | Valeur | Date / source |
|------|------|-----------|
| TVL protocole Aave (parent DefiLlama) | ~**$18.40B** | 2026-09-07, [DefiLlama API](https://defillama.com/protocol/aave) |
| Offre (est.) / emprunts / TVL nette | ~**$31.2B / $12.85B / $18.4B** | DefiLlama: supply ≈ net TVL + Borrowed |
| TVL Aave V3 | ~**$17.64B** | DefiLlama protocols |
| TVL Aave V4 | ~**$0.384B** | Idem (caps conservateurs après lancement ; encore petit) |
| TVL Aave V2 | ~**$0.112B** | Idem (legacy) |

![TVL Aave par version](charts/01_aave_tvl_versions.png)

**Lecture :** Sur ~$18.4B de TVL nette parent, V3 représente environ 96%. V4 est autour de $384M — caps conservateurs plus migration précoce. Le récit d'architecture est live ; la liquidité n'a pas encore basculé.

![Offre, emprunts et TVL nette](charts/02_aave_supply_borrow_net.png)

**Lecture :** Des emprunts ~$12.9B et une TVL nette ~$18.4B placent l'utilisation dans une plage génératrice de frais. Le côté offre (net + borrowed) ~$31.2B montre l'échelle de bilan du protocole.

![Tendance de TVL nette Aave](charts/07_aave_tvl_trend.png)

**Lecture :** La TVL nette sur l'année écoulée a reculé depuis un pic de fin 2025, a baissé par paliers mi-2026, puis s'est reprise en août–septembre autour de $18.4B — **toujours le leader en taille, clairement cyclique**, étroitement liée aux actifs risqués et aux flux de stablecoins.

### 4.2 Revenus et frais (DefiLlama Fees)

| Indicateur | Approx. | Source |
|------|------|------|
| Frais protocole, 30j | ~**$32.8M** | DefiLlama fees/aave, 2026-09-07 |
| Revenus protocole, 30j | ~**$4.57M** | Idem (dailyRevenue) |
| Frais / revenus, all-time | ~**$2.28B / $309M** | Idem |

![Frais 30 jours vs revenus protocole](charts/03_aave_fees_vs_revenue_30d.png)

**Lecture :** Sur les 30 derniers jours, ~$32.8M de frais et ~$4.57M de revenus protocole, soit un taux de capture d'environ **13.9%** (le reste surtout aux fournisseurs). L'échelle des frais mène le lending, mais la capture au niveau du jeton dépend encore du reserve factor, des intérêts GHO et de l'exécution d'« Aave Will Win » — pas du seul titre des frais.

**Note :** Le dernier jour d'une série de revenus quotidiens peut être incomplet ; préférer les agrégats 7/30 jours.

### 4.3 Parts concurrentielles (DefiLlama, 7 septembre 2026)

| Protocole | TVL approx. |
|------|----------|
| Aave V3 | $17.6B |
| Morpho Blue | $9.8B |
| SparkLend | $4.5B |
| Compound V3 | $1.4B |
| Fluid Lending | $0.75B |
| Aave V4 | $0.38B |
| Euler V2 | $0.35B |

![TVL des concurrents de lending](charts/06_lending_competitors_tvl.png)

**Lecture :** Aave V3 mène encore largement. Morpho Blue à ~$9.8B est le suiveur le plus proche, en concurrence sur le yield et l'efficacité du capital. La part de Compound V3 s'est réduite. Spark se situe dans l'orbite Sky et est à la fois concurrent et complément de la liquidité Aave.

### 4.4 Mix de chaînes (DefiLlama currentChainTvls, hors borrowed/staking/pool2)

Environ **84.8%** de la TVL nette est sur **Ethereum** (~$15.6B) ; puis Base, Plasma, Arbitrum, Monad, Avalanche, BSC, Polygon et d'autres. Emprunts totaux ~**$12.85B**. L'expansion multi-chaînes est en cours, mais le risque et les revenus restent fortement concentrés sur Ethereum.

---

## 5. Gouvernance, équipe / historique de fondation

- **Aave Labs :** Entité produit et R&D dirigée par le fondateur **Stani Kulechov**, couvrant l'itération du protocole, les front-ends et le travail de marque.  
- **Aave DAO :** Les détenteurs d'AAVE et les délégués gèrent les paramètres, listings, trésorerie et upgrades majeurs via [governance.aave.com](https://governance.aave.com) et la gouvernance on-chain.  
- **Pile de prestataires :** Historiquement, BGD Labs, les risk providers, ACI et d'autres ont contribué au développement et aux ops de gouvernance. Autour de 2026, les frictions publiques sur le funding et le pouvoir (certains prestataires ont réduit ou arrêté de contribuer) sont un point de suivi de gouvernance.  
- **Cadre « Aave Will Win » (~adopté avril 2026) :** Oriente les revenus des produits de marque Aave vers la DAO ; donne à Labs un budget d'environ un an ; s'engage sur une proposition suivante pour que la marque/IP siège dans un véhicule de protection communautaire (de type fondation). CoinDesk et d'autres l'ont qualifié de jalon mettant fin au combat « qui reçoit les revenus », tout en soulevant des questions de centralisation et de responsabilité.  
- **Ops de risque et de paramètres :** Risk Steward, GHO Stewards et rôles similaires peuvent ajuster les taux dans un mandat — réponse plus rapide, risque plus délégué.

L'information publique ne montre pas une fondation traditionnelle unique remplaçant pleinement Labs. La structure juridique finale de tout véhicule fondation/IP suivra des AIP ultérieurs. **Cette note signale : cadre adopté, détails encore à suivre.**

---

## 6. Concurrence et fossé

**Fossé (relativement solide) :**

1. **Effets de réseau de liquidité et confiance de marque :** Des pools profonds réduisent le slippage de taille importante et le choc de taux ; les institutions et trésoreries préfèrent des venues éprouvées.  
2. **Multi-chaînes et matrice produit :** V3 multi-marchés + GHO + Umbrella + Horizon (lending RWA, listé séparément sur DefiLlama) + Spokes modulaires V4.  
3. **Expérience de liquidation et de risque :** Plusieurs cycles de stress crypto ; les documents officiels insistent sur l'historique de tests en production.  
4. **Gouvernance et largeur d'intégration :** Coût de câblage par défaut pour wallets, agrégateurs et produits structurés.

**Défis :**

- **Morpho et pairs :** Une meilleure efficacité du capital et un yield curaté peuvent siphonner les dépôts marginaux.  
- **Friction de migration V4 :** Split dual-version ; les caps conservateurs gardent la part de V4 petite à court terme.  
- **Tension DAO–Labs :** Affecte la prévisibilité des contributeurs externes et la cadence d'upgrades.  
- **Guerres de stablecoins :** sUSDS, Ethena et d'autres produits d'épargne compriment la croissance de GHO/sGHO.

---

## 7. Risques (expositions uniquement, pas de détail d'exploit)

| Catégorie | Exposition |
|------|--------|
| Smart contracts | Complexité V3/V4/Umbrella/GHO ; la surface d'attaque s'élargit au lancement d'une nouvelle architecture ; dépend des audits continus et des méthodes formelles |
| Oracles | Un lag ou une manipulation peut provoquer de mauvaises liquidations ou de la bad debt ; le multi-chaînes multiplie la dépendance aux oracles |
| Gouvernance | Propositions malveillantes ou précipitées, erreurs de paramètres, concentration des délégués ; bords de permissions Steward |
| Régulation | Le lending et les stables font face à une incertitude titres/stablecoins selon la juridiction ; front-end et domicile de l'entité Labs |
| GHO / stables | Depeg, liquidité cross-chain mince, taux d'épargne non soutenable, épuisement du GSM |
| Liquidité et cygnes noirs | Liquidations en cascade, depegs de stables, décotes LST, risque de bridge, contagion de protocoles liés |
| Ops et politique | Sorties de prestataires, litiges marque/IP, incentives trop minces vs couverture cible |

Umbrella aligne les actifs slashés avec les actifs de bad debt potentiels et ajoute un buffer de déficit. Le langage du help center officiel indique que le Safety Module historique est longtemps resté sans slash effectif — **ce n'est pas une promesse de zéro à l'avenir**.

---

## 8. Catalyseurs et métriques de suivi

**Catalyseurs potentiels :**

- Relevés de caps V4, nouveaux Spokes (institution/RWA/type eMode) et davantage de déploiements de chaînes  
- Breakout du flottant GHO et des dépôts sGHO ; efficacité de la politique ASR et des taux d'emprunt  
- Exécution du routage des revenus DAO et toute proposition « buyback / incentive / dividend » (à évaluer séparément si elles apparaissent)  
- Atterrissage des détails de la fondation de marque, refroidissement du narratif de split de gouvernance  
- Un cycle de hausse des taux relevant les frais et les revenus

**Métriques hebdomadaires suggérées :**

1. DefiLlama : TVL parent Aave / V3 / V4 et mix de chaînes  
2. Frais et revenus (7d/30d) plus utilisation  
3. Mcap circulante GHO, écart de peg, TVL sGHO, ASR  
4. Stake Umbrella par actif versus couverture cible  
5. Parts relatives de TVL Morpho / Spark / Compound  
6. Forum de gouvernance : paramètres V4, Risk Steward, budgets prestataires et propositions de fondation  
7. Offre circulante AAVE et avoirs de trésorerie (on-chain)

---

## 9. Conclusion et liste de suivi

**Conclusion :** En 2026, Aave reste le « protocole systémique » du lending DeFi : TVL nette autour de $18B, échelle des frais en tête, V4 live mais ne portant pas encore la liquidité cœur. Côté jeton, l'offre est presque entièrement circulante ; la valeur est davantage liée aux droits sur les revenus DAO et à une prime de gouvernance. Le cadre de gouvernance 2026 a renforcé « les revenus vers la DAO », mais la qualité d'exécution et la stabilité de la pile de contributeurs restent à prouver. Pour les lecteurs orientés recherche, Aave convient comme **holding de référence du secteur lending et suivi d'infrastructure**. Les décisions de trading nécessitent une vue séparée des taux macro, de l'appétit pour le risque et des fuites concurrentielles.

**Liste de suivi :**

- [ ] Si la TVL nette V4 continue de sortir par le haut (pente de migration versus V3)  
- [ ] Si les revenus protocole 30 jours se reprennent avec l'utilisation (versus les pics 2025)  
- [ ] Si GHO reste près de $1 avec des flux nets côté épargne  
- [ ] Si la couverture Umbrella atteint les cibles de gouvernance sans déficits anormaux  
- [ ] Si les relations DAO–Labs et les contributeurs externes se restabilisent  
- [ ] Si Morpho et d'autres continuent de manger la croissance marginale

---

## 10. Synthèse objective et score d'achat

**Date d'arrêté : 7 septembre 2026 (Asia/Shanghai, UTC+8)**

Cette section est un score structuré selon le cadre de recherche interne de DRLabs, utilisé pour comparer l'attractivité relative au sein d'un même secteur. **Ce n'est pas une recommandation d'achat, de conservation ou de vente pour aucun lecteur** (voir l'avertissement en fin de document).

### 10.1 Échelle de score (1–10)

| Score | Signification (définition recherche) |
|------|------------------|
| 1 | Fondamentaux gravement altérés ou un défaut structurel difficile à accepter ; le cadre penche vers l'évitement |
| 2–3 | Une incertitude majeure domine ; les négatifs l'emportent clairement sur le fossé et la logique de cash-flow |
| 4–5 | Suivable mais attrait limité ; seulement pour un appétit au risque très élevé ou une taille event-driven |
| 6 | Fondamentaux acceptables avec des points de débat clairs ; à discuter comme un suivi ou un petit satellite |
| 7 | Position sectorielle et fondamentaux plutôt positifs, encore contraints par la concurrence, la gouvernance ou la valorisation |
| 8 | Attrait relatif plus fort ; plusieurs facteurs scorent haut ; le reliquat est surtout exécution et macro |
| 9 | La chaîne de preuves est très solide, les négatifs limités ; le cadre penche vers une discussion de surpondération à haute conviction |
| 10 | Cas « must own » extrêmement rare ; fossé, croissance, capture et valorisation presque sans trou majeur |

### 10.2 Facteurs et pondérations

| Facteur | Poids | Score (1–10) | Base brève (2026-09-07) |
|------|------|-------------|------------------------|
| Fondamentaux / fossé | 25% | **8.0** | TVL nette ~$18.4B, marque et intégrations en tête ; expérience profonde de liquidation et multi-chaînes |
| Croissance et parts | 20% | **6.5** | Toujours #1, mais Morpho Blue ~$9.8B est proche ; part V4 encore petite |
| Capture de valeur du jeton | 20% | **6.5** | « Aave Will Win » renforce les revenus DAO ; revenus/frais 30j ~13.9% ; rythme d'exécution non prouvé |
| Risque (plus élevé = plus contenu) | 20% | **5.5** | Complexité contrats et cross-chain, friction de gouvernance, régulation et concurrence des stablecoins sont de vraies contraintes |
| Valorisation et timing | 15% | **6.5** | Quasi pleinement circulant, petit écart mcap/FDV ; fort drawdown 1 an puis un rebond — une marge de timing existe, pas une preuve de sous-valorisation extrême |

**Score pondéré :**  
`0.25×8.0 + 0.20×6.5 + 0.20×6.5 + 0.20×5.5 + 0.15×6.5 = 6.675` → **score d'achat final : 6.7 / 10**

### 10.3 Pourquoi 6.7, pas plus haut ni plus bas

- **Pas 8+ :** Morpho et ses pairs peuvent contester la part marginale ; la migration de liquidité V4 est lente ; les relations DAO–Labs et prestataires restent bruyantes ; la capture de revenus protocole versus les frais est limitée, et l'exécution de gouvernance est path-dependent.  
- **Pas sous 5 :** L'échelle, le volume de frais et la confiance de marque mènent encore Compound et d'autres pairs legacy ; l'offre est propre ; GHO plus revenus-vers-DAO est une option de moyen terme ; la TVL s'est réparée depuis le creux de mi-année.  
- **Discutable :** Les lecteurs qui surpondèrent « jeton = cash-flow » et veulent une certitude de capture plus élevée peuvent imprimer 5–6 ; ceux qui surpondèrent la rareté d'infra systémique et l'adoption institutionnelle peuvent imprimer 7–7.5. Cette note prend le centre pondéré **6.7** — « un suivi de référence sectorielle à biais positif, pas une surpondération inconditionnelle ».

---

## 11. Avertissement

Ce rapport est compilé par DRLabs à partir d'informations publiques et est **destiné uniquement à l'information générale et à la discussion de recherche**. Il n'est pas, et ne doit pas être lu comme, un conseil en investissement, une recommandation, une offre, une sollicitation ou une quelconque forme d'engagement portant sur des titres, actifs numériques ou autres produits financiers.

Les crypto-actifs et protocoles DeFi sont hautement volatils et incertains. Les prix et paramètres de protocole peuvent bouger violemment en peu de temps. Les investisseurs peuvent perdre une partie ou la totalité de leur capital. Les lecteurs doivent juger de façon indépendante selon leurs finances, leur tolérance au risque et leurs objectifs, et consulter des conseillers qualifiés si besoin. **Toute décision fondée sur ce rapport, et ses conséquences, appartient au lecteur.**

Le « score d'achat » et les scores de facteurs sont des **quantifications subjectives** selon un cadre énoncé et des contraintes de données publiques, utilisés pour la comparaison interne et la discussion. **Ils ne constituent pas une recommandation d'achat ou de vente sur un actif numérique** et ne garantissent pas la performance de marché future.

Les données, graphiques et sources tierces cités (y compris, sans s'y limiter, DefiLlama, docs officielles et forums de gouvernance) peuvent différer en définition, être retardés, incomplets ou erronés. DRLabs et l'auteur n'offrent aucune garantie expresse ou implicite d'exactitude, d'exhaustivité, d'actualité ou d'adéquation, et ne sont pas responsables de toute perte directe ou indirecte liée à l'usage ou à la confiance accordée à ce rapport. Les marchés et l'état des protocoles changent vite ; revérifier les sources originales et l'état on-chain avant de citer.

---

## 12. Sources

1. [Aave V4 Overview (docs officielles)](https://aave.com/docs/aave-v4)  
2. [Understanding Aave V4’s Architecture (blog officiel)](https://aave.com/blog/understanding-aave-v4s-architecture)  
3. [Aave V4 is Live on Ethereum (blog officiel, 2026-03-30)](https://aave.com/blog/aave-v4-live-ethereum)  
4. [Site Aave](https://aave.com)  
5. [DefiLlama — Aave](https://defillama.com/protocol/aave)  
6. [DefiLlama — Aave V3](https://defillama.com/protocol/aave-v3)  
7. [DefiLlama — stablecoin GHO](https://defillama.com/stablecoin/gho)  
8. [Aavescan Protocol Totals](https://aavescan.com/protocol/totals) (non utilisé pour les graphiques cette fois)  
9. [CoinGecko — Aave](https://www.coingecko.com/en/coins/aave) (certains chiffres de rendement sont des citations historiques ; API throttlée le jour des graphiques)  
10. [Aide Umbrella](https://aave.com/help/umbrella/umbrella)  
11. [BGD : Safety Module — Umbrella (forum de gouvernance)](https://governance.aave.com/t/bgd-aave-safety-module-umbrella/18366)  
12. [GHO Stewards août 2026, mise à jour des taux et de l'ASR](https://governance.aave.com/t/gho-stewards-august-2026-gho-borrow-rate-and-aave-savings-rate-update/25534)  
13. [Proposition d'outil de migration stkGHO → sGHO](https://governance.aave.com/t/direct-to-aip-stkgho-sgho-migration-tool/25250)  
14. [[ARFC] Aave Will Win Framework](https://governance.aave.com/t/arfc-aave-will-win-framework/24352)  
15. [CoinDesk : vote Aave Will Win](https://www.coindesk.com/tech/2026/04/13/aave-passes-landmark-vote-ending-months-long-fight-over-who-controls-protocol-revenue)  
16. [DL News : friction DAO vs Labs](https://www.dlnews.com/articles/defi/aave-dao-members-accuse-stani-kulechov-of-power-grab/)  
17. [Aperçu GitHub Aave V4](https://github.com/aave/aave-v4/blob/main/docs/overview.md)  
18. [Wikipedia — Aave (contexte)](https://en.wikipedia.org/wiki/Aave)  
19. [Etherscan — jeton AAVE](https://etherscan.io/token/0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDAE9)  
20. [Forum de gouvernance Aave](https://governance.aave.com)  
21. API DefiLlama : `/protocol/aave`, `/protocols`, `/summary/fees/aave`, `coins.llama.fi`, `stablecoins.llama.fi` (extraction graphiques 2026-09-07)

---

*Version du rapport : 7 septembre 2026 (Asia/Shanghai). Dossier des graphiques : `charts/`. Ne pas utiliser ce texte pour une activité illégale ou une manipulation de marché.*

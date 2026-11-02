# Compte rendu des corrections de sources et de formulation

Corrections du 2 novembre 2026 dans l’introduction générale et le chapitre 1. Ce document est séparé du mémoire. Il reproduit les passages exacts avant et après modification.

17 lignes de texte modifiées. Deux notices bibliographiques ajoutées. Les chapitres 2, 3 et 4, la conclusion, les résultats et les formules ne sont pas modifiés.

## Introduction générale — ligne 326

[Ouvrir le passage](</Users/joelkouraogo/Desktop/Master 2 IBAM ISIE Soutenance 2026/Rapport/Rapport Joel KOURAOGO.tex:326>)

Avant :

```latex
L’augmentation constante du volume de documents numériques produits par les organisations, les entreprises et les établissements universitaires rend leur gestion et leur exploitation de plus en plus complexes. Les utilisateurs doivent souvent parcourir un nombre important de fichiers avant de trouver l’information recherchée. Les méthodes traditionnelles de recherche fondées sur les mots-clés restent simples et rapides, mais reposent principalement sur la correspondance entre les termes de la requête et ceux présents dans les documents. Elles peuvent ainsi rencontrer des difficultés lorsque les documents et les requêtes utilisent des synonymes, des formulations différentes ou un vocabulaire spécialisé.
```

Après :

```latex
L’augmentation constante du volume de documents numériques produits par les organisations, les entreprises et les établissements universitaires rend leur gestion et leur exploitation de plus en plus complexes. Les utilisateurs doivent souvent parcourir un nombre important de fichiers avant de trouver l’information recherchée. Les méthodes traditionnelles de recherche fondées sur les mots-clés reposent principalement sur la correspondance entre les termes de la requête et ceux présents dans les documents. Elles peuvent ainsi rencontrer des difficultés lorsque les documents et les requêtes utilisent des synonymes, des formulations différentes ou un vocabulaire spécialisé \cite{karpukhin_dpr_2020}.
```

## Introduction générale — ligne 327

[Ouvrir le passage](</Users/joelkouraogo/Desktop/Master 2 IBAM ISIE Soutenance 2026/Rapport/Rapport Joel KOURAOGO.tex:327>)

Avant :

```latex
Pour répondre à ces limites, l’indexation sémantique propose de représenter les documents en tenant compte de leur contenu et de leur signification. Cette approche s’appuie notamment sur le traitement automatique du langage naturel et sur les modèles d’embeddings. Ces modèles permettent de transformer les textes en représentations vectorielles, c’est-à-dire en ensembles de valeurs numériques représentant certaines caractéristiques sémantiques des textes. Il devient alors possible de comparer les documents et les requêtes selon leur proximité dans un espace vectoriel, y compris lorsque les termes employés sont différents mais que les contenus présentent une proximité de sens.
```

Après :

```latex
Pour répondre à ces limites, l’indexation sémantique propose de représenter les documents en tenant compte de leur contenu et de leur signification. Cette approche s’appuie notamment sur le traitement automatique du langage naturel et sur les modèles d’embeddings. Ces modèles permettent de transformer les textes en représentations vectorielles, c’est-à-dire en ensembles de valeurs numériques représentant certaines caractéristiques sémantiques des textes. Il devient alors possible de comparer les documents et les requêtes selon leur proximité dans un espace vectoriel, y compris lorsque les termes employés sont différents mais que les contenus présentent une proximité de sens \cite{reimers_sbert_2019}.
```

## Introduction générale — ligne 328

[Ouvrir le passage](</Users/joelkouraogo/Desktop/Master 2 IBAM ISIE Soutenance 2026/Rapport/Rapport Joel KOURAOGO.tex:328>)

Avant :

```latex
La mise en œuvre d’une telle approche nécessite un mécanisme permettant de stocker les représentations vectorielles et d’effectuer efficacement des recherches par similarité. Les bases de données vectorielles répondent à ce besoin en permettant de stocker les vecteurs associés aux textes et à leurs métadonnées, puis de rechercher les représentations les plus proches d’une requête donnée. Elles constituent ainsi un composant important des systèmes d’indexation et de recherche sémantiques.
```

Après :

```latex
La mise en œuvre d’une telle approche nécessite un mécanisme permettant de stocker les représentations vectorielles et d’effectuer efficacement des recherches par similarité. Les bases de données vectorielles répondent à ce besoin en permettant de stocker les vecteurs associés aux textes et à leurs métadonnées, puis de rechercher les représentations les plus proches d’une requête donnée \cite{pan_survey_2024}. Elles constituent ainsi un composant important des systèmes d’indexation et de recherche sémantiques.
```

## Introduction générale — ligne 329

[Ouvrir le passage](</Users/joelkouraogo/Desktop/Master 2 IBAM ISIE Soutenance 2026/Rapport/Rapport Joel KOURAOGO.tex:329>)

Avant :

```latex
Cependant, la mise en place d’une approche d’indexation sémantique ne repose pas uniquement sur le choix d’une base de données vectorielle. Elle dépend également de plusieurs paramètres, notamment le modèle d’embeddings utilisé, la méthode de prétraitement et de segmentation des documents, la mesure de similarité, l’algorithme d’indexation ainsi que les méthodes retenues pour évaluer les résultats. Ces choix peuvent avoir une influence sur la pertinence des documents retrouvés et sur les performances du système.
```

Après :

```latex
Cependant, la mise en place d’une approche d’indexation sémantique ne repose pas uniquement sur le choix d’une base de données vectorielle. Elle dépend également de plusieurs paramètres, notamment le modèle d’embeddings utilisé, la méthode de prétraitement et de segmentation des documents, la mesure de similarité, l’algorithme d’indexation ainsi que les méthodes retenues pour évaluer les résultats. Ces choix peuvent avoir une influence sur la pertinence des documents retrouvés et sur les performances du système \cite{thakur_beir_2021,qu_is_2024,pan_survey_2024}.
```

## Chapitre 1 — section 1.3 — ligne 394

[Ouvrir le passage](</Users/joelkouraogo/Desktop/Master 2 IBAM ISIE Soutenance 2026/Rapport/Rapport Joel KOURAOGO.tex:394>)

Avant :

```latex
    \item \textbf{La recherche fondée sur les mots-clés}, qui compare les termes saisis par l’utilisateur à ceux qui figurent dans les documents indexés. Le système identifie les documents contenant ces mots, puis les classe selon une méthode de pertinence. Simple et largement répandue dans les moteurs de recherche comme dans les systèmes documentaires, cette approche est efficace lorsque la requête emploie des termes identiques ou proches de ceux présents dans les documents. Elle reste néanmoins sensible aux variations de formulation. Une requête contenant le terme « véhicule » peut, par exemple, ne pas retrouver un document qui n’emploie que le terme « automobile ». Les relations entre les mots et le contexte global de la requête sont également difficiles à interpréter par cette méthode.
```

Après :

```latex
    \item \textbf{La recherche fondée sur les mots-clés}, qui compare les termes saisis par l’utilisateur à ceux qui figurent dans les documents indexés. Le système identifie les documents contenant ces mots, puis les classe selon une méthode de pertinence. Simple et largement répandue dans les moteurs de recherche comme dans les systèmes documentaires, cette approche est efficace lorsque la requête emploie des termes identiques ou proches de ceux présents dans les documents. Dans sa forme lexicale simple, sans expansion de requête, elle reste sensible aux variations de formulation \cite{karpukhin_dpr_2020}. Une requête contenant le terme « véhicule » peut, par exemple, ne pas retrouver un document qui n’emploie que le terme « automobile ». Les relations entre les mots et le contexte global de la requête sont également difficiles à interpréter par cette méthode.
```

## Chapitre 1 — section 1.3 — ligne 396

[Ouvrir le passage](</Users/joelkouraogo/Desktop/Master 2 IBAM ISIE Soutenance 2026/Rapport/Rapport Joel KOURAOGO.tex:396>)

Avant :

```latex
    \item \textbf{L’index inversé}, une structure de données couramment employée en recherche documentaire. Chaque terme y est associé à la liste des documents dans lesquels il apparaît. Cette organisation évite de parcourir l’ensemble du corpus à chaque requête et accélère donc la recherche. Ainsi, le mot « vecteur » peut être relié aux documents 1, 3 et 7. Lorsqu’un utilisateur recherche ce terme, le système consulte directement cette liste. Malgré son efficacité, l’index inversé repose essentiellement sur la présence des termes : il ne prend pas nécessairement en compte leur signification ni les relations sémantiques entre des expressions différentes.
```

Après :

```latex
    \item \textbf{L’index inversé}, une structure de données couramment employée en recherche documentaire. Chaque terme y est associé à la liste des documents dans lesquels il apparaît \cite[chap.~1]{manning_ir_2008}. Cette organisation évite de parcourir l’ensemble du corpus à chaque requête et accélère donc la recherche. Ainsi, le mot « vecteur » peut être relié aux documents 1, 3 et 7. Lorsqu’un utilisateur recherche ce terme, le système consulte directement cette liste. L’index inversé est une structure de données : la prise en compte de synonymes ou de relations sémantiques dépend des traitements et du modèle de recherche qui l’utilisent, et non de cette structure seule \cite[chap.~1 et~9]{manning_ir_2008}.
```

## Chapitre 1 — section 1.3 — ligne 398

[Ouvrir le passage](</Users/joelkouraogo/Desktop/Master 2 IBAM ISIE Soutenance 2026/Rapport/Rapport Joel KOURAOGO.tex:398>)

Avant :

```latex
    \item \textbf{La pondération TF-IDF}, qui attribue un poids aux termes présents dans les documents en comparant leur fréquence dans un document à leur fréquence dans l’ensemble du corpus. Un terme fréquent dans un document mais rare dans le corpus reçoit généralement un poids plus élevé. Pour un terme $t$ et un document $d$, la pondération peut s’écrire :
```

Après :

```latex
    \item \textbf{La pondération TF-IDF}, qui attribue un poids aux termes présents dans les documents en comparant leur fréquence dans un document à leur fréquence dans l’ensemble du corpus. Un terme fréquent dans un document mais rare dans le corpus reçoit généralement un poids plus élevé. Pour un terme $t$ présent dans le corpus et un document $d$, une forme classique de cette pondération s’écrit \cite[sect.~6.2]{manning_ir_2008} :
```

## Chapitre 1 — section 1.3 — ligne 403

[Ouvrir le passage](</Users/joelkouraogo/Desktop/Master 2 IBAM ISIE Soutenance 2026/Rapport/Rapport Joel KOURAOGO.tex:403>)

Avant :

```latex
    où $\operatorname{tf}(t,d)$ est la fréquence de $t$ dans $d$, $\operatorname{df}(t)$ le nombre de documents contenant $t$ et $N$ le nombre total de documents du corpus. Ce modèle améliore le classement des documents par rapport à une recherche fondée uniquement sur la présence ou l’absence des mots. Son fonctionnement demeure toutefois lexical : deux textes exprimant la même idée avec des termes différents peuvent être considérés comme éloignés.
```

Après :

```latex
    où $\operatorname{tf}(t,d)$ est la fréquence de $t$ dans $d$, $\operatorname{df}(t)$ le nombre de documents contenant $t$ et $N$ le nombre total de documents du corpus. Cette pondération distingue l’importance des termes au-delà de leur seule présence ou absence ; elle ne garantit pas un meilleur classement pour toutes les requêtes et tous les corpus. Son fonctionnement demeure toutefois lexical : deux textes exprimant la même idée avec des termes différents peuvent être considérés comme éloignés.
```

## Chapitre 1 — section 1.3 — ligne 405

[Ouvrir le passage](</Users/joelkouraogo/Desktop/Master 2 IBAM ISIE Soutenance 2026/Rapport/Rapport Joel KOURAOGO.tex:405>)

Avant :

```latex
    \item \textbf{Le modèle de classement BM25}, utilisé dans les systèmes de recherche d’information, prend notamment en compte la fréquence des termes, la longueur des documents et la rareté des mots dans le corpus. Le modèle BM25 obtient souvent de bons résultats en recherche par mots-clés, mais  il ne constitue pas pour autant un mécanisme complet de compréhension sémantique, puisqu’il repose principalement sur les correspondances entre les termes de la requête et ceux des documents.
```

Après :

```latex
    \item \textbf{Le modèle de classement BM25}, utilisé dans les systèmes de recherche d’information, combine notamment une pondération liée à la rareté des termes, un effet de saturation de leur fréquence et une normalisation tenant compte de la longueur des documents \cite{robertson_bm25_2009}. BM25 constitue une référence lexicale solide dans les expériences du benchmark BEIR \cite{thakur_beir_2021}. Dans sa formulation classique, il repose sur les correspondances entre les termes de la requête et ceux des documents \cite{robertson_bm25_2009}.
```

## Chapitre 1 — section 1.4.3 — ligne 421

[Ouvrir le passage](</Users/joelkouraogo/Desktop/Master 2 IBAM ISIE Soutenance 2026/Rapport/Rapport Joel KOURAOGO.tex:421>)

Avant :

```latex
En s’appuyant sur le sens général des textes, la recherche sémantique permet de retrouver des documents pertinents même lorsque les termes utilisés diffèrent de ceux de la requête. Elle facilite ainsi l’accès à l’information au sein de corpus volumineux. La qualité des résultats dépend cependant du modèle d’embeddings, de la langue, du domaine étudié et de la qualité du corpus.
```

Après :

```latex
Les représentations sémantiques peuvent permettre de retrouver des documents pertinents même lorsque les termes utilisés diffèrent de ceux de la requête \cite{karpukhin_dpr_2020}. Cette possibilité ne garantit pas leur supériorité sur les méthodes lexicales. Les expériences de BEIR montrent que les performances varient selon les modèles et les jeux de données, et que leur généralisation à de nouveaux domaines reste une difficulté \cite{thakur_beir_2021}.
```

## Chapitre 1 — section 1.4.3 — ligne 422

[Ouvrir le passage](</Users/joelkouraogo/Desktop/Master 2 IBAM ISIE Soutenance 2026/Rapport/Rapport Joel KOURAOGO.tex:422>)

Avant :

```latex
La taille des passages influe aussi sur les résultats. Un passage trop court peut manquer de contexte, alors qu’un passage trop long risque de réunir plusieurs informations distinctes.
```

Après :

```latex
Le découpage des documents constitue également un choix à évaluer expérimentalement. Qu, Tu et Bao montrent que le découpage sémantique n’apporte pas de gains systématiques par rapport à un découpage de taille fixe, malgré son coût de calcul supplémentaire \cite{qu_is_2024}.
```

## Chapitre 1 — section 1.5 — ligne 426

[Ouvrir le passage](</Users/joelkouraogo/Desktop/Master 2 IBAM ISIE Soutenance 2026/Rapport/Rapport Joel KOURAOGO.tex:426>)

Avant :

```latex
La représentation vectorielle traduit chaque document, passage ou requête en une suite de valeurs numériques appelée vecteur. En recherche sémantique, ces vecteurs sont placés dans un espace multidimensionnel : la distance qui les sépare sert à estimer la proximité de sens entre les textes associés. Deux vecteurs proches selon la mesure de similarité retenue correspondent donc, en principe, à des contenus sémantiquement similaires.
```

Après :

```latex
La représentation vectorielle traduit chaque document, passage ou requête en une suite de valeurs numériques appelée vecteur. En recherche sémantique, ces vecteurs sont placés dans un espace multidimensionnel : la distance qui les sépare sert à estimer la proximité de sens entre les textes associés. Deux vecteurs proches selon la mesure de similarité retenue correspondent donc, en principe, à des contenus sémantiquement similaires \cite{reimers_sbert_2019}.
```

## Chapitre 1 — section 1.5 — ligne 428

[Ouvrir le passage](</Users/joelkouraogo/Desktop/Master 2 IBAM ISIE Soutenance 2026/Rapport/Rapport Joel KOURAOGO.tex:428>)

Avant :

```latex
Cette transformation repose sur les \textit{embeddings} textuels, produits par des modèles d’intelligence artificielle. Un embedding convertit une phrase, un paragraphe ou un document en une représentation exploitable par le système. La qualité du modèle se mesure notamment à sa capacité à rapprocher les vecteurs de passages traitant d’un même sujet et à éloigner ceux dont le contenu diffère.
```

Après :

```latex
Cette transformation repose sur les \textit{embeddings} textuels, produits par des modèles d’intelligence artificielle. Un embedding convertit une phrase, un paragraphe ou un document en une représentation exploitable par le système. Pour la recherche documentaire, la proximité thématique ne suffit pas : les représentations doivent permettre de retrouver des passages pertinents pour la requête, ce qui nécessite une évaluation sur des requêtes et des documents dont la pertinence est connue \cite{thakur_beir_2021}.
```

## Chapitre 1 — section 1.5 — ligne 430

[Ouvrir le passage](</Users/joelkouraogo/Desktop/Master 2 IBAM ISIE Soutenance 2026/Rapport/Rapport Joel KOURAOGO.tex:430>)

Avant :

```latex
Les modèles \textit{Sentence Transformers} sont particulièrement adaptés à cette tâche, car ils génèrent des représentations vectorielles de phrases et de passages utilisables pour la recherche sémantique, le classement documentaire et la comparaison de textes. Lorsqu’un même modèle encode les passages d’un corpus et les requêtes, les vecteurs obtenus appartiennent au même espace de représentation et peuvent être comparés de manière cohérente.
```

Après :

```latex
La bibliothèque \textit{Sentence Transformers} permet d’utiliser des modèles qui génèrent des représentations vectorielles de phrases et de passages utilisables pour la recherche sémantique, le classement documentaire et la comparaison de textes. Lorsqu’un même modèle encode les passages d’un corpus et les requêtes, les vecteurs obtenus appartiennent au même espace de représentation et peuvent être comparés de manière cohérente \cite{reimers_sbert_2019,sbert_quickstart}.
```

## Chapitre 1 — section 1.6 — ligne 434

[Ouvrir le passage](</Users/joelkouraogo/Desktop/Master 2 IBAM ISIE Soutenance 2026/Rapport/Rapport Joel KOURAOGO.tex:434>)

Avant :

```latex
Une base de données vectorielle est conçue pour stocker, organiser et interroger des données représentées sous forme de vecteurs. Dans un système d’indexation sémantique, chaque passage documentaire est associé à son vecteur, à son texte d’origine et à des métadonnées. À partir du vecteur généré pour la requête de l’utilisateur, la base identifie ensuite les passages dont les vecteurs sont les plus proches et les retourne sous forme de résultats classés.
```

Après :

```latex
Une base de données vectorielle est conçue pour stocker, organiser et interroger des données représentées sous forme de vecteurs. Dans un système d’indexation sémantique, chaque passage documentaire est associé à son vecteur, à son texte d’origine et à des métadonnées. À partir du vecteur généré pour la requête de l’utilisateur, la base identifie ensuite les passages dont les vecteurs sont les plus proches et les retourne sous forme de résultats classés \cite{pan_survey_2024}.
```

## Chapitre 1 — section 1.6 — ligne 472

[Ouvrir le passage](</Users/joelkouraogo/Desktop/Master 2 IBAM ISIE Soutenance 2026/Rapport/Rapport Joel KOURAOGO.tex:472>)

Avant :

```latex
Les métadonnées conservées avec chaque vecteur sont essentielles : elles renseignent l’utilisateur sur le document retrouvé et servent à appliquer des filtres, par exemple sur la catégorie, la source ou la langue. La recherche des plus proches voisins compare le vecteur de la requête aux vecteurs des passages indexés afin d’identifier les résultats les plus pertinents. Une comparaison exhaustive devient coûteuse lorsque le volume de données augmente ; des index spécialisés, tels que HNSW ou IVF, accélèrent donc cette recherche en établissant un compromis entre rapidité et précision.
```

Après :

```latex
Les métadonnées conservées avec chaque vecteur sont essentielles : elles renseignent l’utilisateur sur le document retrouvé et servent à appliquer des filtres, par exemple sur la catégorie, la source ou la langue. La recherche des plus proches voisins compare le vecteur de la requête aux vecteurs des passages indexés afin de retrouver les vecteurs les plus proches selon la mesure retenue. Cette proximité ne garantit pas à elle seule la pertinence du contenu. Lorsque le volume de données augmente, des index tels que HNSW ou IVF peuvent réduire le coût de recherche, au prix éventuel d’une perte de rappel par rapport à une recherche exacte, selon les paramètres employés \cite{pan_survey_2024,douze_faiss_2025}.
```

## Chapitre 1 — section 1.6 — ligne 474

[Ouvrir le passage](</Users/joelkouraogo/Desktop/Master 2 IBAM ISIE Soutenance 2026/Rapport/Rapport Joel KOURAOGO.tex:474>)

Avant :

```latex
La proximité entre deux vecteurs peut être évaluée selon différentes mesures. Trois mesures sont couramment employées en recherche vectorielle : la similarité cosinus, la distance euclidienne et le produit scalaire.
```

Après :

```latex
La proximité entre deux vecteurs peut être évaluée selon différentes mesures. Trois mesures sont couramment employées en recherche vectorielle : la similarité cosinus, la distance euclidienne et le produit scalaire \cite{pan_survey_2024}.
```

## Notices ajoutées dans references.bib

```bibtex
@book{manning_ir_2008,
 author = {Manning, Christopher D. and Raghavan, Prabhakar and Schütze, Hinrich},
 title = {Introduction to Information Retrieval},
 publisher = {Cambridge University Press},
 year = {2008},
 doi = {10.1017/CBO9780511809071},
 url = {https://nlp.stanford.edu/IR-book/},
 urldate = {2026-11-02}
}

@article{robertson_bm25_2009,
 author = {Robertson, Stephen and Zaragoza, Hugo},
 title = {The Probabilistic Relevance Framework: {BM25} and Beyond},
 journaltitle = {Foundations and Trends in Information Retrieval},
 volume = {3},
 number = {4},
 pages = {333--389},
 year = {2009},
 doi = {10.1561/1500000019},
 url = {https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf},
 urldate = {2026-11-02}
}
```

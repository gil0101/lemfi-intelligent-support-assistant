# LemFi Intelligent Support Assistant

Assistant intelligent de support pour les transferts internationaux, développé dans le cadre d'un projet de **M2 Data Science**, pour le 
module de formation **Programmation en Python**.

Le projet combine les **modèles de langage (LLM)**, le **Retrieval-Augmented Generation (RAG)**, **PostgreSQL**, le **tool calling**, **FastAPI** et **Streamlit** afin de construire un assistant conversationnel capable de répondre à des questions liées aux transferts internationaux.

## 🎯 Objectif du projet

L'objectif est de développer un chatbot capable de répondre aux questions relatives aux transferts internationaux en combinant :

* les informations issues de la documentation LemFi ;
* les données transactionnelles structurées stockées dans PostgreSQL ;
* des outils spécialisés permettant d'interroger et d'analyser ces données ;
* l'historique de la conversation.

L'assistant doit être capable de déterminer si une question nécessite :

* une recherche dans la documentation ;
* une requête dans la base de données ;
* les deux ;
* ou une réponse directe.

> **Ce projet est un prototype académique et ne constitue pas un produit officiel de LemFi.**

## 🏗️ Architecture

```text
                    ┌─────────────────┐
                    │    Streamlit    │
                    │    Frontend     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │     FastAPI     │
                    │     Backend     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Orchestrateur   │
                    │      LLM        │
                    └───────┬─────────┘
                            / \
                           /   \
                          ▼     ▼
                    ┌───────┐ ┌────────────┐
                    │  RAG  │ │   Tools    │
                    └───┬───┘ └──────┬─────┘
                        │            │
                        ▼            ▼
                   Documents    PostgreSQL
```

## 🧩 Composants principaux

### RAG

Le pipeline RAG comprendra :

1. l'extraction des documents ;
2. le nettoyage ;
3. le découpage en chunks ;
4. la génération des embeddings ;
5. l'indexation vectorielle ;
6. la recherche sémantique ;
7. l'injection du contexte dans le LLM.

### PostgreSQL

Une base de données transactionnelle **synthétique mais réaliste** sera utilisée pour représenter notamment :

* les clients ;
* les bénéficiaires ;
* les transferts ;
* les statuts des transferts ;
* les événements liés aux transferts ;
* les motifs d'échec.

### Tools

Le LLM pourra utiliser des outils spécialisés tels que :

```text
get_transfer_status()
get_transfer_details()
get_customer_transfers()
get_transfer_history()
get_failed_transfers()
get_transfer_statistics()
```

Ces outils interagiront avec PostgreSQL au moyen de requêtes SQL paramétrées.

### Orchestration LLM

Le LLM devra déterminer quelle source utiliser pour chaque question et combiner les informations obtenues afin de produire une réponse cohérente.

## 🛠️ Technologies

* Python
* LLM
* RAG
* Embeddings / base vectorielle
* PostgreSQL
* FastAPI
* Streamlit
* Docker / Docker Compose
* Git / GitHub
* GitLab CI/CD
* Déploiement sur VPS

## 👥 Équipe

**M2 Data Science — Aix-Marseille Université**

* Gildas ADJAHOSSOU
* Mamadou DIAGNE

## ⚠️ Avertissement

Ce repository contient un prototype développé dans un cadre académique.

Il n'est pas affilié à LemFi, n'est pas approuvé par LemFi et ne constitue pas un produit officiel de LemFi.

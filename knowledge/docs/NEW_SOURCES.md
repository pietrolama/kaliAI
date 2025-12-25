# Nuove Fonti di Conoscenza per KaliAI

Questo documento descrive le nuove fonti di conoscenza integrate in KaliAI, organizzate per livello di priorità.

## Livello 1: Dati Strutturati (Priorità Massima)

Queste sono le risorse più preziose perché già organizzate per essere lette da una macchina.

### 1. PayloadsAllTheThings
- **Source**: `payloadsallthethings`
- **Tipo**: Repository GitHub con payload in Markdown
- **Descrizione**: Considerata la "Bibbia" dei payload per penetration testing
- **Configurazione**: 
  - Clona automaticamente il repository in `data/PayloadsAllTheThings`
  - Processa tutti i file `.md` con estrazione di payload e comandi
- **Uso**: 
  ```python
  from knowledge.sources import PayloadsAllTheThingsSource
  source = PayloadsAllTheThingsSource()
  results = source.fetch(update_repo=True, max_files=100)
  ```

### 2. Exploit-DB Repository Completo
- **Source**: `exploitdb_repo`
- **Tipo**: Repository GitHub completo con codice exploit
- **Descrizione**: Repository ufficiale che alimenta searchsploit
- **Configurazione**:
  - Clona automaticamente in `data/exploitdb`
  - Legge `files_exploits.csv` per metadati
  - Processa file exploit con analisi del codice
- **Uso**:
  ```python
  from knowledge.sources import ExploitDBRepoSource
  source = ExploitDBRepoSource()
  results = source.fetch(update_repo=True, max_exploits=1000)
  ```

### 3. CISA Known Exploited Vulnerabilities (KEV)
- **Source**: `cisa_kev`
- **Tipo**: File JSON giornaliero
- **Descrizione**: Vulnerabilità confermate come attivamente sfruttate
- **Priorità**: CRITICA - Queste vulnerabilità hanno relevance score 1.0
- **Uso**:
  ```python
  from knowledge.sources import CISAKEVSource
  source = CISAKEVSource()
  results = source.fetch(update_daily=True)
  ```

## Livello 2: Conoscenza Specialistica

Queste risorse richiedono scraping ma contengono informazioni di altissima qualità.

### 4. HackTricks
- **Source**: `hacktricks`
- **Tipo**: Scraping del sito web
- **Descrizione**: Enciclopedia di tecniche di hacking
- **Configurazione**:
  - Scraping da `book.hacktricks.xyz`
  - Estrazione di comandi e tecniche
  - Rate limiting: 0.5s tra richieste
- **Uso**:
  ```python
  from knowledge.sources import HackTricksSource
  source = HackTricksSource()
  results = source.fetch(max_pages=100)
  ```

### 5. OWASP Cheat Sheet Series
- **Source**: `owasp_cheatsheets`
- **Tipo**: Scraping del sito web
- **Descrizione**: Guida definitiva per sicurezza applicazioni web
- **Configurazione**:
  - Scraping da `cheatsheetseries.owasp.org`
  - Estrazione di sezioni e esempi di codice
- **Uso**:
  ```python
  from knowledge.sources import OWASPCheatSheetsSource
  source = OWASPCheatSheetsSource()
  results = source.fetch(max_sheets=50)
  ```

## Livello 3: Aggiornamenti Continui

Fonti di notizie e aggiornamenti per mantenere l'IA "fresca".

### 6. RSS Feeds Multipli
- **Source**: `rss_feeds`
- **Tipo**: Feed RSS multipli
- **Feed Inclusi**:
  - The Hacker News
  - Bleeping Computer
  - Krebs on Security
  - Threatpost
  - Security Week
- **Uso**:
  ```python
  from knowledge.sources import RSSFeedsSource
  source = RSSFeedsSource()
  results = source.fetch(days=7, max_items_per_feed=20)
  ```

## CTF Write-ups e Log di Hacking

Fonti per addestrare KaliAI con log reali di attacchi.

### 7. Hack The Box Write-ups
- **Source**: `htb_writeups`
- **Tipo**: Scraping da 0xdf.gitlab.io e altre fonti
- **Descrizione**: Write-ups dettagliati per macchine HTB ritirate
- **Caratteristiche**:
  - Estrazione automatica di comandi
  - Identificazione fasi dell'attacco
  - Creazione di "case files" strutturati
- **Uso**:
  ```python
  from knowledge.sources import HTBWriteupsSource
  source = HTBWriteupsSource()
  results = source.fetch(max_pages=50, retired_only=True)
  ```

### 8. TryHackMe Walkthroughs
- **Source**: `tryhackme`
- **Tipo**: Walkthrough da community
- **Descrizione**: Walkthrough per room TryHackMe
- **Uso**:
  ```python
  from knowledge.sources import TryHackMeSource
  source = TryHackMeSource()
  results = source.fetch(max_rooms=30)
  ```

### 9. VulnHub Write-ups
- **Source**: `vulnhub_writeups`
- **Tipo**: Write-ups da community
- **Descrizione**: Write-ups per macchine virtuali VulnHub
- **Uso**:
  ```python
  from knowledge.sources import VulnHubWriteupsSource
  source = VulnHubWriteupsSource()
  results = source.fetch(max_machines=30)
  ```

### 10. Honeypot Logs
- **Source**: `honeypot_logs`
- **Tipo**: Log da honeypot (T-Pot)
- **Descrizione**: Log di attacchi reali da honeypot
- **Configurazione**:
  - Richiede file JSON in `data/honeypot_logs/`
  - Formato T-Pot
- **Uso**:
  ```python
  from knowledge.sources import HoneypotLogsSource
  source = HoneypotLogsSource(log_path='data/honeypot_logs')
  results = source.fetch(max_logs=100)
  ```

### 11. Penetration Test Reports
- **Source**: `pentest_reports`
- **Tipo**: Report pubblici di pentest
- **Fonti**:
  - Cure53
  - NCC Group
  - Trail of Bits
- **Uso**:
  ```python
  from knowledge.sources import PentestReportsSource
  source = PentestReportsSource()
  results = source.fetch(max_reports=20)
  ```

## Formato Case File

Per strutturare i log di hacking, è stato creato un formato standard `CaseFile`:

```python
from knowledge.case_file_format import CaseFile, create_case_file_from_writeup

# Crea case file da write-up
case_file = create_case_file_from_writeup(
    title="HTB Lame",
    platform="hack_the_box",
    content="...",
    commands=[...],
    phases=[...],
    vulnerabilities=[...],
    source_url="https://..."
)

# Esporta in vari formati
json_str = case_file.to_json()
markdown_str = case_file.to_markdown()
```

## Configurazione

Tutti i sources sono configurati in `knowledge/rag_config.json`:

```json
{
  "sources": {
    "payloadsallthethings": {
      "enabled": true,
      "priority": 10,
      "collection": "kb",
      "update_frequency": "weekly",
      "params": {
        "update_repo": true,
        "max_files": null
      }
    }
  }
}
```

## Utilizzo con RAG Manager

```python
from knowledge.rag_manager import rag_manager

# Fetcha da tutti i sources abilitati
stats = rag_manager.fetch_all_sources(force=True)

# Cerca nella knowledge base
results = rag_manager.enhanced_search(
    "SQL injection payloads",
    top_k=10,
    source_filter=['payloadsallthethings', 'owasp_cheatsheets']
)
```

## Note Importanti

1. **Rate Limiting**: I sources che fanno scraping rispettano robots.txt e implementano delay tra richieste
2. **Repository Locali**: PayloadsAllTheThings e Exploit-DB vengono clonati localmente per performance
3. **Priorità**: CISA KEV ha priorità massima (relevance 1.0) perché sono vulnerabilità attivamente sfruttate
4. **Honeypot Logs**: Richiede setup manuale di T-Pot o file JSON in formato compatibile
5. **CTF Write-ups**: Alcuni sources sono template che possono essere estesi con scraping più sofisticato

## Prossimi Passi

- [ ] Implementare scraping più avanzato per GitHub write-ups
- [ ] Aggiungere supporto per altri honeypot (oltre T-Pot)
- [ ] Creare script di automazione per aggiornamento giornaliero
- [ ] Implementare deduplicazione intelligente dei contenuti
- [ ] Aggiungere metriche di qualità per ogni source



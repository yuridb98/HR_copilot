## 2026-09-19 — Un ENVIRONMENT sbagliato non dava errore
- **Sintomo**: con ENVIRONMENT=porod l'app partiva e usava solo base.yaml, senza nessun segnale.
- **Causa**: _load_yaml ritornava {} per qualsiasi file mancante.
- **Fix**: FileNotFoundError esplicito; CONFIG_DIR per non dipendere dal percorso del modulo.
- **Cosa ho imparato**: un default silenzioso su un errore di deploy è peggio di un crash.

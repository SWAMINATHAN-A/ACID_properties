# ACID Lab — Transaction Simulator

A Flask + MySQL website for learning database transaction properties. Includes a transaction dashboard, concurrent transfer requests, timestamped history, database event logs, CSV export, an ACID quiz, competitive-exam practice, learning notes, help, and project credits.

## Important

This is an educational simulator, not a banking product. Use sample data only. Do not enter real financial data or expose database credentials.

## Files

- `app.py` — Flask API and MySQL transaction logic.
- `static/index.html` — responsive website, quiz, competitive questions and learning pages.
- `schema.sql` — MySQL tables and starter accounts.
- `.env.example` — configuration template. Copy it to `.env` and fill in your own credentials.
- `render.yaml` and `Procfile` — deployment configuration examples.

## Run locally on Windows

1. Install Python 3.11+ and MySQL 8+.
2. In MySQL Workbench, open and run `schema.sql`.
3. In PowerShell, open this project folder and run:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   Copy-Item .env.example .env
   ```

4. Edit `.env` and set `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`. Keep `.env` private; it is excluded by `.gitignore`.
5. Start the app:

   ```powershell
   python app.py
   ```

6. Open `http://127.0.0.1:5000`.
7. Visit `http://127.0.0.1:5000/api/health` to confirm the server can reach MySQL.

## How simultaneous transfers work

Every HTTP request opens its own MySQL connection and transaction. The server locks sender/receiver rows with `SELECT ... FOR UPDATE`, acquiring account locks in sorted ID order to reduce deadlock risk. Debit, credit, status update and log writes are committed together. Concurrent requests can execute on separate Flask threads and MySQL coordinates conflicting row updates. A simulated rollback intentionally rolls back the transfer and writes a separate failed-attempt record afterward.

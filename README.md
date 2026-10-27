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

## Deploy publicly

A public website cannot connect to MySQL running only on your laptop. You need (1) a hosted MySQL database and (2) a Python web host.

1. Create a hosted MySQL database with a provider such as Railway or Aiven. Copy its connection hostname, port, database, username and password.
2. Import `schema.sql` into that hosted database. If the provider creates a database for you, run the table definitions and starter-account inserts after selecting that database; you may omit the `CREATE DATABASE` / `USE` lines if your provider restricts them. If you are reusing your existing `acid_simulator` database, first add the `completed_at` field by running `migration_add_completed_at.sql` once (only if that column is not already present).
3. Push this folder to a new GitHub repository. Do **not** commit `.env`, real passwords, or database URLs.
4. Create a Python web service on Render from the repository. The included `render.yaml` sets the build/start commands. Set the environment variables in the host dashboard using the values from your hosted database. Keep `MYSQL_SSL_DISABLED=false` for hosted services that require TLS; follow your database provider's SSL instructions.
5. Deploy and check `/api/health`. If it reports unavailable, inspect the host logs and verify the host, port, credentials, database name, allowed network access and SSL settings.
6. Open the service's public URL and test a successful transfer, a rollback simulation, CSV download and the quiz. Check that balances and transaction history persist after reloading the page.

The exact database and hosting dashboard screens can change. Keep credentials in host environment variables, not in Python or HTML files.

## Competitive-exam practice sources

Some questions are paraphrased/adapted for practice and clearly labeled as such. Reference links are included in the website, including GATE CSE transaction PYQ archives, official GATE downloads, and a UGC NET DBMS PYQ archive. Verify original wording and answer keys from the original papers when preparing for exams.

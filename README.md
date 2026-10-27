## ACID Property Simulator

A database transaction simulator demonstrating Atomicity, Consistency, Isolation, and Durability using Python, Flask, and MySQL.

### Prerequisites
- Python 3.10 or newer
- MySQL Server and MySQL Workbench
- Git

### Setup Instructions

**1. Clone the repository**
```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd YOUR_REPOSITORY_FOLDER
```

**2. Create the database**

Open MySQL Workbench, connect to your local MySQL server, and import `acid_simulator_full.sql`.

Alternatively, using a terminal:
```bash
mysql -u YOUR_MYSQL_USERNAME -p < acid_simulator_full.sql
```

**3. Configure environment variables**

Create a `.env` file using `.env.example` as a reference. Enter your own MySQL host, port, username, password, and database name.

Never share or commit your real `.env` credentials.

**4. Install dependencies**

```bash
pip install -r requirements.txt
```

If `requirements.txt` is inside the `backend` folder, run:
```bash
pip install -r backend/requirements.txt
```

**5. Run the application**

Follow the startup command and working directory specified by the project's Flask entry point.

### Important Notes
- Each user runs their own local MySQL database.
- Import the provided SQL file before starting the backend.
- Keep database credentials private.
- Transactions and account balances persist in the configured MySQL database when successfully committed.

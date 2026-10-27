
import csv
import io
import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, date

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file

load_dotenv()
app = Flask(__name__, static_folder="static", static_url_path="")


def get_connection():
    required = ["MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError("Missing database configuration: " + ", ".join(missing))

    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE", "acid_simulator"),
        connection_timeout=10,
        autocommit=False,
        ssl_disabled=os.getenv("MYSQL_SSL_DISABLED", "false").lower() == "true",
    )


def json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ", timespec="seconds") if isinstance(value, datetime) else value.isoformat()
    return value


def close_quietly(cursor=None, connection=None):
    if cursor is not None:
        try:
            cursor.close()
        except Error:
            pass
    if connection is not None:
        try:
            connection.close()
        except Error:
            pass


def log_event(cursor, transaction_id, operation, message):
    cursor.execute(
        "INSERT INTO transaction_logs (transaction_id, operation, message) VALUES (%s, %s, %s)",
        (transaction_id, operation, message),
    )


def save_failed_transaction(sender_id, receiver_id, amount, message):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO transactions (from_account, to_account, amount, status) VALUES (%s, %s, %s, 'FAILED')",
            (sender_id, receiver_id, amount),
        )
        transaction_id = cursor.lastrowid
        log_event(cursor, transaction_id, "ROLLBACK", message[:255])
        connection.commit()
        return transaction_id
    finally:
        close_quietly(cursor, connection)


@app.get("/")
def home():
    return app.send_static_file("index.html")


@app.get("/api/health")
def health():
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return jsonify({"ok": True, "database": "connected"})
    except Exception:
        app.logger.exception("Health check failed")
        return jsonify({"ok": False, "database": "unavailable"}), 503
    finally:
        close_quietly(cursor, connection)


@app.get("/api/accounts")
def list_accounts():
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT account_id, account_name, balance FROM accounts ORDER BY account_id"
        )
        rows = cursor.fetchall()
        return jsonify([
            {**row, "balance": json_value(row["balance"])}
            for row in rows
        ])
    except Exception:
        app.logger.exception("Could not load accounts")
        return jsonify({"error": "Could not load accounts. Check the database connection and schema."}), 503
    finally:
        close_quietly(cursor, connection)


@app.get("/api/transactions")
def list_transactions():
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """SELECT t.transaction_id AS id,
                      t.from_account AS sender_id,
                      t.to_account AS receiver_id,
                      a1.account_name AS sender_name,
                      a2.account_name AS receiver_name,
                      t.amount, t.status, t.created_at
               FROM transactions t
               LEFT JOIN accounts a1 ON a1.account_id = t.from_account
               LEFT JOIN accounts a2 ON a2.account_id = t.to_account
               ORDER BY t.transaction_id DESC LIMIT 500"""
        )
        rows = cursor.fetchall()
        return jsonify([
            {
                "id": row["id"],
                "senderId": row["sender_id"],
                "receiverId": row["receiver_id"],
                "senderName": row["sender_name"] or "Unknown account",
                "receiverName": row["receiver_name"] or "Unknown account",
                "amount": json_value(row["amount"]),
                "status": row["status"],
                "createdAt": json_value(row["created_at"]),
                "completedAt": json_value(row["created_at"]),
            }
            for row in rows
        ])
    except Exception:
        app.logger.exception("Could not load transaction history")
        return jsonify({"error": "Could not load transaction history."}), 503
    finally:
        close_quietly(cursor, connection)


@app.get("/api/stats")
def stats():
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """SELECT COUNT(*) AS total,
                      COALESCE(SUM(status = 'COMMITTED'), 0) AS committed,
                      COALESCE(SUM(status = 'FAILED'), 0) AS failed,
                      COALESCE(SUM(CASE WHEN status = 'COMMITTED' THEN amount ELSE 0 END), 0) AS total_value
               FROM transactions"""
        )
        row = cursor.fetchone()
        return jsonify({
            "total": row["total"],
            "committed": row["committed"],
            "rolledBack": row["failed"],
            "value": json_value(row["total_value"]),
        })
    except Exception:
        app.logger.exception("Could not load statistics")
        return jsonify({"error": "Could not load statistics."}), 503
    finally:
        close_quietly(cursor, connection)


@app.get("/api/transactions/<int:transaction_id>")
def transaction_detail(transaction_id):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """SELECT t.transaction_id AS id,
                      t.from_account AS sender_id,
                      t.to_account AS receiver_id,
                      a1.account_name AS sender_name,
                      a2.account_name AS receiver_name,
                      t.amount, t.status, t.created_at
               FROM transactions t
               LEFT JOIN accounts a1 ON a1.account_id = t.from_account
               LEFT JOIN accounts a2 ON a2.account_id = t.to_account
               WHERE t.transaction_id = %s""",
            (transaction_id,),
        )
        transaction = cursor.fetchone()
        if not transaction:
            return jsonify({"error": "Transaction not found."}), 404

        cursor.execute(
            "SELECT operation, message, created_at FROM transaction_logs WHERE transaction_id=%s ORDER BY log_id",
            (transaction_id,),
        )
        logs = cursor.fetchall()

        for log in logs:
            log["created_at"] = json_value(log["created_at"])

        transaction["amount"] = json_value(transaction["amount"])
        transaction["created_at"] = json_value(transaction["created_at"])
        transaction["completed_at"] = json_value(transaction["created_at"])

        return jsonify({"transaction": transaction, "logs": logs})
    except Exception:
        app.logger.exception("Could not load transaction details")
        return jsonify({"error": "Could not load transaction details."}), 503
    finally:
        close_quietly(cursor, connection)


def parse_transfer_payload():
    payload = request.get_json(silent=True) or {}

    try:
        sender_id = int(payload.get("sender_id"))
        receiver_id = int(payload.get("receiver_id"))
        amount = Decimal(str(payload.get("amount", ""))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    except (ValueError, TypeError, InvalidOperation):
        return None, (
            jsonify({"error": "Enter valid account IDs and a numeric amount."}),
            400,
        )

    if sender_id == receiver_id:
        return None, (
            jsonify({"error": "Sender and receiver must be different accounts."}),
            400,
        )

    if amount <= 0:
        return None, (
            jsonify({"error": "Amount must be greater than zero."}),
            400,
        )

    return {
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "amount": amount,
        "simulate_rollback": bool(payload.get("simulate_rollback", False)),
    }, None


@app.post("/api/transfers")
def create_transfer():
    data, error = parse_transfer_payload()
    if error:
        return error

    sender_id = data["sender_id"]
    receiver_id = data["receiver_id"]
    amount = data["amount"]
    simulate_rollback = data["simulate_rollback"]

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()
        connection.start_transaction()

        cursor.execute(
            "INSERT INTO transactions (from_account, to_account, amount, status) VALUES (%s, %s, %s, 'STARTED')",
            (sender_id, receiver_id, amount),
        )
        transaction_id = cursor.lastrowid
        log_event(cursor, transaction_id, "START", "Transaction started")

        locked = {}
        for account_id in sorted([sender_id, receiver_id]):
            cursor.execute(
                "SELECT account_id, account_name, balance FROM accounts WHERE account_id=%s FOR UPDATE",
                (account_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Account #{account_id} was not found.")
            locked[account_id] = row

        sender = locked[sender_id]
        receiver = locked[receiver_id]

        if Decimal(str(sender[2])) < amount:
            raise ValueError("Insufficient balance for this transfer.")

        cursor.execute(
            "UPDATE accounts SET balance = balance - %s WHERE account_id = %s",
            (amount, sender_id),
        )
        log_event(cursor, transaction_id, "DEBIT", f"{amount:.2f} debited from {sender[1]}")

        if simulate_rollback:
            connection.rollback()
            close_quietly(cursor, connection)
            cursor = None
            connection = None

            failed_id = save_failed_transaction(
                sender_id,
                receiver_id,
                amount,
                "Educational rollback simulation: changes were rolled back.",
            )
            return jsonify({
                "id": failed_id,
                "status": "FAILED",
                "message": "Rollback simulated. The transfer did not change account balances.",
            }), 201

        cursor.execute(
            "UPDATE accounts SET balance = balance + %s WHERE account_id = %s",
            (amount, receiver_id),
        )
        log_event(cursor, transaction_id, "CREDIT", f"{amount:.2f} credited to {receiver[1]}")

        cursor.execute(
            "UPDATE transactions SET status='COMMITTED' WHERE transaction_id=%s",
            (transaction_id,),
        )
        log_event(cursor, transaction_id, "COMMIT", "Transaction committed successfully")

        connection.commit()

        return jsonify({
            "id": transaction_id,
            "status": "COMMITTED",
            "message": "Transfer committed successfully.",
        }), 201

    except ValueError as exc:
        if connection:
            try:
                connection.rollback()
            except Error:
                pass

        close_quietly(cursor, connection)
        cursor = None
        connection = None

        try:
            failed_id = save_failed_transaction(
                sender_id, receiver_id, amount, str(exc)
            )
            return jsonify({
                "id": failed_id,
                "status": "FAILED",
                "error": str(exc),
            }), 400
        except Exception:
            app.logger.exception("Could not record failed transfer")
            return jsonify({"error": str(exc)}), 400

    except Exception:
        app.logger.exception("Transfer failed")

        if connection:
            try:
                connection.rollback()
            except Error:
                pass

        close_quietly(cursor, connection)
        cursor = None
        connection = None

        try:
            failed_id = save_failed_transaction(
                sender_id,
                receiver_id,
                amount,
                "Database error; transaction rolled back.",
            )
            return jsonify({
                "id": failed_id,
                "status": "FAILED",
                "error": "Database error. The transaction was rolled back.",
            }), 500
        except Exception:
            return jsonify({
                "error": "Database error. The transaction was rolled back where possible."
            }), 500

    finally:
        close_quietly(cursor, connection)


@app.get("/api/transactions.csv")
def download_csv():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """SELECT t.transaction_id, a1.account_name, a2.account_name,
                      t.amount, t.status, t.created_at
               FROM transactions t
               LEFT JOIN accounts a1 ON a1.account_id = t.from_account
               LEFT JOIN accounts a2 ON a2.account_id = t.to_account
               ORDER BY t.transaction_id DESC"""
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "transaction_id", "sender", "receiver", "amount_inr",
            "status", "created_at", "completed_at",
        ])

        for row in cursor.fetchall():
            timestamp = json_value(row[5])
            writer.writerow([
                row[0],
                row[1] or "Unknown",
                row[2] or "Unknown",
                str(row[3]),
                row[4],
                timestamp,
                timestamp,
            ])

        memory_file = io.BytesIO(output.getvalue().encode("utf-8-sig"))
        memory_file.seek(0)

        return send_file(
            memory_file,
            mimetype="text/csv",
            as_attachment=True,
            download_name="acid-lab-transactions.csv",
        )
    except Exception:
        app.logger.exception("Could not export transactions")
        return jsonify({"error": "Could not export transaction data."}), 503
    finally:
        close_quietly(cursor, connection)


@app.post("/api/demos/consistency")
def consistency_demo():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()
        connection.start_transaction()

        cursor.execute(
            "INSERT INTO accounts (account_name, balance) VALUES (%s, %s)",
            ("Invalid Account", Decimal("-500.00")),
        )
        connection.commit()

        return jsonify({
            "ok": False,
            "message": "The database accepted the test row. Verify that the accounts table has CHECK (balance >= 0).",
        }), 500

    except mysql.connector.IntegrityError:
        if connection:
            connection.rollback()

        return jsonify({
            "ok": True,
            "message": "MySQL rejected the negative balance and the transaction was rolled back. Consistency rule verified.",
        })

    except Exception:
        app.logger.exception("Consistency demonstration could not run")

        if connection:
            try:
                connection.rollback()
            except Error:
                pass

        return jsonify({
            "error": "Could not run the consistency test. Check database connectivity and the CHECK constraint."
        }), 503

    finally:
        close_quietly(cursor, connection)


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "API endpoint not found."}), 404
    return app.send_static_file("index.html")


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False,
        threaded=True,
    )

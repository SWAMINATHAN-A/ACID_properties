CREATE DATABASE IF NOT EXISTS acid_simulator;
USE acid_simulator;

CREATE TABLE IF NOT EXISTS accounts (
    account_id INT PRIMARY KEY AUTO_INCREMENT,
    account_name VARCHAR(100) NOT NULL,
    balance DECIMAL(10,2) NOT NULL,
    CHECK (balance >= 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INT PRIMARY KEY AUTO_INCREMENT,
    from_account INT,
    to_account INT,
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL DEFAULT NULL,
    CONSTRAINT fk_transactions_sender FOREIGN KEY (from_account) REFERENCES accounts(account_id),
    CONSTRAINT fk_transactions_receiver FOREIGN KEY (to_account) REFERENCES accounts(account_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS transaction_logs (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    transaction_id INT,
    operation VARCHAR(100),
    message VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_logs_transaction FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
) ENGINE=InnoDB;

INSERT INTO accounts (account_name, balance)
SELECT 'Alice', 10000.00 WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE account_name = 'Alice');
INSERT INTO accounts (account_name, balance)
SELECT 'Bob', 5000.00 WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE account_name = 'Bob');
INSERT INTO accounts (account_name, balance)
SELECT 'Charlie', 7500.00 WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE account_name = 'Charlie');
INSERT INTO accounts (account_name, balance)
SELECT 'David', 3000.00 WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE account_name = 'David');

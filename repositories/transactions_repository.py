import sqlite3
import logging
import uuid
from datetime import datetime
from utils.logger import get_logger
from utils.helppers import resource_path
from entities.transactions_entity import TransactionEntity

class TransactionsRepository:
    
    def __init__(self):
        self._db_path = resource_path('database/database.db')
        self.logger = get_logger("TransactionsRepository")
        self.create_table()
        self.total_income , self.total_outcome = self.get_total()

    def _connect(self):
        return sqlite3.connect(self._db_path)

    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS Transactions (
            id TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            owner TEXT NOT NULL DEFAULT 'talisma',
            email TEXT NOT NULL DEFAULT 'talisma@email.com',
            status TEXT NOT NULL DEFAULT 'unsynced',
            createdAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
        with self._connect() as conn:
            conn.execute(query)

#insert methods
    def insert_one(self, transaction: TransactionEntity):
        query = """
        INSERT INTO Transactions (id, description, type, category, price, owner, email, status, createdAt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        # createdAt = datetime.now().isoformat(timespec='milliseconds') + 'Z' # padrão ISO 8601 para datas
        with self._connect() as conn:
            try:
                conn.execute(query, (
                    str(uuid.uuid4()),
                    transaction.description,
                    transaction.type,
                    transaction.category,
                    transaction.price,
                    transaction.owner,
                    transaction.email,
                    transaction.status,
                    transaction.created_at 
                ))
                self.logger.info(f"Transaction with ID {transaction.id} inserted successfully!")
            except sqlite3.Error as e:
                self.logger.error(f"Error inserting transaction: {e}")

    def insert_many(self, transactions: list[TransactionEntity]):
        query = """
        INSERT INTO Transactions (id, description, type, category, price, owner, email, status, createdAt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        successful_insertions = 0
        failed_transactions = []

        with self._connect() as conn:
            cur = conn.cursor()
            for transaction in transactions:
                try:
                    cur.execute(query, (
                        transaction.id,
                        transaction.description,
                        transaction.type,
                        transaction.category,
                        transaction.price,
                        transaction.owner,
                        transaction.email,
                        transaction.status,
                        transaction.created_at
                    ))
                    successful_insertions += 1
                except sqlite3.Error as e:
                    self.logger.error(f"Error inserting transaction: {transaction}. Details: {e}")
                    failed_transactions.append(transaction)

            conn.commit()
            self.logger.info(f"{successful_insertions} transactions inserted successfully.")
            if failed_transactions:
                self.logger.warning(f"{len(failed_transactions)} transactions failed and were ignored.")

    def insert_non_synced(self, transaction: TransactionEntity):
        query = """
        INSERT INTO Transactions (id, description, type, category, price, owner, email, status, createdAt)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'unsynced', ?)
        """
        with self._connect() as conn:
            try:
                conn.execute(query, (
                    transaction.id,
                    transaction.description,
                    transaction.type,
                    transaction.category,
                    transaction.price,
                    transaction.owner,
                    transaction.email,
                    transaction.created_at
                ))
                self.logger.info(f"Non-synced transaction with ID {transaction.id} inserted successfully!")
            except sqlite3.Error as e:
                self.logger.error(f"Error inserting non-synced transaction: {e}")

#fetch methods
    def is_database_empty(self):
        with self._connect() as conn:
            cur = conn.cursor()
            query = "SELECT COUNT(*) FROM transactions"
            cur.execute(query)
            count = cur.fetchone()[0]
            return count == 0
        
    def fetch_somes(self, last_date) -> list[TransactionEntity]: # last_date shoulb be in format %Y-%m-%d

        query = """
        SELECT id, description, type, category, price, owner, email, status, createdAt
        FROM Transactions 
        WHERE status IN ('synced', 'unsynced', 'updated') AND createdAt < ? 
        ORDER BY createdAt DESC 
        LIMIT 20
        """ if last_date else """
        SELECT id, description, type, category, price, owner, email, status, createdAt
        FROM Transactions 
        WHERE status IN ('synced', 'unsynced', 'updated')
        ORDER BY createdAt DESC 
        LIMIT 20
        """
        self.total_income , self.total_outcome = self.get_total()

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query, (last_date,) if last_date else ())
            transactions = cur.fetchall()

        return [TransactionEntity(*t) for t in transactions]
    
    def get_all(self) -> list[TransactionEntity]:
        query = 'SELECT id, description, type, category, price, owner, email, status, createdAt FROM Transactions ORDER BY createdAt DESC'
        with self._connect() as conn:
            cur = conn.cursor()
            transactions = cur.execute(query).fetchall()
            return [TransactionEntity(*t) for t in transactions]
    
    def get_deleted_transactions(self) -> list[TransactionEntity]:
        query = """
        SELECT id, description, type, category, price, owner, email, status, createdAt
        FROM Transactions 
        WHERE status == 'deleted'
        """
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query)
            transactions = cur.fetchall()

        return [TransactionEntity(*t) for t in transactions]
    
    def get_updated_transactions(self) -> list[TransactionEntity]:
        query = """
        SELECT id, description, type, category, price, owner, email, status, createdAt 
        FROM Transactions 
        WHERE status == 'updated'
        ORDER BY createdAt DESC 
        """

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query)
            transactions = cur.fetchall()

        return [TransactionEntity(*t) for t in transactions]

    def get_unsynced_transactions(self) -> list[TransactionEntity]:
        query = """
        SELECT id, description, type, category, price, owner, email, status, createdAt
        FROM Transactions
        WHERE status IN ('unsynced', 'deleted', 'updated')
        """

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query)
            transactions = cur.fetchall()

        return [TransactionEntity(*t) for t in transactions]

    def get_filter_options(self, column: str) -> list[str]:
        allowed_columns = {
            "category",
            "type",
            "status",
        }

        if column not in allowed_columns:
            raise ValueError(f"Invalid column: {column}")

        query = f"""
            SELECT DISTINCT {column}
            FROM Transactions
            WHERE status != 'deleted'
              AND {column} IS NOT NULL
              AND {column} != ''
            ORDER BY {column} ASC
        """

        with self._connect() as conn:
            cursor = conn.execute(query)
            return [row[0] for row in cursor.fetchall()]

    def get_total(self, filters=None):
        query = """
            SELECT
                COALESCE(SUM(CASE WHEN type = 'income' THEN price ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN type = 'outcome' THEN price ELSE 0 END), 0)
            FROM Transactions
            WHERE status != 'deleted'
        """

        params = []

        if filters:
            if filters.get("keyword"):
                query += """
                    AND (
                        description LIKE ?
                        OR category LIKE ?
                        OR CAST(price AS TEXT) LIKE ?
                    )
                """

                keyword = f"%{filters['keyword']}%"
                params.extend([keyword, keyword, keyword])

            if filters.get("category"):
                query += (
                    " AND ("
                    + " OR ".join(
                        ["category LIKE ?"] * len(filters["category"])
                    )
                    + ")"
                )

                params.extend(
                    [f"%{value}%" for value in filters["category"]]
                )

            if filters.get("type"):
                query += (
                    " AND ("
                    + " OR ".join(
                        ["type LIKE ?"] * len(filters["type"])
                    )
                    + ")"
                )

                params.extend(
                    [f"%{value}%" for value in filters["type"]]
                )

            if filters.get("status"):
                query += (
                    " AND ("
                    + " OR ".join(
                        ["status LIKE ?"] * len(filters["status"])
                    )
                    + ")"
                )

                params.extend(
                    [f"%{value}%" for value in filters["status"]]
                )

            if filters.get("start_date"):
                query += " AND createdAt >= ?"
                params.append(filters["start_date"])

            if filters.get("end_date"):
                query += " AND createdAt < ?"
                params.append(filters["end_date"])

        with self._connect() as conn:
            cur = conn.execute(query, params)
            row = cur.fetchone()

            self.total_income = row[0]
            self.total_outcome = row[1]

            return self.total_income, self.total_outcome

    #delete methods
    def delete_many(self, transaction_ids: list[str]):
        """
        Deleta múltiplas transações no banco de dados local.
        """
        with self._connect() as conn:
            cur = conn.cursor()
            try:
                # Construir a query para deletar múltiplos registros
                query = "DELETE FROM transactions WHERE id IN ({})".format(
                ",".join(["?" for _ in transaction_ids])
                )
                # Executando a query para deletar as transações
                cur.execute(query, transaction_ids)
                logging.info(f'{len(transaction_ids)} transações deletadas com sucesso!')
            except Exception as e:
                logging.error(f"Erro ao deletar transações: {e}")

    def check_status(self,transaction_id: str):
        with self._connect() as conn:
            cur = conn.cursor()
            # Execute a query
            query = "SELECT * FROM transactions WHERE id = ?"
            cur.execute(query, (transaction_id,))
            transaction = cur.fetchone()
            if not transaction:
                logging.info(f'Transação com id {transaction_id} nao foi encontrada!')
                return 
            return transaction[7] # status is the 7º position 
      
    def delete_transaction_from_db(self, transaction_id: str):
        with self._connect() as conn:
            cur = conn.cursor()
            query = "DELETE FROM Transactions WHERE id = ?"
            cur.execute(query, (transaction_id,))
            logging.info(f'Transação com id {transaction_id} deletada com sucesso!')

    def mark_as_deleted(self, transaction_id: str):
        with self._connect() as conn:
            cur = conn.cursor()
            query = "UPDATE transactions SET status = ? WHERE id = ?"
            cur.execute(query, ("deleted", transaction_id))
            logging.info(f'Transação com id {transaction_id} marcada como deleted com sucesso!')

#update methods 
    def update_many(self, transactions: list[TransactionEntity]):
        query = """
        UPDATE Transactions SET 
        description = ?, type = ?, category = ?, price = ?, owner = ?, email = ?, status = ?, createdAt = ?
        WHERE id = ?
        """
        with self._connect() as conn:
            cur = conn.cursor()
            for transaction in transactions:
                try:
                    cur.execute(query, (
                        transaction.description,
                        transaction.type,
                        transaction.category,
                        transaction.price,
                        transaction.owner,
                        transaction.email,
                        transaction.status,
                        transaction.created_at,
                        transaction.id
                    ))
                except sqlite3.Error as e:
                    self.logger.error(f"Error updating transaction ID {transaction.id}: {e}")
            conn.commit()

        self.logger.info(f"Updated {len(transactions)} transactions successfully.")

    def update_one(self, transaction: TransactionEntity):
        query = """
        UPDATE Transactions SET 
        description = ?, type = ?, category = ?, price = ?, status = ?, createdAt = ?
        WHERE id = ?
        """
        
        with self._connect() as conn:
            try:
                conn.execute(query, (
                    transaction.description,
                    transaction.type,
                    transaction.category,
                    transaction.price,
                    transaction.status,
                    transaction.created_at,
                    transaction.id
                ))
                self.logger.info(f"Transaçao com id: {transaction.id} updated successfully!")
            except sqlite3.Error as e:
                self.logger.error(f"Error updating transaction: {e}")

    def mark_as_synced(self,transactions):
      with self._connect() as conn:
            cur = conn.cursor()
            
            for transaction in transactions:
                query = "UPDATE Transactions SET status = 'synced' WHERE id = ?"
                cur.execute(query, (transaction['id'],))  # Marcar cada transação como sincronizada
                logging.info(f"Transação {transaction['id']} marcada como sincronizada.")


    
    def search_transactions_by_filters(
        self,
        last_date=None,
        filters=None
    ) -> list[TransactionEntity]:
    
        query = """
            SELECT
                id,
                description,
                type,
                category,
                price,
                owner,
                email,
                status,
                createdAt
            FROM Transactions
            WHERE status != 'deleted'
        """
    
        params = []
    
        # --------------------------------
        # Keyword
        # --------------------------------
    
        if filters.get("keyword"):
            query += """
                AND (
                    description LIKE ?
                    OR category LIKE ?
                    OR CAST(price AS TEXT) LIKE ?
                )
            """
    
            keyword = f"%{filters['keyword']}%"
            params.extend([keyword, keyword, keyword])
    
        # --------------------------------
        # Category
        # --------------------------------
    
        if filters.get("category"):
            query += (
                " AND ("
                + " OR ".join(
                    ["category LIKE ?"] * len(filters["category"])
                )
                + ")"
            )
    
            params.extend(
                [f"%{value}%" for value in filters["category"]]
            )
    
        # --------------------------------
        # Type
        # --------------------------------
    
        if filters.get("type"):
            query += (
                " AND ("
                + " OR ".join(
                    ["type LIKE ?"] * len(filters["type"])
                )
                + ")"
            )
    
            params.extend(
                [f"%{value}%" for value in filters["type"]]
            )
    
        # --------------------------------
        # Status
        # --------------------------------
    
        if filters.get("status"):
            query += (
                " AND ("
                + " OR ".join(
                    ["status LIKE ?"] * len(filters["status"])
                )
                + ")"
            )
    
            params.extend(
                [f"%{value}%" for value in filters["status"]]
            )
    
        # --------------------------------
        # Período
        # --------------------------------
    
        if filters.get("start_date"):
            query += " AND createdAt >= ?"
            params.append(filters["start_date"])
    
        if filters.get("end_date"):
            query += " AND createdAt < ?"
            params.append(filters["end_date"])
    
        # --------------------------------
        # Paginação
        # --------------------------------
    
        if last_date:
            query += " AND createdAt < ?"
            params.append(last_date)
    
        # --------------------------------
        # Ordenação + limite
        # --------------------------------
    
        query += """
            ORDER BY createdAt DESC
            LIMIT 20
        """
    
        with self._connect() as conn:
            cursor = conn.execute(query, params)
            transactions = cursor.fetchall()
    
            return [
                TransactionEntity(*transaction)
                for transaction in transactions
            ]
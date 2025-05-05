import sys
from util.config import get_config_path
import sqlite3
import os

class Economy:
    def __init__(self):
        appdata_dir = os.path.dirname(get_config_path())  # Get the app data directory
        self.db_path = os.path.join(appdata_dir, "economy.db")
        self.initialize_database()

    def initialize_database(self):
        """Initialize the SQLite database for storing user balances."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_balances (
                user_id TEXT PRIMARY KEY,
                balance REAL NOT NULL DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

    def get_balance(self, user_id):
        """Retrieve the balance of a user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT balance
            FROM user_balances
            WHERE user_id = ?
        """, (user_id,))
        result = cursor.fetchone()
        conn.close()
        # round to nearest 0.01
        if result:
            result = round(result[0], 2)
        else:
            result = 0.0
        return result

    def add_balance(self, user_id, amount):
        """Add an amount to the user's balance."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        current_balance = self.get_balance(user_id)
        new_balance = round(current_balance + amount, 2)
        cursor.execute("""
            INSERT INTO user_balances (user_id, balance)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET balance = excluded.balance
        """, (user_id, new_balance))
        conn.commit()
        conn.close()
        return new_balance

    def deduct_balance(self, user_id, amount):
        """Deduct an amount from the user's balance."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        current_balance = self.get_balance(user_id)
        if current_balance < amount:
            conn.close()
            return {"error": "Insufficient funds."}
        new_balance = round(current_balance - amount, 2)
        cursor.execute("""
            UPDATE user_balances
            SET balance = ?
            WHERE user_id = ?
        """, (new_balance, user_id))
        conn.commit()
        conn.close()
        return new_balance

    def get_top_balances(self, limit=5):
        """Retrieve the top users with the highest balances."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, balance
            FROM user_balances
            ORDER BY balance DESC
            LIMIT ?
        """, (limit,))
        top_players = cursor.fetchall()
        conn.close()
        new_top_players = []
        for player in top_players:
            new_top_players.append((player[0], round(player[1], 2)))
        top_players = sorted(new_top_players, key=lambda x: x[1], reverse=True)
        top_players = [{"name": player[0], "balance": player[1]} for player in top_players]
        return top_players
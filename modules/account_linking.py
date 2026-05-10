"""
Account linking module for cross-platform user identification.
"""
import random
import string
from datetime import datetime, timedelta
from util.database import DatabaseConnection
from util.module_registry import module_registry


class AccountLinking:
    """Manage account linking across platforms."""
    
    def __init__(self):
        """Initialize the account linking module."""
        self.code_length = 6
        self.code_expiry_minutes = 10

    def _translate(self, t, key, default_text, **kwargs):
        if callable(t):
            translated = t(key, **kwargs)
            if translated != key:
                return translated
        return default_text.format(**kwargs)
    
    def generate_code(self, platform: str, identifier: str) -> str:
        """
        Generate a temporary linking code for a user.
        
        :param platform: The platform (e.g., 'discord', 'cs2')
        :param identifier: The user identifier on that platform
        :return: The generated code
        """
        # Generate a random 6-digit code
        code = ''.join(random.choices(string.digits, k=self.code_length))
        
        # Calculate expiration time
        expires_at = datetime.now() + timedelta(minutes=self.code_expiry_minutes)
        
        with DatabaseConnection() as cursor:
            # Remove any existing codes for this user
            cursor.execute("""
                DELETE FROM link_codes
                WHERE platform = %s AND identifier = %s
            """, (platform, identifier))
            
            # Insert the new code
            cursor.execute("""
                INSERT INTO link_codes (code, platform, identifier, expires_at)
                VALUES (%s, %s, %s, %s)
            """, (code, platform, identifier, expires_at))
        
        return code
    
    def use_code(self, code: str, target_platform: str, target_identifier: str, t=None) -> dict:
        """
        Use a linking code to link two accounts.
        
        :param code: The linking code
        :param target_platform: The platform of the account using the code
        :param target_identifier: The identifier on that platform
        :return: Dictionary with success/error information
        """
        with DatabaseConnection() as cursor:
            # Find the code
            cursor.execute("""
                SELECT platform, identifier, expires_at
                FROM link_codes
                WHERE code = %s
            """, (code,))
            
            result = cursor.fetchone()
            
            if not result:
                return {"error": self._translate(t, "commands.link.invalid_code", "Invalid code. Please check and try again.")}
            
            source_platform, source_identifier, expires_at = result
            
            # Check if expired
            if datetime.now() > expires_at:
                cursor.execute("DELETE FROM link_codes WHERE code = %s", (code,))
                return {"error": self._translate(t, "commands.link.code_expired", "Code has expired. Please generate a new one.")}
            
            # Check if trying to link the same account
            if source_platform == target_platform and source_identifier == target_identifier:
                return {"error": self._translate(t, "commands.link.cannot_link_self", "Cannot link an account to itself.")}
            
            # Check if either account is already linked
            cursor.execute("""
                SELECT account_id FROM account_links
                WHERE (platform = %s AND identifier = %s)
                   OR (platform = %s AND identifier = %s)
            """, (source_platform, source_identifier, target_platform, target_identifier))
            
            existing_links = cursor.fetchall()
            
            if existing_links:
                # Both accounts should share the same account_id
                account_ids = set(link[0] for link in existing_links)
                
                if len(account_ids) > 1:
                    return {
                        "error": self._translate(
                            t,
                            "commands.link.already_linked_different_ids",
                            "Cannot link accounts that are already linked to different account IDs.",
                        )
                    }
                
                account_id = account_ids.pop()
                
                # Add the missing link(s)
                existing_platforms = {}
                cursor.execute("""
                    SELECT platform, identifier FROM account_links
                    WHERE account_id = %s
                """, (account_id,))
                for plat, ident in cursor.fetchall():
                    existing_platforms[plat] = ident
                
                # Add source if not exists
                if source_platform not in existing_platforms:
                    # Check if this (platform, identifier) already exists
                    cursor.execute("""
                        SELECT account_id FROM account_links
                        WHERE platform = %s AND identifier = %s
                    """, (source_platform, source_identifier))
                    existing = cursor.fetchone()
                    if not existing:
                        cursor.execute("""
                            INSERT INTO account_links (account_id, platform, identifier)
                            VALUES (%s, %s, %s)
                        """, (account_id, source_platform, source_identifier))
                
                # Add target if not exists
                if target_platform not in existing_platforms:
                    # Check if this (platform, identifier) already exists
                    cursor.execute("""
                        SELECT account_id FROM account_links
                        WHERE platform = %s AND identifier = %s
                    """, (target_platform, target_identifier))
                    existing = cursor.fetchone()
                    if not existing:
                        cursor.execute("""
                            INSERT INTO account_links (account_id, platform, identifier)
                            VALUES (%s, %s, %s)
                        """, (account_id, target_platform, target_identifier))
            else:
                # Neither account is linked, create new account_id
                # Check if source already exists
                cursor.execute("""
                    SELECT account_id FROM account_links
                    WHERE platform = %s AND identifier = %s
                """, (source_platform, source_identifier))
                existing_source = cursor.fetchone()
                
                if existing_source:
                    account_id = existing_source[0]
                else:
                    # Generate a new account_id (get max + 1)
                    cursor.execute("SELECT COALESCE(MAX(account_id), 0) + 1 FROM account_links")
                    account_id = cursor.fetchone()[0]
                    
                    # Insert source account
                    cursor.execute("""
                        INSERT INTO account_links (account_id, platform, identifier)
                        VALUES (%s, %s, %s)
                    """, (account_id, source_platform, source_identifier))
                
                # Check if target already exists
                cursor.execute("""
                    SELECT account_id FROM account_links
                    WHERE platform = %s AND identifier = %s
                """, (target_platform, target_identifier))
                existing_target = cursor.fetchone()
                
                if not existing_target:
                    # Link the target account with the same account_id
                    cursor.execute("""
                        INSERT INTO account_links (account_id, platform, identifier)
                        VALUES (%s, %s, %s)
                    """, (account_id, target_platform, target_identifier))
            
            # Delete the used code
            cursor.execute("DELETE FROM link_codes WHERE code = %s", (code,))
            
            # Migrate fishing data if needed
            self._migrate_fishing_data(cursor, source_platform, source_identifier, 
                                       target_platform, target_identifier)
        
        return {
            "success": True,
            "message": self._translate(
                t,
                "commands.link.success",
                "Successfully linked {target_platform} user \"{target_identifier}\" to {source_platform} user \"{source_identifier}\".",
                target_platform=target_platform,
                target_identifier=target_identifier,
                source_platform=source_platform,
                source_identifier=source_identifier,
            ),
            "account_id": account_id
        }
    
    def _migrate_fishing_data(self, cursor, source_platform: str, source_identifier: str,
                             target_platform: str, target_identifier: str):
        """
        Migrate fishing data from CS2 to Discord if Discord account is empty.
        
        :param cursor: Database cursor
        :param source_platform: Platform where code was generated
        :param source_identifier: User identifier on source platform
        :param target_platform: Platform where code was used
        :param target_identifier: User identifier on target platform
        """
        # Determine which account is CS2 and which is Discord
        cs2_user = None
        discord_user = None
        
        if source_platform == 'cs2':
            cs2_user = source_identifier
            discord_user = target_identifier if target_platform == 'discord' else None
        elif target_platform == 'cs2':
            cs2_user = target_identifier
            discord_user = source_identifier if source_platform == 'discord' else None
        elif source_platform == 'discord':
            discord_user = source_identifier
        elif target_platform == 'discord':
            discord_user = target_identifier
        
        # Only migrate if we have both CS2 and Discord accounts
        if not cs2_user or not discord_user:
            return
        
        # Check if Discord account has any fishing data
        cursor.execute("""
            SELECT COUNT(*) FROM caught_fish WHERE user_id = %s
        """, (discord_user,))
        discord_fish_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM user_inventory WHERE user_id = %s
        """, (discord_user,))
        discord_inventory_count = cursor.fetchone()[0]
        
        # If Discord account is empty, migrate from CS2; otherwise merge
        if discord_fish_count == 0 and discord_inventory_count == 0:
            # Simple migration - just update user_id from CS2 to Discord
            cursor.execute("""
                UPDATE caught_fish
                SET user_id = %s
                WHERE user_id = %s
            """, (discord_user, cs2_user))
            
            cursor.execute("""
                UPDATE user_inventory
                SET user_id = %s
                WHERE user_id = %s
            """, (discord_user, cs2_user))
            
            cursor.execute("""
                UPDATE user_balances
                SET user_id = %s
                WHERE user_id = %s
            """, (discord_user, cs2_user))
            
            cursor.execute("""
                UPDATE status_effects
                SET user_id = %s
                WHERE user_id = %s
            """, (discord_user, cs2_user))
        else:
            # Merge data from both accounts
            # Merge caught fish - just update user_id
            cursor.execute("""
                UPDATE caught_fish
                SET user_id = %s
                WHERE user_id = %s
            """, (discord_user, cs2_user))
            
            # Merge inventory - combine quantities for same items
            cursor.execute("""
                INSERT INTO user_inventory (user_id, item_name, item_data, quantity)
                SELECT %s, item_name, item_data, quantity
                FROM user_inventory
                WHERE user_id = %s
                ON CONFLICT (user_id, item_name) 
                DO UPDATE SET quantity = user_inventory.quantity + EXCLUDED.quantity
            """, (discord_user, cs2_user))
            
            # Delete old CS2 inventory entries
            cursor.execute("""
                DELETE FROM user_inventory WHERE user_id = %s
            """, (cs2_user,))
            
            # Merge balance - add CS2 balance to Discord balance
            cursor.execute("""
                INSERT INTO user_balances (user_id, balance)
                SELECT %s, balance
                FROM user_balances
                WHERE user_id = %s
                ON CONFLICT (user_id)
                DO UPDATE SET balance = user_balances.balance + EXCLUDED.balance
            """, (discord_user, cs2_user))
            
            # Delete old CS2 balance
            cursor.execute("""
                DELETE FROM user_balances WHERE user_id = %s
            """, (cs2_user,))
            
            # Merge status effects - keep longest duration ones
            cursor.execute("""
                INSERT INTO status_effects (user_id, effect_type, expires_at)
                SELECT %s, effect_type, expires_at
                FROM status_effects
                WHERE user_id = %s
                ON CONFLICT (user_id, effect_type)
                DO UPDATE SET expires_at = GREATEST(status_effects.expires_at, EXCLUDED.expires_at)
            """, (discord_user, cs2_user))
            
            # Delete old CS2 status effects
            cursor.execute("""
                DELETE FROM status_effects WHERE user_id = %s
            """, (cs2_user,))
    
    def get_linked_accounts(self, platform: str, identifier: str) -> list:
        """
        Get all linked accounts for a user.
        
        :param platform: The platform
        :param identifier: The user identifier
        :return: List of (platform, identifier) tuples
        """
        with DatabaseConnection() as cursor:
            # Find the account_id
            cursor.execute("""
                SELECT account_id FROM account_links
                WHERE platform = %s AND identifier = %s
            """, (platform, identifier))
            
            result = cursor.fetchone()
            
            if not result:
                return []
            
            account_id = result[0]
            
            # Get all linked accounts
            cursor.execute("""
                SELECT platform, identifier
                FROM account_links
                WHERE account_id = %s
            """, (account_id,))
            
            return cursor.fetchall()
    
    def get_unified_user_id(self, platform: str, identifier: str) -> str:
        """
        Get the unified user ID (primary identifier) for cross-platform operations.
        Returns the original identifier if no link exists.
        
        :param platform: The platform
        :param identifier: The user identifier
        :return: The unified user ID (account_id) or original identifier
        """
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT account_id FROM account_links
                WHERE platform = %s AND identifier = %s
            """, (platform, identifier))
            
            result = cursor.fetchone()
            
            if result:
                return f"account_{result[0]}"
            
            return identifier
    
    def get_preferred_identifier(self, platform: str, identifier: str) -> str:
        """
        Get the preferred identifier for a user (Discord if linked, otherwise original).
        This ensures CS2 users access their Discord fishing data when linked.
        
        :param platform: The platform
        :param identifier: The user identifier
        :return: The preferred identifier (Discord username if linked, otherwise original)
        """
        with DatabaseConnection() as cursor:
            # Find the account_id for this user
            cursor.execute("""
                SELECT account_id FROM account_links
                WHERE platform = %s AND identifier = %s
            """, (platform, identifier))
            
            result = cursor.fetchone()
            
            if not result:
                # No linked account, return original identifier
                return identifier
            
            account_id = result[0]
            
            # Look for a Discord account in this link group
            cursor.execute("""
                SELECT identifier FROM account_links
                WHERE account_id = %s AND platform = 'discord'
            """, (account_id,))
            
            discord_result = cursor.fetchone()
            
            if discord_result:
                # Return Discord identifier if it exists
                return discord_result[0]
            
            # No Discord account linked, return original identifier
            return identifier
    
    def cleanup_expired_codes(self):
        """Remove expired linking codes."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                DELETE FROM link_codes
                WHERE expires_at < NOW()
            """)


# Register the module
module_registry.register("account_linking", AccountLinking)

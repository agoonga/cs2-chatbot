-- Initialize PostgreSQL database schema for fishing bot

-- User balances table
CREATE TABLE IF NOT EXISTS user_balances (
    user_id TEXT PRIMARY KEY,
    balance NUMERIC(12, 2) NOT NULL DEFAULT 0
);

-- Caught fish table
CREATE TABLE IF NOT EXISTS caught_fish (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    weight NUMERIC(10, 2) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    bait INTEGER DEFAULT 0
);

-- Create index on user_id for faster queries
CREATE INDEX IF NOT EXISTS idx_caught_fish_user_id ON caught_fish(user_id);

-- Trophy fish table
CREATE TABLE IF NOT EXISTS trophy_fish (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    weight NUMERIC(10, 2) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on user_id for faster queries
CREATE INDEX IF NOT EXISTS idx_trophy_fish_user_id ON trophy_fish(user_id);

-- User inventory table
CREATE TABLE IF NOT EXISTS user_inventory (
    user_id TEXT NOT NULL,
    item_name TEXT NOT NULL,
    item_data TEXT DEFAULT '{}',
    quantity INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, item_name)
);

-- Status effects table
CREATE TABLE IF NOT EXISTS status_effects (
    user_id TEXT NOT NULL,
    effect_name TEXT NOT NULL,
    expiration_time BIGINT NOT NULL,
    PRIMARY KEY (user_id, effect_name)
);

-- Create index on expiration_time for cleanup queries
CREATE INDEX IF NOT EXISTS idx_status_effects_expiration ON status_effects(expiration_time);

-- Account linking table
CREATE TABLE IF NOT EXISTS account_links (
    account_id INTEGER NOT NULL,
    platform TEXT NOT NULL,
    identifier TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (platform, identifier),
    UNIQUE (platform, identifier)
);

-- Create index on account_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_account_links_account_id ON account_links(account_id);

-- Link codes table (for temporary linking codes)
CREATE TABLE IF NOT EXISTS link_codes (
    code TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    identifier TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- Create index on expires_at for cleanup
CREATE INDEX IF NOT EXISTS idx_link_codes_expires_at ON link_codes(expires_at);

-- Daily quests table
CREATE TABLE IF NOT EXISTS daily_quests (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    quest_id TEXT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP
);

-- Create index on user_id and assigned_at for faster queries
CREATE INDEX IF NOT EXISTS idx_daily_quests_user_id ON daily_quests(user_id, assigned_at DESC);

-- Quest completions table (for regular quests)
CREATE TABLE IF NOT EXISTS quest_completions (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    quest_id TEXT NOT NULL,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on user_id and quest_id for tracking
CREATE INDEX IF NOT EXISTS idx_quest_completions_user_quest ON quest_completions(user_id, quest_id);

-- Grant permissions (if needed)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bot_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bot_user;

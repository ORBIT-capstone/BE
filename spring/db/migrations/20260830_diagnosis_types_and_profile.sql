-- Existing MySQL database: run before deploying the new application.
-- No rows are deleted. Existing diagnoses remain RETIREMENT_ASSET.
-- Column additions are guarded so this also works after Hibernate ddl-auto=update.

SET @ddl = IF(
    EXISTS(SELECT 1 FROM information_schema.columns
           WHERE table_schema = DATABASE() AND table_name = 'diagnoses' AND column_name = 'diagnosis_type'),
    'SELECT 1',
    'ALTER TABLE diagnoses ADD COLUMN diagnosis_type VARCHAR(40) NOT NULL DEFAULT ''RETIREMENT_ASSET'''
);
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

SET @ddl = IF(
    EXISTS(SELECT 1 FROM information_schema.columns
           WHERE table_schema = DATABASE() AND table_name = 'users' AND column_name = 'monthly_income'),
    'SELECT 1',
    'ALTER TABLE users ADD COLUMN monthly_income BIGINT NULL'
);
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

SET @ddl = IF(
    EXISTS(SELECT 1 FROM information_schema.columns
           WHERE table_schema = DATABASE() AND table_name = 'users' AND column_name = 'access_token_hash'),
    'SELECT 1',
    'ALTER TABLE users ADD COLUMN access_token_hash VARCHAR(512) NULL'
);
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

-- Employee/scenario results do not have a top-level readiness status.
-- Hibernate schema update does not reliably relax existing NOT NULL constraints.
ALTER TABLE diagnoses MODIFY COLUMN status VARCHAR(20) NULL;

SET @ddl = IF(
    EXISTS(SELECT 1 FROM information_schema.columns
           WHERE table_schema = DATABASE() AND table_name = 'users' AND column_name = 'asset'),
    'SELECT 1',
    'ALTER TABLE users ADD COLUMN asset BIGINT NULL'
);
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

SET @ddl = IF(
    EXISTS(SELECT 1 FROM information_schema.columns
           WHERE table_schema = DATABASE() AND table_name = 'users' AND column_name = 'monthly_expenses'),
    'SELECT 1',
    'ALTER TABLE users ADD COLUMN monthly_expenses BIGINT NULL'
);
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

SET @ddl = IF(
    EXISTS(SELECT 1 FROM information_schema.columns
           WHERE table_schema = DATABASE() AND table_name = 'users' AND column_name = 'current_years'),
    'SELECT 1',
    'ALTER TABLE users ADD COLUMN current_years INT NULL'
);
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

-- Existing MySQL database: run before deploying the monthly pension profile field.
-- Safe to run after Hibernate ddl-auto=update. Existing users keep NULL.
SET @ddl = IF(
    EXISTS(SELECT 1 FROM information_schema.columns
           WHERE table_schema = DATABASE() AND table_name = 'users' AND column_name = 'monthly_pension'),
    'SELECT 1',
    'ALTER TABLE users ADD COLUMN monthly_pension BIGINT NULL'
);
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

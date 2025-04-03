-- Drop test_json and test_jsonb tables migration
-- This migration removes the test_json and test_jsonb tables which are no longer needed

-- First, check if the tables exist and drop them
DO $$
BEGIN
    -- Check and drop test_json table
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'test_json') THEN
        RAISE NOTICE 'Dropping test_json table...';
        DROP TABLE IF EXISTS test_json CASCADE;
        RAISE NOTICE 'Table test_json has been dropped successfully.';
    ELSE
        RAISE NOTICE 'Table test_json does not exist. No action needed.';
    END IF;
    
    -- Check and drop test_jsonb table
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'test_jsonb') THEN
        RAISE NOTICE 'Dropping test_jsonb table...';
        DROP TABLE IF EXISTS test_jsonb CASCADE;
        RAISE NOTICE 'Table test_jsonb has been dropped successfully.';
    ELSE
        RAISE NOTICE 'Table test_jsonb does not exist. No action needed.';
    END IF;
END
$$; 
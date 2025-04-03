-- Drop compressed_data table migration
-- This migration removes the compressed_data table which is no longer needed

-- First, check if the table exists
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'compressed_data') THEN
        -- Display a notice
        RAISE NOTICE 'Dropping compressed_data table...';
        
        -- Drop the table
        DROP TABLE IF EXISTS compressed_data;
        
        RAISE NOTICE 'Table compressed_data has been dropped successfully.';
    ELSE
        RAISE NOTICE 'Table compressed_data does not exist. No action needed.';
    END IF;
END
$$; 
-- =====================================================
-- SPACE42 HR AGENT - SETUP SCHEMA
-- Run this in Supabase SQL Editor to initialize/update the database
-- =====================================================

-- 1. ENABLE VECTOR EXTENSION
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. SETUP EMBEDDINGS TABLE (Optimized for Groq/FastEmbed 384d)
-- If table exists with wrong dimension, you might need to drop it first or alter it.
-- This script assumes we are enforcing 384 dimensions.
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT,
    source_type VARCHAR(50),
    source_id UUID,
    metadata JSONB,
    embedding vector(384),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Ensure correct dimension if table already existed
DO $$
BEGIN
    BEGIN
        ALTER TABLE embeddings ALTER COLUMN embedding TYPE vector(384);
    EXCEPTION
        WHEN OTHERS THEN
            NULL; -- Ignore if column doesn't exist or other issues (handled manually if needed)
    END;
END $$;

-- 3. SEARCH FUNCTION (Similarity Search)
CREATE OR REPLACE FUNCTION match_embeddings(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 5,
    filter_source_types text[] DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    content text,
    source_type varchar(50),
    source_id uuid,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.content,
        e.source_type,
        e.source_id,
        e.metadata,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM embeddings e
    WHERE 
        (filter_source_types IS NULL OR e.source_type = ANY(filter_source_types))
        AND 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Grant permissions
GRANT EXECUTE ON FUNCTION match_embeddings TO anon, authenticated, service_role;

-- 4. CONVERSATIONS TABLE UPDATES
-- Ensure all necessary columns exist for the chat features
ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS candidate_id UUID REFERENCES candidates(id),
ADD COLUMN IF NOT EXISTS conversation_type VARCHAR(50) DEFAULT 'general',
ADD COLUMN IF NOT EXISTS title VARCHAR(255);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_conversations_candidate_id ON conversations(candidate_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

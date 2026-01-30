-- Migration: Add Model Metadata Columns
-- Purpose: Enable model-level traceability by logging provider, name, version, deployment ID, temperature, and safety mode
-- Date: 2026-01-30
-- Status: Ready to apply

-- Add model metadata columns to conversation_audit_logs table
-- These columns are nullable to maintain backward compatibility with existing logs

ALTER TABLE conversation_audit_logs
ADD COLUMN model_provider TEXT,
ADD COLUMN model_name TEXT,
ADD COLUMN model_version TEXT,
ADD COLUMN deployment_id TEXT,
ADD COLUMN temperature TEXT,
ADD COLUMN safety_mode TEXT,
ADD COLUMN model_config JSONB;

-- Create indexes for common metadata queries (optional, for performance)
-- Uncomment if you anticipate frequent filtering by model_provider or model_name
-- CREATE INDEX idx_conversation_logs_model_provider ON conversation_audit_logs(model_provider);
-- CREATE INDEX idx_conversation_logs_model_name ON conversation_audit_logs(model_name);
-- CREATE INDEX idx_conversation_logs_deployment_id ON conversation_audit_logs(deployment_id);

-- Verify the columns were added
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'conversation_audit_logs' 
-- ORDER BY ordinal_position;

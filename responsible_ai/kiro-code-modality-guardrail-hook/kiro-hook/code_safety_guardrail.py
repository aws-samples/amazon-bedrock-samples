#!/usr/bin/env python3
"""
Kiro Agent Guardrail Validator
Validates code generation against Bedrock Guardrails
"""
import boto3
import sys
import json
import os
from datetime import datetime
from pathlib import Path

# Configuration - Updated with your guardrail details
REGION = os.environ.get('AWS_REGION', 'us-east-1')
GUARDRAIL_ID = os.environ.get('BEDROCK_GUARDRAIL_ID', 'h7t5aokrpe1n')
GUARDRAIL_VERSION = os.environ.get('BEDROCK_GUARDRAIL_VERSION', 'DRAFT')

# Log file configuration
LOG_DIR = Path('.kiro/hooks/logs')
LOG_FILE = LOG_DIR / 'guardrail_validation.log'

def log_message(message, level="INFO"):
    """Write log message to file and stderr"""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    
    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Write to log file
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry)
    
    # Also write to stderr for immediate visibility
    sys.stderr.write(log_entry)
    sys.stderr.flush()

def validate_content(content):
    """Validate content against Bedrock Guardrails"""
    log_message("Starting guardrail validation")
    log_message(f"Content length: {len(content)} characters")
    
    try:
        bedrock_runtime = boto3.client('bedrock-runtime', region_name=REGION)
        log_message(f"Using guardrail: {GUARDRAIL_ID} (version: {GUARDRAIL_VERSION})")
        
        response = bedrock_runtime.apply_guardrail(
            guardrailIdentifier=GUARDRAIL_ID,
            guardrailVersion=GUARDRAIL_VERSION,
            source='OUTPUT',  # Validate agent output
            content=[{"text": {"text": content}}]
        )
        
        action = response.get('action')
        log_message(f"Guardrail action: {action}")
        
        if action == 'GUARDRAIL_INTERVENED':
            log_message("❌ GUARDRAIL BLOCKED: Harmful content detected!", "ERROR")
            
            # Extract violation details
            violations = []
            if 'assessments' in response and response['assessments']:
                assessment = response['assessments'][0]
                
                if 'contentPolicy' in assessment:
                    for f in assessment['contentPolicy'].get('filters', []):
                        violation = f"Content: {f.get('type')}"
                        violations.append(violation)
                        log_message(f"  - {violation}", "ERROR")
                
                if 'topicPolicy' in assessment:
                    for t in assessment['topicPolicy'].get('topics', []):
                        violation = f"Topic: {t.get('name')}"
                        violations.append(violation)
                        log_message(f"  - {violation}", "ERROR")
                
                if 'sensitiveInformationPolicy' in assessment:
                    si = assessment['sensitiveInformationPolicy']
                    for p in si.get('piiEntities', []):
                        violation = f"PII: {p.get('type')}"
                        violations.append(violation)
                        log_message(f"  - {violation}", "ERROR")
            
            if violations:
                log_message(f"Total violations: {len(violations)}", "ERROR")
            
            return False
        else:
            log_message("✅ Content validated successfully - No violations detected", "SUCCESS")
            return True
            
    except Exception as e:
        log_message(f"⚠️ Validation error: {str(e)}", "ERROR")
        log_message("Failing open - allowing content to pass", "WARNING")
        # On error, allow content to pass (fail open)
        return True

if __name__ == "__main__":
    log_message("=" * 80)
    log_message("Guardrail hook triggered")
    
    # Read content from stdin
    content = sys.stdin.read()
    
    if not content.strip():
        log_message("⚠️ No content to validate - stdin is empty", "WARNING")
        sys.exit(0)
    
    log_message(f"Received content from stdin ({len(content)} chars)")
    
    if validate_content(content):
        log_message("Validation result: PASSED", "SUCCESS")
        log_message("=" * 80)
        sys.exit(0)  # Success - content is safe
    else:
        log_message("Validation result: BLOCKED", "ERROR")
        log_message("=" * 80)
        sys.exit(1)  # Blocked - content is harmful

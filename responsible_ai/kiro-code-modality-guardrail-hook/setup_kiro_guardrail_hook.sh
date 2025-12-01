#!/bin/bash
# Setup script for Kiro Agent Guardrail Hook

echo "🛡️  Kiro Agent Guardrail Hook Setup"
echo "===================================="
echo ""

# Check if guardrail ID is provided
if [ -z "$1" ]; then
    echo "❌ Error: Guardrail ID required"
    echo ""
    echo "Usage: ./setup_kiro_guardrail_hook.sh <GUARDRAIL_ID> [VERSION] [REGION]"
    echo ""
    echo "Example:"
    echo "  ./setup_kiro_guardrail_hook.sh abc123xyz DRAFT us-east-1"
    echo ""
    echo "First, run the notebook to create your guardrail:"
    echo "  responsible_ai/bedrock-guardrails/kiro_agent_guardrails_demo.ipynb"
    exit 1
fi

GUARDRAIL_ID=$1
GUARDRAIL_VERSION=${2:-DRAFT}
AWS_REGION=${3:-us-east-1}

echo "Configuration:"
echo "  Guardrail ID: $GUARDRAIL_ID"
echo "  Version: $GUARDRAIL_VERSION"
echo "  Region: $AWS_REGION"
echo ""

# Set environment variables
export BEDROCK_GUARDRAIL_ID="$GUARDRAIL_ID"
export BEDROCK_GUARDRAIL_VERSION="$GUARDRAIL_VERSION"
export AWS_REGION="$AWS_REGION"

# Add to shell profile
SHELL_PROFILE=""
if [ -f "$HOME/.zshrc" ]; then
    SHELL_PROFILE="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_PROFILE="$HOME/.bashrc"
fi

if [ -n "$SHELL_PROFILE" ]; then
    echo "📝 Adding environment variables to $SHELL_PROFILE"
    
    # Remove old entries if they exist
    sed -i.bak '/BEDROCK_GUARDRAIL_ID/d' "$SHELL_PROFILE"
    sed -i.bak '/BEDROCK_GUARDRAIL_VERSION/d' "$SHELL_PROFILE"
    
    # Add new entries
    echo "" >> "$SHELL_PROFILE"
    echo "# Kiro Agent Guardrail Configuration" >> "$SHELL_PROFILE"
    echo "export BEDROCK_GUARDRAIL_ID=\"$GUARDRAIL_ID\"" >> "$SHELL_PROFILE"
    echo "export BEDROCK_GUARDRAIL_VERSION=\"$GUARDRAIL_VERSION\"" >> "$SHELL_PROFILE"
    echo "export AWS_REGION=\"$AWS_REGION\"" >> "$SHELL_PROFILE"
    
    echo "✅ Environment variables added to $SHELL_PROFILE"
else
    echo "⚠️  Could not find shell profile. Please set environment variables manually:"
    echo "   export BEDROCK_GUARDRAIL_ID=\"$GUARDRAIL_ID\""
    echo "   export BEDROCK_GUARDRAIL_VERSION=\"$GUARDRAIL_VERSION\""
    echo "   export AWS_REGION=\"$AWS_REGION\""
fi

# Test the script
echo ""
echo "🧪 Testing guardrail validation script..."
if command -v python3 &> /dev/null; then
    echo "Test content" | python3 ../../.kiro/hooks/code_safety_guardrail.py
    if [ $? -eq 0 ]; then
        echo "✅ Validation script is working"
    else
        echo "⚠️  Script executed but check for errors above"
    fi
else
    echo "❌ Python 3 not found. Please install Python 3."
    exit 1
fi

# Check boto3
echo ""
echo "📦 Checking dependencies..."
python3 -c "import boto3" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ boto3 is installed"
else
    echo "❌ boto3 not found. Installing..."
    pip3 install boto3
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Restart your terminal or run: source $SHELL_PROFILE"
echo "2. Open Kiro Command Palette (Cmd+Shift+P)"
echo "3. Search for 'Open Kiro Hook UI'"
echo "4. Create a new hook with these settings:"
echo "   - Name: Code Safety Guardrail"
echo "   - Trigger: When agent execution completes"
echo "   - Command: python3 .kiro/hooks/code_safety_guardrail.py"
echo "   - Input: Agent message content"
echo ""
echo "Or view existing hooks in the Kiro Explorer → Agent Hooks section"
echo ""

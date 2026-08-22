#!/usr/bin/env python3
import os
import subprocess
import sys

class ClaudeSetup:
    """Class to handle Claude Code setup and execution."""
    
    def install_claude_code(self):
        """Install Claude Code using npm."""
        print("Installing Claude Code...")
        result = subprocess.run(["npm", "install", "-g", "@anthropic-ai/claude-code"], 
                               capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error installing Claude Code: {result.stderr}")
            sys.exit(1)
        print("Claude Code installed successfully.")
    
    def configure_environment(self, model="sonnet"):
        """Configure environment variables for Bedrock with Claude models.
        
        Args:
            model: Either "sonnet" for Claude 3.7 Sonnet or "haiku" for Claude 3.5 Haiku
        """
        print("Configuring environment variables...")
        os.environ["CLAUDE_CODE_USE_BEDROCK"] = "1"
        
        if model == "haiku":
            os.environ["ANTHROPIC_MODEL"] = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
            os.environ["ANTHROPIC_SMALL_FAST_MODEL"] = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
            print(f"Using Claude 3.5 Haiku model: {os.environ['ANTHROPIC_MODEL']}")
        else:
            os.environ["ANTHROPIC_MODEL"] = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
            print(f"Using Claude 3.7 Sonnet model: {os.environ['ANTHROPIC_MODEL']}")
        
        os.environ["DISABLE_PROMPT_CACHING"] = "1"
        print("To disable caching: export DISABLE_PROMPT_CACHING=true")
        print("To enable caching (if you have access): unset DISABLE_PROMPT_CACHING")
    
    def launch_claude(self):
        """Launch Claude Code with the configured environment."""
        print("Launching Claude Code...")
        subprocess.run(["claude"], env=os.environ)
    
    def run_setup(self):
        """Run the complete setup process."""
        self.install_claude_code()
        self.configure_environment()
        self.launch_claude()

def simulate_user_chat():
    """Simulate a user chat session that executes the setup with a friendly interface."""
    print("\n" + "="*60)
    print("🤖 Welcome to Claude Code Setup Assistant 🤖".center(60))
    print("="*60)
    
    print("\n👋 Hi there! I'll help you set up Claude Code with AWS Bedrock.")
    print("   This assistant will guide you through the installation and configuration process.")
    
    # Ask if user wants to proceed with installation
    print("\n📦 First, we need to install Claude Code.")
    proceed = input("   Would you like to proceed with installation? (y/n, default: y): ").lower() or "y"
    
    if proceed != "y":
        print("\n❌ Setup cancelled. You can run this script again when you're ready.")
        return
    
    setup = ClaudeSetup()
    setup.install_claude_code()
    
    # Ask user about model selection with more details
    print("\n🧠 Model Selection:")
    print("   Claude offers different models with varying capabilities:")
    print("   1. Claude 3.7 Sonnet - More powerful, better for complex tasks")
    print("   2. Claude 3.5 Haiku - Faster, great for simpler tasks")
    
    model_choice = input("\n   Which model would you prefer? (1/2, default: 1): ") or "1"
    
    if model_choice == "2":
        model = "haiku"
        model_name = "Claude 3.5 Haiku"
    else:
        model = "sonnet"
        model_name = "Claude 3.7 Sonnet"
    
    print(f"\n✅ Selected {model_name}")
    setup.configure_environment(model)
    
    # Ask user about caching preferences with explanation
    print("\n🔄 Prompt Caching:")
    print("   Caching can improve performance by storing previous responses.")
    print("   Note: This feature requires special access.")
    print("   1. Enable caching (if you have access)")
    print("   2. Disable caching")
    
    cache_choice = input("\n   What's your preference? (1/2, default: 2): ") or "2"
    
    if cache_choice == "1":
        if "DISABLE_PROMPT_CACHING" in os.environ:
            del os.environ["DISABLE_PROMPT_CACHING"]
        print("\n✅ Prompt caching has been enabled.")
    else:
        os.environ["DISABLE_PROMPT_CACHING"] = "true"
        print("\n✅ Prompt caching has been disabled.")
    
    # Final confirmation before launch
    print("\n🚀 Ready to launch Claude Code!")
    launch = input("   Would you like to launch it now? (y/n, default: y): ").lower() or "y"
    
    if launch == "y":
        print("\n🔄 Launching Claude Code...")
        setup.launch_claude()
        print(f"\n✨ Success! Claude Code is now running with {model_name} on AWS Bedrock.")
    else:
        print("\n👍 Setup complete! You can launch Claude Code later with the 'claude' command.")
    
    print("\n💡 Tip: You can reconfigure these settings by running this script again.")
    print("\n" + "="*60)
    print("Thank you for using Claude Code Setup Assistant!".center(60))
    print("="*60 + "\n")

if __name__ == "__main__":
    simulate_user_chat()
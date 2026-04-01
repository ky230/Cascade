import argparse
import asyncio
import os
from dotenv import load_dotenv
from cascade.core.agent import Agent

def main():
    load_dotenv()
    default_provider = os.getenv("CASCADE_DEFAULT_PROVIDER", "openai")
    default_model = os.getenv("CASCADE_DEFAULT_MODEL", "gpt-4o")

    parser = argparse.ArgumentParser(description="Cascade: CLI Agentic Orchestrator for HEP")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    chat_parser = subparsers.add_parser("chat", help="Start an interactive chat session.")
    chat_parser.add_argument("--provider", type=str, default=default_provider)
    chat_parser.add_argument("--model", type=str, default=default_model)

    args = parser.parse_args()

    if args.command == "chat":
        asyncio.run(interactive_chat(args.provider, args.model))

async def interactive_chat(provider: str, model: str):
    print(f"🌀 Welcome to Cascade! (Model: {provider}/{model})")
    print("Type 'exit' or 'quit' to end.\n")
    
    agent = Agent(provider=provider, model_name=model)
    
    while True:
        try:
            user_input = input("You> ")
            if user_input.lower() in ["exit", "quit"]:
                print("Exiting Cascade. Goodbye!")
                break
            if not user_input.strip():
                continue
                
            response = await agent.chat(user_input)
            print(f"\nCascade> {response}\n")
            
        except KeyboardInterrupt:
            print("\nExiting Cascade. Goodbye!")
            break
        except Exception as e:
            print(f"\n[Error] {str(e)}")

if __name__ == "__main__":
    main()

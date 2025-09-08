import anthropic
import os
import time
import src.tools as tools


def chat_with_claude():
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    conversation = []

    print("Chat with Claude (Type Ctrl+C to exit)")

    try:
        while True:
            user_input = input("\nYou: ")
            conversation.append({"role": "user", "content": user_input})

            while True:

                retry_delay = 1
                while True:
                    try:
                        response = client.messages.create(
                            model="claude-3-haiku-20240307",
                            max_tokens=512,
                            messages=conversation,
                            tools=tools.TOOLS_SCHEME,
                            tool_choice={"type": "auto"},
                        )
                        break
                    except anthropic.APIConnectionError as e:
                        print(f"Connection error: {e}")
                        time.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, 60)

                    except anthropic.APIStatusError as e:
                        if e.status_code == 429:
                            retry_after = e.response.headers.get(
                                "retry-after", retry_delay
                            )
                            reset_time = e.response.headers.get(
                                "anthropic-ratelimit-requests-reset"
                            )

                            try:
                                retry_after = float(retry_after)
                            except (TypeError, ValueError):
                                retry_after = retry_delay

                            print(
                                f"Rate limited. Retry after: {retry_after}s | Reset at: {reset_time}"
                            )
                            time.sleep(retry_after)
                            continue

                        else:
                            print(f"API error {e.status_code}: {e.message}")
                            raise

                claude_response = response.content
                conversation.append({"role": "assistant", "content": claude_response})

                tool_uses = [c for c in claude_response if c.type == "tool_use"]
                if not tool_uses:
                    text_response = response.content[0]
                    print(f"\nClaude: {text_response}")
                    break

                tool_results = []
                for tool_use in tool_uses:
                    result, error = tools.tool_dispatcher(tool_use.name, tool_use.input)
                    output = f"Error: {error}" if error else str(result)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": output,
                        }
                    )

                conversation.append({"role": "user", "content": tool_results})
                print("↳ Tool used. Processing...")

    except KeyboardInterrupt:
        print("\nExiting chat...")

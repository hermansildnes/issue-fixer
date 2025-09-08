import anthropic
from anthropic.types import MessageParam
import os
from dotenv import load_dotenv, find_dotenv
import requests
import time
from git import Repo
import src.tools as tools


def get_github_issues(username: str, repo_name: str):
    headers = {
        "Authorization": f'Token {os.environ.get("GITHUB_API_KEY")}',
        "Accept": "application/vnd.github.v3+json",
    }

    url = f"https://api.github.com/repos/{username}/{repo_name}/issues"
    params = {"state": "open", "per_page": 100, "page": 1}
    issues = []

    while True:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if not data:
            break
        issues.extend([issue for issue in data if "pull_request" not in issue])
        if "next" not in response.links:
            break

        params["page"] += 1
    return issues


def claude_suggest_fix(
    issue, repo_url, repo_path, username, token, tools_scheme, model
):
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    if not os.path.exists(repo_path):
        authed_url = repo_url.replace("https://", f"https://{username}:{token}@")
        Repo.clone_from(authed_url, repo_path)

    repo = Repo(repo_path)
    origin = repo.remote("origin")

    repo.git.checkout("main")
    repo.git.fetch("origin")
    repo.git.reset("--hard", "origin/main")
    repo.git.clean("-fd")

    branch_name = f"fix-issue-{issue['number']}"

    if branch_name in repo.heads:
        print(f"Branch {branch_name} exists - reusing")
        repo.git.checkout(branch_name)
        repo.git.reset("--hard", "origin/main")
    else:
        print(f"Creating new branch {branch_name}")
        repo.git.checkout("-b", branch_name)

    conversation = [
        MessageParam(
            role="user",
            content=f"""Fix this GitHub issue in the cloned repository:

            Title: {issue['title']}
            Description: {issue['body']}

            Follow these rules:
                1. **Search First**  
                Always use find_code_patterns before reading files  
                Example good pattern:  
                - Search for \"def calculate_risk\"  
                - Read only matched lines from search results  

                2. **Minimal Reading**  
                Never read entire files unless absolutely necessary  
                Prefer line ranges from search results  

                3. **Clean History**  
                After using a tool, summarize findings instead of keeping raw output  
                Example:  
                \"Found calculate_risk in src/risk.py (lines 45-48)\"  
                Instead of keeping full file content  

                Current token budget: 45000 remaining (refresh every minute)

            Follow these steps:
            1. Use find_code_patterns/read_code_snippet and if absolutely neccesarry, read_file to analyze the codebase
            2. Use edit_file to make necessary changes
            3. Return confirmation when done""",
        )
    ]

    try:
        while True:
            token_count = client.messages.count_tokens(
                model=model, system="You are a scientist", messages=conversation
            )

            print(f"Tokens for the conversation so far: {token_count.input_tokens}")

            if token_count.input_tokens > 50000:
                print("Token limit exceeded. Waiting for 60 seconds...")
                time.sleep(60)

            response = client.messages.create(
                model=model,
                max_tokens=1024,
                messages=conversation,
                tools=tools_scheme,
                tool_choice={"type": "auto"},
            )

            claude_response = response.content
            conversation.append(MessageParam(role="assistant", content=claude_response))

            tool_uses = [c for c in claude_response if c.type == "tool_use"]
            if not tool_uses:
                repo.git.add("--all")
                repo.index.commit(f"Fix #{issue['number']}: {issue['title']}")
                origin.push(branch_name)

                return {
                    "success": True,
                    "branch": branch_name,
                    "pr_url": f"{repo_url}/compare/main...{branch_name}?expand=1",
                }

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

            conversation.append(MessageParam(role="user", content=tool_results))

    except Exception as e:
        repo.git.reset("--hard")
        repo.git.checkout("main")
        repo.git.branch("-D", branch_name)
        return {"success": False, "error": str(e)}


def main():
    models = {
        "Haiku": "claude-3-5-haiku-20241022",
        "Sonnet": "claude-3-7-sonnet-20250219",
    }

    tools_scheme = tools.TOOLS_SCHEME

    load_dotenv(find_dotenv())

    username = os.environ.get("GITHUB_USERNAME")
    token = os.environ.get("GITHUB_TOKEN")
    repo_url = os.environ.get("GITHUB_REPO_URL")

    repo_path = os.path.join(os.getcwd(), "cloned_repo")

    issues = get_github_issues("your-github-username", "your-repo-name")

    for issue in issues:
        print(f"\nProcessing issue #{issue['number']}: {issue['title']}")
        result = claude_suggest_fix(
            issue, repo_url, repo_path, username, token, tools_scheme, models["Haiku"]
        )

        if result["success"]:
            print(f"Success! Created PR at: {result['pr_url']}")
        else:
            print(f"Failed: {result['error']}")

        print("Waiting for 20 seconds before processing the next issue...")
        time.sleep(20)


if __name__ == "__main__":
    main()

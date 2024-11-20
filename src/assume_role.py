import argparse
import subprocess
import json
import datetime
import sys


def assume_role(role_arn: str, session_name: str, session_tags: dict | None = None) -> None:
    """
    Assumes an AWS IAM role, optionally with session tags, and prints environment variables for sourcing.

    Args:
        role_arn (str): The ARN of the role to assume.
        session_name (str): A unique identifier for the session.
        session_tags (dict): Key-value pairs for session tags (optional).
    """
    try:
        # Base command
        command = [
            "aws", "sts", "assume-role",
            "--role-arn", role_arn,
            "--role-session-name", session_name
        ]

        # Add session tags if provided
        if session_tags:
            tag_string = ",".join(
                [f"Key={key},Value={value}" for key, value in session_tags.items()])
            command += ["--tags", tag_string]

        # Execute the command
        response = subprocess.run(
            command, capture_output=True, text=True, check=True)
        credentials = json.loads(response.stdout)["Credentials"]

        # Extract credentials
        access_key = credentials["AccessKeyId"]
        secret_key = credentials["SecretAccessKey"]
        session_token = credentials["SessionToken"]

        # Print credentials in export format
        print(f"export AWS_ACCESS_KEY_ID={access_key}")
        print(f"export AWS_SECRET_ACCESS_KEY={secret_key}")
        print(f"export AWS_SESSION_TOKEN={session_token}")

    except subprocess.CalledProcessError as e:
        print("Error assuming role:", e.stderr, file=sys.stderr)
    except KeyError:
        print("Error: Malformed response from AWS CLI. Check your AWS CLI configuration and permissions.", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Assume an AWS IAM role and print environment variables for sourcing.")
    parser.add_argument("role_arn", help="The ARN of the role to assume.")
    parser.add_argument(
        "--session_name",
        help="A unique name for the session. If not provided, a name based on the current timestamp will be used.",
        default=None
    )
    parser.add_argument(
        "--tags",
        nargs="*",
        help="Optional session tags as key=value pairs (e.g., --tags project=demo env=testing).",
        default=None
    )

    args = parser.parse_args()

    # Generate session name if not provided
    session_name = args.session_name or f"session_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Parse tags into a dictionary
    session_tags = None
    if args.tags:
        session_tags = dict(tag.split("=", 1) for tag in args.tags)

    # Assume the role
    assume_role(args.role_arn, session_name, session_tags)


if __name__ == "__main__":
    main()

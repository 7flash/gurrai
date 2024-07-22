#!/usr/bin/env python3

import argparse
import requests
from bs4 import BeautifulSoup
import re
import os
import sqlite3
import logging
from urllib.parse import urlparse
from openai import OpenAI
import sys
import random
import signal

# Function to get logging level from environment variable
def get_logging_level():
    log_level = os.getenv('LOG_LEVEL', 'WARNING').upper()
    levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    return levels.get(log_level, logging.INFO)

# Configure logging
logging.basicConfig(level=get_logging_level(), format='%(asctime)s - %(levelname)s - %(message)s')

# Database setup
DB_PATH = os.path.expanduser("~/.tag_db.sqlite")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            tag TEXT PRIMARY KEY,
            path TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS aliases (
            alias TEXT PRIMARY KEY,
            path TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    logging.info("Database initialized.")

def add_tag(tag, path):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO tags (tag, path) VALUES (?, ?)', (tag, path))
    conn.commit()
    conn.close()
    logging.info(f"Tag '{tag}' added with path '{path}'.")

def add_alias(alias, path):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO aliases (alias, path) VALUES (?, ?)', (alias, path))
    conn.commit()
    conn.close()
    logging.info(f"Alias '{alias}' added with path '{path}'.")

def get_path_by_tag(tag):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT path FROM tags WHERE tag = ?', (tag,))
    result = cursor.fetchone()
    conn.close()
    if result:
        logging.info(f"Path '{result[0]}' retrieved for tag '{tag}'.")
    else:
        logging.warning(f"Tag '{tag}' not found in database.")
    return result[0] if result else None

def remember_path(path):
    parts = path.split('/')
    for i in range(1, len(parts)):
        alias = '/' + '/'.join(parts[i:])
        full_path = '/' + '/'.join(parts[:i+1])
        add_alias(alias, full_path)

def get_path_by_alias(alias):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT path FROM aliases WHERE alias = ?', (alias,))
    result = cursor.fetchone()
    conn.close()
    if result:
        logging.info(f"Path '{result[0]}' retrieved for alias '{alias}'.")
    else:
        logging.warning(f"Alias '{alias}' not found in database.")
    return result[0] if result else None

def find_base_dir(start_path):
    current_path = os.path.abspath(start_path)
    logging.debug(f"Starting path for base directory search: {current_path}")
    while current_path != os.path.dirname(current_path):
        # switched to readme.md instead of package.json because it was breaking when bun accidentally initialized project in root
        if os.path.exists(os.path.join(current_path, 'README.md')):
            logging.debug(f"Found README in: {current_path}")
            return current_path
        current_path = os.path.dirname(current_path)
    return None

# Signal handler for graceful exit
def signal_handler(sig, frame):
    logging.info("Interrupt received, exiting gracefully...")
    sys.exit(0)

# Register the signal handler for SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, signal_handler)

# .main
def main(prompt_path, model_name, temperature):
    try:
        init_db()
    
        prompt_path = os.path.expanduser(prompt_path)
        with open(prompt_path, "r") as file:
            prompt = file.read().strip()

        original_prompt = prompt

        base_dir = find_base_dir(prompt_path)
        if not base_dir:
            logging.warning("No package.json found in ancestor directories. Using current working directory as base directory.")
            base_dir = os.getcwd()

        success, resolved_content_or_error = resolve_links(prompt, base_dir)

        messages, raw_prompt = parse_prompt_into_messages(resolved_content_or_error)

        raw_file_path = os.path.join(
            os.path.dirname(prompt_path),
            os.path.basename(prompt_path).replace("-in.txt", "-raw.txt"),
        )

        # Write the raw prompt to the raw prompt file
        with open(raw_file_path, "w") as raw_file:
            raw_file.write(raw_prompt)
        logging.info(f"Raw prompt written to {raw_file_path}")

        if not success:
            error_message = resolved_content_or_error
            write_error_to_files(prompt_path, original_prompt, error_message)
            sys.exit(0)

        response_file_path = os.path.join(
            os.path.dirname(prompt_path),
            os.path.basename(prompt_path).replace("-in.txt", "-response.txt"),
        )

        client = OpenAI()

        if temperature is None:
            temperature = random.uniform(0.0, 1.0)

        temperature = round(temperature, 2)
        
        logging.warning(f"temperature: {temperature}")

        completion = client.chat.completions.create(
            model=model_name, messages=messages, temperature=temperature
        )

        answer = completion.choices[0].message.content

        out_file_path = os.path.join(
            os.path.dirname(prompt_path),
            os.path.basename(prompt_path).replace("-in.txt", "-out.txt"),
        )

        with open(response_file_path, "w") as response_file:
            response_file.write(answer)
        logging.info(f"Response written to {response_file_path}")

        with open(out_file_path, "w") as out_file:
            out_file.write(original_prompt + "\n|assistant|\n" + answer)
        logging.info(f"Output written to {out_file_path}")
    except KeyboardInterrupt:
        logging.info("Process interrupted by user. Exiting gracefully.")
        sys.exit(0)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    sys.exit(0)

def write_error_to_files(prompt_path, original_prompt, error_message):
    response_file_path = os.path.join(
        os.path.dirname(prompt_path),
        os.path.basename(prompt_path).replace("-in.txt", "-response.txt"),
    )
    out_file_path = os.path.join(
        os.path.dirname(prompt_path),
        os.path.basename(prompt_path).replace("-in.txt", "-out.txt"),
    )

    with open(response_file_path, "w") as response_file:
        response_file.write(error_message)
    logging.info(f"Error written to {response_file_path}")

    with open(out_file_path, "w") as out_file:
        out_file.write(original_prompt + "\n|assistant|\n\n" + error_message)
    logging.info(f"Error written to {out_file_path}")

# .parse_prompt_into_messages
def parse_prompt_into_messages(prompt):
    roles = ["user", "assistant", "system"]
    pattern = r"^\|(" + "|".join(roles) + r")\|"

    parts = re.split(pattern, prompt, flags=re.MULTILINE)

    messages = []
    raw_prompt = ""

    for i in range(1, len(parts), 2):
        role = parts[i]
        content = parts[i + 1].strip()
        if content.lower().startswith("!ignore"):
            logging.warning(f"Ignoring message with role '{role}' and content starting with 'ignore'.")
            continue
        if role in roles:
            messages.append({"role": role, "content": content})
            raw_prompt += f"|{role}|\n{content}\n"

    if len(messages) == 0:
        messages.append({"role": "user", "content": prompt})
        raw_prompt = prompt

    return messages, raw_prompt

def resolve_links(content, base_dir):
    linkRegex = r"^(file:[^\s]+)|(^(http[s]?:\/\/[^\s]+))|(^(#\w+))"
    logging.debug(f"linkRegexp {linkRegex}")
    matches = re.findall(linkRegex, content, re.MULTILINE)

    if not matches:
        return True, content

    for match in matches:
        match = match[0] or match[1] or match[2]
        logging.debug(f"match {match}")
        if match.startswith("file:"):
            protocol = urlparse(match).scheme
            path = urlparse(match).path
            logging.debug(f"path {path}")
            fileName = path.split("/")[-1]
            logging.debug(f"fileName {fileName}")
            selector = None
            if "#" in match:
                _, selector = match.split("#")
            logging.debug(f"selector {selector} & {path}")
            resolvedContent = fetch_file_content(path, selector, base_dir)
            if resolvedContent is None:
                return False, f"Failed to fetch file content from {path}"
            if not resolvedContent.strip():
                return False, f"Resolved content for {match} is empty."
            resolvedContent = re.sub(r"^\|user\|", "user:", resolvedContent, flags=re.MULTILINE)
            resolvedContent = re.sub(r"^\|assistant\|", "assistant:", resolvedContent, flags=re.MULTILINE)
            resolvedContent = re.sub(r"^\|system\|", "system:", resolvedContent, flags=re.MULTILINE)
            resolvedContent = resolvedContent.replace("\\", "\\\\")
            pattern = r"^" + re.escape(match).replace("/", "\/") + r"$"
            logging.debug("sub pattern")
            logging.debug(pattern)
            content = re.sub(
                pattern, resolvedContent, content, flags=re.MULTILINE
            )
            remember_path(path)
        elif match.startswith("#"):
            tag = match[1:]
            path = get_path_by_tag(tag)
            if path:
                resolvedContent = fetch_file_content(path, tag, base_dir)
                if resolvedContent is None:
                    return False, f"Failed to fetch file content for tag {tag}"
                if not resolvedContent.strip():
                    return False, f"Resolved content for {match} is empty."
                resolvedContent = re.sub(r"^\|user\|", "user:", resolvedContent, flags=re.MULTILINE)
                resolvedContent = re.sub(r"^\|assistant\|", "assistant:", resolvedContent, flags=re.MULTILINE)
                resolvedContent = re.sub(r"^\|system\|", "system:", resolvedContent, flags=re.MULTILINE)
                resolvedContent = resolvedContent.replace("\\", "\\\\")
                content = content.replace(match, resolvedContent)
            else:
                logging.warning(f"Tag {tag} not found in database.")
        else:
            path = urlparse(match).path
            fileName = path.split("/")[-1]
            logging.debug(f"fileName {fileName}")
            resolvedContent = fetch_web_content(match)
            if resolvedContent is None:
                return False, f"Failed to fetch web content from {match}"
            resolvedContent = resolvedContent.replace("user:", "user:")
            resolvedContent = resolvedContent.replace(
                "assistant:", "assistant:"
            )
            resolvedContent = resolvedContent.replace("system:", "system:")
            if "#" in match:
                element = match.split("#")[-1]
                logging.debug(f"element {element}")
                soup = BeautifulSoup(resolvedContent, "html.parser")
                resolvedContent = soup.select(element)[0].get_text()
            content = content.replace(match, resolvedContent)

    return True, content

# .fetch_file_content
def fetch_file_content(file_path, selector, base_dir):
    home_dir = os.path.expanduser("~")
    if os.path.isabs(file_path):
        if not file_path.startswith(home_dir):
            file_path = file_path.lstrip("/")
            file_path = os.path.join(home_dir, file_path)
    else:
        local_path = os.path.join(base_dir, file_path)
        if os.path.exists(local_path):
            file_path = local_path
        else:
            alias_path = get_path_by_alias(file_path)
            if alias_path:
                file_path = alias_path
            else:
                file_path = os.path.join(base_dir, file_path)
    logging.debug(f"file path {file_path}")
    try:
        with open(file_path, "r") as file:
            content = file.read()
        if selector:
            file_extension = os.path.splitext(file_path)[1]
            if file_extension == ".md":
                # Handle Markdown headers
                pattern = rf"(^#+\s+{re.escape(selector)}.*?$)(.*?)(?=^#+\s|\Z)"
            else:
                # Handle other file types with comments
                if file_extension == ".py" or file_extension == ".css":
                    comment_symbol = "#"
                else:
                    comment_symbol = "//"
                pattern = rf"({re.escape(comment_symbol)}\s?\.{re.escape(selector)}.*?$)(.*?)(?={re.escape(comment_symbol)}\s?\.|\Z)"
            logging.debug(f"Pattern used: {pattern}")
            matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
            if matches:
                segmented_content = matches[0][1]
                return segmented_content.strip()
            else:
                logging.warning(f"Segment not found for {selector} in {file_path}")
                return ""
        else:
            return content.strip()
    except Exception as e:
        logging.error(f"Failed to fetch file content from {file_path}: {e}")
        return None

# .fetch_web_content
def fetch_web_content(link):
    try:
        response = requests.get(link)
        return response.text
    except Exception as e:
        logging.error(f"Failed to fetch web content from {link}: {e}")
        return ""

# .start
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate response from a prompt file using OpenAI's model and write the response to a new file."
    )
    parser.add_argument(
        "prompt_path",
        type=str,
        help="Path to the file containing the prompt text.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4-0125-preview",
        help="Model name to be used. Default is 'gpt-4-1106-preview'.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        help="Temperature/Creativity. If not specified, a random temperature between 0.0 and 1.0 will be used.",
    )

    args = parser.parse_args()

    main(args.prompt_path, args.model, args.temperature)

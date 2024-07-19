import re

def parse_markdown(text):
    """Parses a markdown text to extract YAML front matter and the document body"""
    # Remove content between {% %}
    content = re.sub(r'{%.*%}', '', content, flags=re.MULTILINE)
    # Define a regular expression pattern to match the front matter between `---\n` delimiters
    pattern = re.compile(r'^---\s*$(.*?)^---\s*$', re.DOTALL | re.MULTILINE)
    match = pattern.search(text)
    if not match:
        raise ValueError("Input text does not contain proper front matter delimiters '---'")
    
    # Extract the front matter and the body
    front_matter = match.group(1).strip()
    body_start = match.end()
    body = text[body_start:].strip()
    
    return front_matter, body

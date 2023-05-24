import re

string = "BOLT #1: Base Protocol"

# Remove non-alphanumeric characters except spaces
string = re.sub(r"[^a-zA-Z0-9 ]+", "", string)
# Convert to lowercase
string = string.lower()

# Replace spaces with dashes
string = string.replace(" ", "-")

print(string)

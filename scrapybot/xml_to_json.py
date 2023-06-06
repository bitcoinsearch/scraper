import xmltodict
import json

print("Reading the XML file...")
with open('dump_20190227_he.xml', 'r') as file:
    xml_data = file.read()

print(" Converting XML to OrderedDict")
xml_dict = xmltodict.parse(xml_data,item_depth=2)

# Convert OrderedDict to JSON
print(" Converting OrderedDict to JSON...")
json_data = json.dumps(xml_dict, indent=4)

# Save the JSON to a file
with open('output.json', 'w') as file:
    file.write(json_data)

print("XML converted to JSON successfully.")


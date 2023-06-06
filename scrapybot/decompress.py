import requests
import bz2

#url = "https://dump.bitcoin.it/dump_20191211_en.xml.bz2"  # Replace with the actual URL of the file you want to download
url = "http://dump.bitcoin.it/dump_20190227_he.xml.bz2"

# Download the file

print("Downloading file...")
response = requests.get(url)
print(response.status_code)
if response.status_code == 200:
    file_content = response.content

    # Save the downloaded file
    with open('dump_20190227_he.xml.bz2', 'wb') as file:
        file.write(file_content)

    print("Done writing file to disk....Now extracting")
    # Extract the file
    with open('dump_20190227_he.xml.bz2', 'rb') as file:
        compressed_data = file.read()

    decompressed_data = bz2.decompress(compressed_data)

    # Save the extracted file
    with open('dump_20190227_he.xml', 'wb') as file:
        file.write(decompressed_data)

    print("File downloaded and extracted successfully.")
else:
    print("Failed to download the file.")


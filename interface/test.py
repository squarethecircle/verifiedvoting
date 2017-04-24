# import requests
# from bs4 import BeautifulSoup
# import xml.etree.ElementTree as ET

# r = requests.get("https://beacon.nist.gov/rest/record/last")
# soup = BeautifulSoup(r.text, "lxml")

# print(soup)
# print(soup.find("timestamp").contents[0])
# print(soup.find("outputvalue").contents[0])


# root = ET.fromstring(r.text)
# print(type(r.text))

# print(root.tag)
# for child in root: 
# 	print (child.tag, child.attrib)


# import untangle

# obj = untangle.parse("https://beacon.nist.gov/rest/record/last")

# print (obj)

import requests
import re

r = requests.get("https://beacon.nist.gov/rest/record/last")
ts = re.search(r"<timeStamp>(.*)<\/timeStamp>",r.text).group(1)
ov = re.search(r"<outputValue>(.*)<\/outputValue>",r.text).group(1)
print(ts, ov)
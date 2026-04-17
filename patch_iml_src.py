import xml.etree.ElementTree as ET

tree = ET.parse('.idea/Friday.iml')
root = tree.getroot()

content = root.find(".//content")
if content is not None:
    # Check if sourceFolder already exists
    exists = False
    for el in content.findall("sourceFolder"):
        if el.get("url") == "file://$MODULE_DIR$/veritas-ai":
            exists = True
            break
            
    if not exists:
        ET.SubElement(content, "sourceFolder", url="file://$MODULE_DIR$/veritas-ai", isTestSource="false")

    ET.indent(tree, space="  ", level=0)
    tree.write('.idea/Friday.iml', encoding="UTF-8", xml_declaration=True)
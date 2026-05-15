import json

from utilities.printer_compatibility import validate_printer_compatibility
from utilities.print_file_validator import validate_schema

with open("hardware_config/hardware_config_example.json", "r") as file_handle:
    config_dict = json.load(file_handle)

print_settings, schema_ver = validate_schema("print_files/example.zip")
if schema_ver not in config_dict["valid_schema_versions"]:
    raise ValueError(f"Printer does not support {schema_ver} JSON format")
validate_printer_compatibility(print_settings, config_dict)

print(f"Validation successful for print_files/example.zip with schema version {schema_ver}.")
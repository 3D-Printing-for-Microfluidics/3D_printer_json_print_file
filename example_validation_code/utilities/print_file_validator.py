import re
import json
import copy
from pathlib import Path
from zipfile import ZipFile, BadZipFile
from tempfile import TemporaryDirectory
from jsonschema import Draft7Validator
from jsonschema.exceptions import ValidationError
from simpleeval import simple_eval
from PIL import Image

VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


def validate_schema(print_file):
    """Validate a print file and return the print settings
    as JSON. If an error is detected, a ValueError is raised with
    appropriate information.
    """
    try:
        with ZipFile(
            print_file, "r"
        ) as zip_file_handle, TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            namelist = zip_file_handle.namelist()
            for name in list(namelist):
                if (".csv" in name) or (".log" in name) or ("exposure_data" in name):
                    namelist.remove(name)
            zip_file_handle.extractall(temp_dir, members=namelist)
            
            # Check that there is only 1 json file and read it
            print_settings = check_for_unique_print_settings(temp_dir)

            # Check version and validate against schema
            # We must expand named layer groups and expand variables before validation
            version = check_version(print_settings)
            expand_named_layer_groups(print_settings)
            expand_variables(print_settings)
            validate_against_schema(print_settings, f"schema_{version}.json")

            if version == "v999":
                return print_settings, version

            # Check named settings and templates (TEMPLATES DEPRECATED)
            check_referenced_templates_exist(print_settings)
            check_referenced_named_position_settings_exist(print_settings)
            check_referenced_named_image_settings_exist(print_settings)
            expand_templates(print_settings)
            check_templates_compatibility(print_settings)
            expand_json(print_settings)

            # Validate negative layer thickness usage
            validate_negative_layer_thickness(print_settings) # DEPRECATED

            check_slices_folder_exists(zip_file_handle, print_settings)
            check_referenced_images_exist(print_settings, temp_dir)

            if __name__ == "__main__":
                print(f"Validation successful for {print_file} with schema version {version}.")
                print(f"Validated print settings JSON:\n{json.dumps(print_settings, indent=2)}")

            return print_settings, version
    except BadZipFile:
        msg = "File is not a .zip file."
        raise ValueError(msg)


def read_json(path_to_file):
    """Helper function to return the json data from a file."""
    with open(path_to_file, "r") as file_handle:
        return json.load(file_handle)


def write_json(path_to_file, print_settings):
    """Helper function to write the json data from a file."""
    with open(path_to_file, "w") as file_handle:
        return json.dump(print_settings, file_handle)


def check_for_unique_print_settings(unzipped_dir):
    """Return the print settings as JSON, checking that there is only 1
    print settings file in the directory.
    """
    json_files = list(unzipped_dir.glob("*.json"))
    if len(json_files) < 1:
        msg = "Could not find a json file. "
        msg += "Make sure there is a json file in the top level directory."
        raise ValueError(msg)
    if len(json_files) > 1:
        raise ValueError(f"More than 1 json file: {json_files}")
    return read_json(json_files[0])


def expand_variables(print_settings):
    """Expand variables in the print settings JSON."""
    # Define default variables

    variables = print_settings.get("Variables", {})
    resolved_print_settings = resolve_expressions(print_settings, variables)
    for key in list(print_settings.keys()):
        if key not in resolved_print_settings.keys():
            del print_settings[key]
    for key in resolved_print_settings.keys():
        print_settings[key] = resolved_print_settings[key]


def resolve_expressions(obj, variables):
    if isinstance(obj, dict):
        return {k: resolve_expressions(v, variables) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [resolve_expressions(item, variables) for item in obj]
    elif isinstance(obj, str):
        matches = list(VAR_PATTERN.finditer(obj))

        if not matches:
            return obj

        # Case 1: Pure Expression - preserve the original type (bool, int, etc.)
        # e.g., obj is exactly "${my_boolean_var}"
        if len(matches) == 1 and matches[0].group(0) == obj:
            return simple_eval(matches[0].group(1), names=variables)

        # Case 2: String Interpolation - convert everything to a string
        # e.g., obj is "Speed: ${base_speed * 1.2} mm/s"
        last_end = 0
        result_parts = []
        for match in matches:
            result_parts.append(obj[last_end : match.start()])
            val = simple_eval(match.group(1), names=variables)
            result_parts.append(str(val))
            last_end = match.end()
        result_parts.append(obj[last_end:])

        return "".join(result_parts)

    return obj


def build_scoped_variables(global_variables, override_variables):
    """Return resolved variables for a scoped context (e.g., named layer group)."""
    merged = dict(global_variables or {})
    if override_variables:
        merged.update(override_variables)
    return resolve_expressions(merged, merged)


def expand_named_layer_groups(print_settings):
    """Expand named layer groups into the main Layers list with variable overrides."""
    if "Named layer groups" not in print_settings:
        return

    named_layer_groups = print_settings.get("Named layer groups") or {}
    layers = print_settings.get("Layers", [])
    if not layers:
        return

    global_variables = print_settings.get("Variables", {})
    expanded_layers = []

    for layer in layers:
        if "Using named layer group" not in layer:
            expanded_layers.append(layer)
            continue

        layer_group_name = layer["Using named layer group"]
        if layer_group_name not in named_layer_groups:
            msg = f"Referenced named layer group '{layer_group_name}' could not be found."
            raise ValueError(msg)

        group_layers = named_layer_groups[layer_group_name]
        group_variables = layer.get("Variables", {})
        scoped_variables = build_scoped_variables(global_variables, group_variables)

        resolved_group_layers = []
        for group_layer in group_layers:
            resolved_layer = resolve_expressions(copy.deepcopy(group_layer), scoped_variables)
            resolved_group_layers.append(resolved_layer)

        num_group_dups = layer.get("Number of duplications", 1)
        for _ in range(num_group_dups):
            for resolved_layer in resolved_group_layers:
                expanded_layers.append(copy.deepcopy(resolved_layer))

    print_settings["Layers"] = expanded_layers


def check_slices_folder_exists(zip_file_handle, print_settings):
    """Ensure the specified image folder exists in the print file."""
    slices_folder = print_settings["Header"]["Image directory"]
    if not any(slices_folder for f in zip_file_handle.namelist()):
        raise ValueError(f"Could not find image folder: {slices_folder}")


def check_version(print_settings):
    """Check the version of print settings file. Should be '0.2 or 2.x.x-5.x.x'."""
    if "Header" not in print_settings:
        msg = "'Header' missing from json file."
        raise ValueError(msg)
    if "Schema version" not in print_settings["Header"]:
        msg = f"Missing schema version.\n"
        msg += "  Check 'Header' -> 'Schema Version'"
        raise ValueError(msg)

    is_semver = False
    is_major_minor = False
    schema_version = print_settings["Header"]["Schema version"]
    ver = schema_version.split(".")

    is_semver = re.search("\d+\.\d+\.\d+", schema_version) != None
    if not is_semver:  #
        is_major_minor = re.search("\d+\.\d+", schema_version) != None
        if is_major_minor:
            ver = [ver[1], 0, 0]
        else:
            msg = "Invalid version format. Must be 'x.x' or 'x.x.x'."
            msg += "  Check 'Header' -> 'Schema Version'"
            raise ValueError(msg)

    if int(ver[0]) < 2:
        msg = "File is version 0.1. Use converter to convert to version 0.2"
        msg += "  Check 'Header' -> 'Schema Version'"
        raise ValueError(msg)
    elif int(ver[0]) > 5 and not int(ver[0]) == 999:
        msg = "Invalid major version number."
        msg += "  Check 'Header' -> 'Schema Version'"
        raise ValueError(msg)
    else:
        return f"v{ver[0]}"


def validate_against_schema(print_settings, schema):
    """Check the print settings against the schema."""
    here = Path(__file__).parent.parent.absolute()
    schema = here / "schemas" / Path(schema)
    try:
        Draft7Validator(read_json(schema)).validate(print_settings)
    except ValidationError as ex:
        path_string = " -> ".join(f"'{str(v)}'" for v in ex.path)
        msg = f"  {ex.message}\n  Check {path_string}"
        raise ValueError(msg)


def check_image_format(image_file):
    """Ensure the image is an 8-bit grayscale PNG."""
    with Image.open(image_file) as img:
        if img.format != "PNG" or img.mode != "L":
            msg = f"Bad image. '{image_file}' must be an 8-bit grayscale PNG."
            raise ValueError(msg)


def check_referenced_images_exist(print_settings, temp_dir):
    """Ensure that all images referenced in the print settings are
    included in the print file. Uses the default image if no override is
    provided.
    """
    slices_folder = Path(print_settings["Header"]["Image directory"])
    slices = list(temp_dir.glob(f"{slices_folder}/**/*.png"))
    img = print_settings["Default layer settings"]["Image settings"]["Image file"]

    if temp_dir / slices_folder / Path(img) not in slices:
        msg = f"Missing image. Default image {img} could not be found.\n"
        msg += "  Check 'Default layer settings' -> 'Image settings' -> 'Image file'"
        raise ValueError(msg)
    for layer in print_settings["Layers"]:
        if "Image settings list" in layer:
            for image_setting in layer["Image settings list"]:
                if "Image file" in image_setting:
                    img = image_setting["Image file"]
                    img_path = temp_dir / slices_folder / Path(img)
                    if img_path not in slices:
                        msg = f"Missing image: '{img}' could not be found."
                        raise ValueError(msg)
                    check_image_format(img_path)


########################### DEPRECATED ###########################
def check_referenced_templates_exist(print_settings):
    """Check that all templates referenced in JSON exist."""
    if "Templates" in print_settings:
        templates = print_settings["Templates"]
    else:
        templates = {}

    "'Templates[]'->'Parent template'"
    for template in templates.values():
        if "Parent template" in template:
            parent_template = template["Parent template"]
            if parent_template not in templates.keys():
                msg = f"Referenced template '{parent_template}' could not be found."
                raise ValueError(msg)

    "'Layers[]'->'Using templates'"
    for layer in print_settings["Layers"]:
        if "Using templates" in layer:
            for template in layer["Using templates"]:
                if template not in templates.keys():
                    msg = f"Referenced template '{template}' could not be found."
                    raise ValueError(msg)
#################################################################


def check_referenced_named_position_settings_exist(print_settings):
    """Check that all named position settings referenced in JSON exist."""
    if "Named position settings" in print_settings:
        named_position_settings = print_settings["Named position settings"]
    else:
        named_position_settings = {}

    "'Named position settings[]'->'Using named position settings'"
    if "Named position settings" in print_settings:
        for named_position_setting in named_position_settings.values():
            if "Using named position settings" in named_position_setting:
                parent_named_position_setting = named_position_setting[
                    "Using named position settings"
                ]
                if parent_named_position_setting not in named_position_settings.keys():
                    msg = f"Referenced position settings '{parent_named_position_setting}' could not be found."
                    raise ValueError(msg)

    ########################### DEPRECATED ###########################
    "'Templates[]'->'Position settings'->'Using named position settings'"
    if "Templates" in print_settings:
        for template in print_settings["Templates"].values():
            if "Position settings" in template:
                position_settings = template["Position settings"]
                if "Using named position settings" in position_settings:
                    named_position_setting = position_settings[
                        "Using named position settings"
                    ]
                    if named_position_setting not in named_position_settings.keys():
                        msg = f"Referenced position settings '{named_position_setting}' could not be found."
                        raise ValueError(msg)
    #################################################################

    "'Layers[]'->'Position settings'->'Using named position settings'"
    for layer in print_settings["Layers"]:
        if "Position settings" in layer:
            position_settings = layer["Position settings"]
            if "Using named position settings" in position_settings:
                named_position_setting = position_settings[
                    "Using named position settings"
                ]
                if named_position_setting not in named_position_settings.keys():
                    msg = f"Referenced position settings '{named_position_setting}' could not be found."
                    raise ValueError(msg)


def check_referenced_named_image_settings_exist(print_settings):
    """Check that all named image settings referenced in JSON exist."""
    if "Named image settings" in print_settings:
        named_image_settings = print_settings["Named image settings"]
    else:
        named_image_settings = {}

    "'Named image settings[]'->'Using named image settings'"
    if "Named image settings" in print_settings:
        for named_image_setting in named_image_settings.values():
            if "Using named image settings" in named_image_setting:
                parent_named_image_setting = named_image_setting[
                    "Using named image settings"
                ]
                if parent_named_image_setting not in named_image_settings.keys():
                    msg = f"Referenced image settings '{parent_named_image_setting}' could not be found."
                    raise ValueError(msg)

    ########################### DEPRECATED ###########################
    "'Templates'->'Using named default image settings' and 'Templates[]'->'Image settings list[]'->'Using named image settings'"
    if "Templates" in print_settings:
        for template in print_settings["Templates"].values():
            if "Using named default image settings" in template:
                named_image_setting = template["Using named default image settings"]
                if named_image_setting not in named_image_settings.keys():
                    msg = f"Referenced image settings '{named_image_setting}' could not be found."
                    raise ValueError(msg)
            if "Image settings list" in template:
                for image_settings in template["Image settings list"]:
                    if "Using named image settings" in image_settings:
                        named_image_setting = image_settings["Using named image settings"]
                        if named_image_setting not in named_image_settings.keys():
                            msg = f"Referenced image settings '{named_image_setting}' could not be found."
                            raise ValueError(msg)
    #################################################################

    "'Layers[]'->'Using named default image settings' and 'Layers[]'->'Image settings list[]'->'Using named image settings'"
    for layer in print_settings["Layers"]:
        if "Using named default image settings" in layer:
            named_image_setting = layer["Using named default image settings"]
            if named_image_setting not in named_image_settings.keys():
                msg = f"Referenced image settings '{named_image_setting}' could not be found."
                raise ValueError(msg)
        if "Image settings list" in layer:
            for image_settings in layer["Image settings list"]:
                if "Using named image settings" in image_settings:
                    named_image_setting = image_settings["Using named image settings"]
                    if named_image_setting not in named_image_settings.keys():
                        msg = f"Referenced image settings '{named_image_setting}' could not be found."
                        raise ValueError(msg)


########################### DEPRECATED ###########################
# Expand templates before calling
def check_templates_compatibility(print_settings):
    "Check template compatibility in Layers"
    for layer_num, layer in enumerate(print_settings["Layers"]):
        if "Using templates" in layer:
            len_image_settings_list = 0
            position_settings = None
            num_dups = None
            first_ittr = True
            for template_key in layer["Using templates"]:
                template = print_settings["Templates"][template_key]
                if first_ittr:
                    position_settings = template.get("Position settings", None)
                    num_dups = template.get("Number of duplications", None)
                    first_ittr = False
                elif template.get("Position settings", None) != position_settings:
                    msg = f"Template conflict found in layer {layer_num}. Insure templates have the same position settings!"
                    raise ValueError(msg)
                elif template.get("Number of duplications", None) != num_dups:
                    msg = f"Template conflict found in layer {layer_num}. Insure templates have same number of duplication!"
                    raise ValueError(msg)
                len_image_settings_list += len(template.get("Image settings list", [{}]))

            if (len(layer.get("Image settings list", [])) > 0) and (
                len(layer.get("Image settings list", [])) != len_image_settings_list
            ):
                msg = f"Incorrect number of image settings for given templates in layer {layer_num}! Needs {len_image_settings_list} image settings."
                raise ValueError(msg)
#################################################################


def update_json(overrides, defaults):
    """Return the position settings for the layer."""
    final_settings = defaults.copy()
    if overrides is not None:
        final_settings.update(overrides)
    return final_settings


def update_layer_json(overrides, defaults):
    new_layer = {}

    # Override top level parameters
    for key in [
        "Comment",
        "Number of duplications",
        "Using named default image settings",
    ]:
        val = overrides.get(key, defaults.get(key, None))
        if val != None:
            new_layer[key] = val

    # Override position settings
    d_position_settings = defaults.get("Position settings", {})
    position_settings = overrides.get("Position settings", {})
    new_position_settings = update_json(position_settings, d_position_settings)
    if len(new_position_settings.keys()) > 0:
        new_layer["Position settings"] = new_position_settings

    # Override image settings list
    new_image_settings_list = []
    d_image_settings_list = defaults.get("Image settings list", [])
    image_settings_list = overrides.get("Image settings list", [])
    for i in range(max(len(d_image_settings_list), len(image_settings_list))):
        d_image_settings = {}
        image_settings = {}
        if i < len(d_image_settings_list):
            d_image_settings = d_image_settings_list[i]
        if i < len(image_settings_list):
            image_settings = image_settings_list[i]
        new_image_settings = update_json(image_settings, d_image_settings)
        new_image_settings_list.append(new_image_settings)
    new_layer["Image settings list"] = new_image_settings_list

    return new_layer


def expand_named_position_settings(print_settings):
    # RESOLVE POSITION SETTINGS INHERITANCE
    if "Named position settings" in print_settings:
        root_position_settings = []
        position_setting_keys = print_settings["Named position settings"].keys()
        last_pass_length = len(root_position_settings)
        while len(root_position_settings) < len(position_setting_keys):
            for position_setting_key in position_setting_keys:
                position_settings = print_settings["Named position settings"][
                    position_setting_key
                ]
                parent_position_settings_key = position_settings.get(
                    "Using named position settings", None
                )
                if (position_setting_key not in root_position_settings) and (
                    parent_position_settings_key == None
                ):
                    root_position_settings.append(position_setting_key)
                elif parent_position_settings_key in root_position_settings:
                    parent_position_settings = print_settings["Named position settings"][
                        parent_position_settings_key
                    ]
                    # expand named position settings
                    position_settings.pop("Using named position settings")
                    position_settings.update(
                        update_json(position_settings, parent_position_settings)
                    )
            if last_pass_length == len(root_position_settings):
                msg = f"Circular dependency in 'Named position settings'!"
                raise ValueError(msg)
            else:
                last_pass_length = len(root_position_settings)


def expand_named_image_settings(print_settings):
    # RESOLVE IMAGE SETTINGS INHERITANCE
    if "Named image settings" in print_settings:
        root_image_settings = []
        image_setting_keys = print_settings["Named image settings"].keys()
        last_pass_length = len(root_image_settings)
        while len(root_image_settings) < len(image_setting_keys):
            for image_setting_key in image_setting_keys:
                image_settings = print_settings["Named image settings"][image_setting_key]
                parent_image_settings_key = image_settings.get(
                    "Using named image settings", None
                )
                if (image_setting_key not in root_image_settings) and (
                    parent_image_settings_key == None
                ):
                    root_image_settings.append(image_setting_key)
                elif parent_image_settings_key in root_image_settings:
                    parent_image_settings = print_settings["Named image settings"][
                        parent_image_settings_key
                    ]
                    # expand image settings
                    image_settings.pop("Using named image settings")
                    image_settings.update(
                        update_json(image_settings, parent_image_settings)
                    )
            if last_pass_length == len(root_image_settings):
                msg = f"Circular dependency in 'Named image settings'!"
                raise ValueError(msg)
            else:
                last_pass_length = len(root_image_settings)

########################### DEPRECATED ###########################
def expand_templates(print_settings):
    # RESOLVE TEMPLATE INHERITANCE
    if "Templates" in print_settings:
        root_templates = []
        template_keys = print_settings["Templates"].keys()
        last_pass_length = len(root_templates)
        while len(root_templates) < len(template_keys):
            for template_key in template_keys:
                template = print_settings["Templates"][template_key]
                parent_template_key = template.get("Parent template", None)
                if (template_key not in root_templates) and (parent_template_key == None):
                    root_templates.append(template_key)
                elif parent_template_key in root_templates:
                    parent_template = print_settings["Templates"][parent_template_key]
                    # expand templates
                    print_settings["Templates"][template_key] = update_layer_json(
                        template, parent_template
                    )
            if last_pass_length == len(root_templates):
                msg = f"Circular dependency in 'Templates'!"
                raise ValueError(msg)
            else:
                last_pass_length = len(root_templates)


def replace_templates_in_layer(print_settings, layer):
    # REPLACE TEMPLATES IN LAYERS
    if "Using templates" in layer:
        number_of_image_settings = 0
        for parent_template_key in layer["Using templates"]:
            parent_template = print_settings["Templates"][parent_template_key]
            parent_template_copy = parent_template.copy()
            parent_template_copy["Image settings list"] = parent_template[
                "Image settings list"
            ].copy()
            for i in range(number_of_image_settings):
                parent_template_copy["Image settings list"].insert(0, {})
            number_of_image_settings = len(parent_template_copy["Image settings list"])
            layer.update(update_layer_json(layer, parent_template_copy))
        layer.pop("Using templates")
#################################################################


def replace_named_position_settings_in_layer(print_settings, layer):
    # REPLACE NAMED POSITION SETTINGS IN LAYERs
    if "Position settings" in layer:
        position_settings = layer["Position settings"]
        if "Using named position settings" in position_settings:
            parent_position_settings_key = position_settings[
                "Using named position settings"
            ]
            parent_position_settings = print_settings["Named position settings"][
                parent_position_settings_key
            ]
            # expand named position settings
            position_settings.update(
                update_json(position_settings, parent_position_settings)
            )
            position_settings.pop("Using named position settings")


def replace_named_image_settings_in_layer(print_settings, layer):
    # REPLACE NAMED IMAGE SETTINGS IN LAYERS
    if "Using named default image settings" in layer:
        if "Image settings list" not in layer:
            layer["Image settings list"] = [{}]
        if len(layer["Image settings list"]) == 0:
            layer["Image settings list"].append({})
        for image_settings in layer["Image settings list"]:
            if "Using named image settings" not in image_settings:
                parent_image_settings_key = layer["Using named default image settings"]
                parent_image_settings = print_settings["Named image settings"][
                    parent_image_settings_key
                ]
                # expand named image settings
                image_settings.update(update_json(image_settings, parent_image_settings))
        layer.pop("Using named default image settings")
    if "Image settings list" in layer:
        for image_settings in layer["Image settings list"]:
            if "Using named image settings" in image_settings:
                parent_image_settings_key = image_settings["Using named image settings"]
                parent_image_settings = print_settings["Named image settings"][
                    parent_image_settings_key
                ]
                # expand named image settings
                image_settings.update(update_json(image_settings, parent_image_settings))
                image_settings.pop("Using named image settings")


def expand_json(print_settings):
    """Expands the JSON to remove all named image/position settings and templates"""
    if check_version(print_settings) == "v999":
        return
    
    expand_named_layer_groups(print_settings)
    expand_variables(print_settings)

    expand_named_position_settings(print_settings)
    expand_named_image_settings(print_settings)
    expand_templates(print_settings) # DEPRECATED

    # EXPAND LAYERS
    for layer in print_settings["Layers"]:
        replace_templates_in_layer(print_settings, layer) # DEPRECATED
        replace_named_position_settings_in_layer(print_settings, layer)
        replace_named_image_settings_in_layer(print_settings, layer)


########################### DEPRECATED ###########################
def validate_negative_layer_thickness(print_settings):
    """Validate that negative layer thickness is only used in specific circumstances.

    Negative layer thickness is only allowed when:
    1. It follows a layer with significantly larger thickness (e.g., for membrane fabrication)
    2. There can be zero or more layers with 0um thickness between the positive and negative layers

    Raises ValueError if validation fails.
    """
    if "Default layer settings" not in print_settings:
        return

    if "Layers" not in print_settings:
        return

    layers = print_settings["Layers"]
    if not layers:
        return

    # Track the last significant positive layer thickness
    last_significant_positive_thickness = None
    last_significant_positive_layer_index = None

    for i, layer in enumerate(layers):
        if "Position settings" not in layer:
            continue

        default_position_settings = print_settings["Default layer settings"][
            "Position settings"
        ]

        position_settings = layer["Position settings"]
        if "Layer thickness (um)" not in position_settings:
            continue

        normal_thickness = print_settings["Default layer settings"]["Position settings"][
            "Layer thickness (um)"
        ]
        thickness = position_settings["Layer thickness (um)"]

        # Check for negative thickness
        if thickness < 0:
            # If we haven't seen a significant positive thickness yet, this is an error
            if last_significant_positive_thickness is None:
                msg = f"Layer {i} has negative thickness ({thickness} um) but there's no previous layer with significant positive thickness."
                raise ValueError(msg)

            # Check if there are any non-zero layers between the last significant positive and this negative
            for j in range(last_significant_positive_layer_index + 1, i):
                if (
                    "Position settings" in layers[j]
                    and "Layer thickness (um)" in layers[j]["Position settings"]
                ):
                    intermediate_thickness = layers[j]["Position settings"][
                        "Layer thickness (um)"
                    ]
                    if intermediate_thickness != 0:
                        msg = f"Layer {i} has negative thickness ({thickness} um) but there's a non-zero layer ({j}) between it and the last significant positive layer."
                        raise ValueError(msg)

            # Check if the negative thickness is appropriate for the last significant positive
            # We expect the negative thickness to be approximately equal to the positive thickness minus the normal layer thickness
            expected_negative_min = -last_significant_positive_thickness
            expected_negative_max = -(
                last_significant_positive_thickness - normal_thickness
            )

            if thickness < expected_negative_min or thickness > expected_negative_max:
                msg = f"Layer {i} has negative thickness ({thickness} um) which doesn't match the expected value ({expected_negative_max}>= thickness >={expected_negative_min} um) based on the previous significant positive layer ({last_significant_positive_thickness} um)."
                raise ValueError(msg)

        # If this is a significant positive thickness, update our tracking
        elif (
            thickness > normal_thickness * 2
        ):  # Consider it significant if it's more than twice the normal thickness
            last_significant_positive_thickness = thickness
            last_significant_positive_layer_index = i
#################################################################


if __name__ == "__main__":
    # for print_job in Path("test_print_files_v2").glob("*.zip"):
    #     try:
    #         print_settings, schema_ver = validate_schema(print_job)
    #         print(f"{schema_ver}: {print_job} is good")
    #     except ValueError as ex:
    #         print(f"Error in {print_job}:\n {ex}")

    # get print settings file from command line argument and validate
    import argparse
    parser = argparse.ArgumentParser(description="Validate a print settings file.")
    parser.add_argument("print_file", type=str, help="Path to the print settings .zip file.")
    args = parser.parse_args()
    print_file = args.print_file
    try:
        print_settings, schema_ver = validate_schema(print_file)
        print(f"{schema_ver}: {print_file} is good")
    except ValueError as ex:
        print(f"Error in {print_file}:\n {ex}")

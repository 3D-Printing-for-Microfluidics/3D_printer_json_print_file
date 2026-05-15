# Nordin Group - 3D Printer Print File Specification

The purpose of this repository is to document a JSON-based file standard for conveying 3D print information to a Digital Light Processing Stereolithography (DLP-SL) 3D printer for how to run a print job. This is the file format used by the custom 3D printers developed in the Nordin Group at Brigham Young University (BYU), and is intended as a general standard that can be used in industry and academia. 

Traditionally DLP-SL 3D printers only expose a single image per layer, and have the same layer thickness for each layer. Print files that follow the format we outline in this repository allow each layer to be comprised of multiple images, with the ability to customize the exposure time for each image, as well as customizing each layer's thickness.

Overall, following this file standard gives a much higher degree of control over how a design is printed compared to traditional 3D printing methods.


# Standard for Print Job

A print job is composed of two parts: (1) a JSON file that follows the specification in this README, and (2) a directory with all of the png images that define what is to be printed. In our implementation, both of these parts are compressed into a single zip file which is uploaded to the printer. The zip file is typically organized as follows:

```
    .  
    ├── print_settings.json  
    └── slices  
        ├── 0000.png  
        ├── 0001.png  
        ├── 0002.png  
        └── 0003.png  
            .  
            .  
            .  
```

## Definitions

`Layer`: everything that happens after finishing the last exposure for the previous layer and the last exposure for the current layer.

This involves two sets of operations controlled by the following settings:
`Position Settings`: move build platform up, an optional wait if specified, and move build platform down the same amount as it moved up minus the layer thickness.
`Exposure Settings`: a series of optional waits and mandatory exposures, one exposure for each image for the current layer.

## Finite State Machine View of 3D Printer Operation

![](assets/HR3p2_finite_state_machine_v2.png)


## JSON File

Time units are milliseconds.
Layer thickness is in microns.
All other distance, velocity, and acceleration units are mm, mm/s, and mm/s<sup>2</sup>.

Schema versions are now in the 5.x line. The examples below are updated to reflect the v5 structure and new features.

## Minimal format (v5)

The following JSON file represent the minimal content to specify a 3D print. **ALL FIELDS ARE REQUIRED.**

### JSON

For this minimal case, **all layers have the same position and exposure parameters**, i.e., those specified in `Default layer settings`. Only 6 layers are included to avoid using too much space to illustrate the idea.

    {
        "Header": {
            "Schema version": "5.0.0",
            "Image directory": "slices"
        },
        "Default layer settings": {
            "Number of duplications": 1,
            "Position settings": {
                "Layer thickness (um)": 10,
                "Distance up (mm)": 1.0,
                "Initial wait (ms)": 100.0,
                "BP up speed (mm/sec)": 25.0,
                "BP up acceleration (mm/sec^2)": 50.0,
                "Up wait (ms)": 0,
                "BP down speed (mm/sec)": 20.0,
                "BP down acceleration (mm/sec^2)": 50.0,
                "Final wait (ms)": 0
            },
            "Image settings": {
                "Image file": "0000.png",
                "Layer exposure time (ms)": 550,
                "Light engine": "visitech",
                "Light engine wavelength (nm)": 365,
                "Light engine power setting": 100,
                "Relative focus position (um)": 0,
                "Wait before exposure (ms)": 0,
                "Wait after exposure (ms)": 0
            }
        },
        "Layers": [
            {
                "Image settings list": [
                    {
                        "Image file": "0001.png"
                    }
                ]
            },
            {
                "Image settings list": [
                    {
                        "Image file": "0002.png"
                    }
                ]
            },
            {
                "Image settings list": [
                    {
                        "Image file": "0003.png"
                    }
                ]
            },
            {
                "Image settings list": [
                    {
                        "Image file": "0004.png"
                    }
                ]
            },
            {
                "Image settings list": [
                    {
                        "Image file": "0005.png"
                    }
                ]
            },
            {
                "Image settings list": [
                    {
                        "Image file": "0006.png"
                    }
                ]
            }
        ]
    }

### Minimal JSON layer object

The minimal information needed for an individual layer in the `Layers` list is an empty Layer object, in which case the default image will be used for the layer exposure:

    # Layer settings object
    {
        # List of Image settings, 1 for each image in the layer
        "Image settings list": [
            # Image settings for first image
            {}
        ]
    }

Or, flattening the JSON Layer object:

    {"Image settings list": [{}]}

## General format - selectively override default settings

The general principle is that the default layer settings are used for each layer except where they are overridden. For a given layer, any additional parameters provided beyond the minimal JSON layer object above will override the corresponding default layer settings. An example is shown below.

Note: A `"Comment"` tag can be put into any object and it will be ignored.

    {
        "Header": {
            "Schema version": "5.0.0",
            "Image directory": "slices"
        },
        "Design": {
            "User": "Jane Doe",
            "Purpose": "Test coupon",
            "Description": "Multi-exposure layer with new schema fields"
        },
        "Variables": {
            "base_exposure_ms": 500,
            "post_wait_ms": 100
        },
        "Default layer settings": {
            "Number of duplications": 1,
            "Position settings": {
                "Layer thickness (um)": 10,
                "Distance up (mm)": 1.0,
                "Initial wait (ms)": 100.0,
                "BP up speed (mm/sec)": 25.0,
                "BP up acceleration (mm/sec^2)": 50.0,
                "Up wait (ms)": 0,
                "BP down speed (mm/sec)": 20.0,
                "BP down acceleration (mm/sec^2)": 50.0,
                "Final wait (ms)": 0
            },
            "Image settings": {
                "Image file": "default_image.png",
                "Layer exposure time (ms)": "${base_exposure_ms}",
                "Light engine": "visitech",
                "Light engine wavelength (nm)": 365,
                "Light engine power setting": 100
                "Relative focus position (um)": 0,
                "Wait before exposure (ms)": 0,
                "Wait after exposure (ms)": "${post_wait_ms}"
            }
        },
        "Named position settings": {
            "fast_peel": {
                "BP up speed (mm/sec)": 40,
                "BP down speed (mm/sec)": 30
            }
        },
        "Named image settings": {
            "high_power": {
                "Light engine power setting": 250
            }
        },
        "Layers": [
            {
                "Comment": "Override layer thickness, up distance, & exposure time",
                "Position settings": {
                    "Layer thickness (um)": 3.3,
                    "Distance up (mm)": 1.2
                },
                "Image settings list": [
                    {
                        "Image file": "0000.png",
                        "Layer exposure time (ms)": 10000
                    }
                ]
            },
            {
                "Comment": "Override exposure time and use a named image preset",
                "Image settings list": [
                    {
                        "Using named image settings": "high_power",
                        "Image file": "0001.png",
                        "Layer exposure time (ms)": 5000
                    }
                ]
            },
            {
                "Comment": "Override number of duplications and use named position settings",
                "Number of duplications": 50,
                "Position settings": {
                    "Using named position settings": "fast_peel"
                },
                "Image settings list": [
                    {
                        "Image file": "0002.png"
                    }
                ]
            },
            {
                "Comment": "Use 4 images for this layer, with x/y offsets",
                "Image settings list": [
                    {
                        "Image file": "0053.png",
                        "Layer exposure time (ms)": 400,
                        "Image x offset (um)": 0,
                        "Image y offset (um)": 0,
                    },
                    {
                        "Image file": "0053a.png",
                        "Layer exposure time (ms)": 200,
                        "Image x offset (um)": 2500,
                        "Image y offset (um)": 0
                    },
                    {
                        "Image file": "0053b.png",
                        "Layer exposure time (ms)": 100,
                        "Image x offset (um)": 0,
                        "Image y offset (um)": 2500
                    },
                    {
                        "Image file": "0053c.png",
                        "Layer exposure time (ms)": 200,
                        "Image x offset (um)": 2500,
                        "Image y offset (um)": 2500
                    }
                ]
            },
            {
                "Comment": "Break 10 um layer into a 5 um layer for one image followed by another 5 um layer everywhere else for the next images. The first 5 um layer could cover only a small area of the projected image while the next 5 um layer could have one or more images that cover much or all of the rest of the image area in which case those regions are actually a 10 um layer because the first 5 um layer did not polymerize any resin there.",
                "Position settings": {
                    "Layer thickness (um)": 5
                },
                "Image settings list": [
                    {
                        "Image file": "0054a.png",
                        "Layer exposure time (ms)": 200
                    }
                ]
            },
            {
                "Comment": "Second 5 um layer",
                "Position settings": {
                    "Layer thickness (um)": 5
                },
                "Image settings list": [
                    {
                        "Image file": "0054.png",
                        "Layer exposure time (ms)": 400,
                        "Special image techniques": {
                            "0 um layer": {
                                "Enable 0 um layer": true,
                                "Number of duplications": 2
                            }
                        }
                    },
                    {
                        "Image file": "0054b.png",
                        "Layer exposure time (ms)": 200
                    },
                    {
                        "Image file": "0054c.png",
                        "Layer exposure time (ms)": 275
                    }
                ]
            },
            {
                "Image settings list": [
                    {
                        "Image file": "0055.png"
                    }
                ]
            },
            {
                "Image settings list": [
                    {
                        "Image file": "0056.png"
                    }
                ]
            },
            {
                "Image settings list": [
                    {
                        "Image file": "0057.png"
                    }
                ]
            },
            {
                "Image settings list": [
                    {
                        "Image file": "0058.png"
                    }
                ]
            },
            {
                "Image settings list": [
                    {
                        "Image file": "0059.png"
                    }
                ]
            },
            {
                "Comment": "Override number of duplications",
                "Number of duplications": 20,
                "Image settings list": [
                    {
                        "Image file": "0060.png"
                    }
                ]
            }
        ]
    }

## New JSON v5.0 features and how to use them

### Design metadata
Add design provenance and context (including the newly added `User` field):

    "Design": {
        "User": "Jane Doe",
        "Purpose": "Prototype",
        "Description": "Bioresorbable scaffold",
        "Resin": "PEGDA",
        "3D printer": "HR5",
        "Design file": "<filepath>",
        "STL file": "<filepath>",
        "Slicer": "Custom",
        "Date": "2026-01-16"
    }

### Variables
Define variables in the top-level `Variables` object and reference them anywhere in the file using `${var_name}`. These can be integers, float, booleans, or strings. If variable is numerical, math can be preformed inside the reference `${var_name * 2}`:

    "Variables": {
        "base_exposure_ms": 550,
        "focus_offset_um": -10
    }

    "Image settings": {
        "Layer exposure time (ms)": "${base_exposure_ms}",
        "Relative focus position (um)": "${focus_offset_um}"
    }

### Named settings and named defaults
Define reusable settings and reference them by name:

**Precedence (highest to lowest)**

- **Image settings:** per-exposure overrides in `Image settings list` → `Using named image settings` → `Using named default image settings` (layer-level) → `Default layer settings` → schema defaults.
- **Position settings:** per-layer overrides in `Position settings` → `Using named position settings` → `Default layer settings` → schema defaults.

```
    "Named position settings": {
        "fast_peel": {
            "BP up speed (mm/sec)": 40,
            "BP down speed (mm/sec)": 30
        }
    }

    "Named image settings": {
        "defocus": {
            "Relative focus position (um)": 100
        },
        "low exposure": {
            "Layer exposure time (ms)": 200
        }
    }

    "Layers": [
        {
            "Position settings": {
                "Using named position settings": "fast_peel"
            },
            "Using named default image settings": "defocus",
            "Image settings list": [
                {"Image file": "0001.png"},
                {
                    "Image file": "0002.png",
                    "Using named image settings": "low exposure"
                },
            ]
        }
    ]
```

### Named layer groups (with variable overrides)
Define a layer sequence once and reuse it in `Layers`. You can override global `Variables` per group call:

    "Named layer groups": {
        "base_stack": [
            {"Image settings list": [{"Image file": "base_000.png"}]},
            {"Image settings list": [{"Image file": "base_001.png"}]}
        ]
    },

    "Layers": [
        {
            "Using named layer group": "base_stack",
            "Variables": {"base_exposure_ms": 700}
        }
    ]

### Special techniques
Special techniques are available at the print, layer, and image levels:

    "Special print techniques": {
        "Print under vacuum": {
            "Enable vacuum": true,
            "Target vacuum level (Torr)": 10,
            "Vacuum wait time (sec)": 30
        }
    }

    "Position settings": {
        "Special layer techniques": {
            "Squeeze out resin": {
                "Enable squeeze": true,
                "Squeeze count": 2,
                "Squeeze force (N)": 40,
                "Squeeze time (ms)": 200
            }
        }
    }

    "Image settings list": [
        {
            "Image file": "0200.png",
            "Special image techniques": {
                "0 um layer": {
                    "Enable 0 um layer": true,
                    "Number of duplications": 3
                },
                "Print on film": {
                    "Enable print on film": true,
                    "Distance up (mm)": 0.3,
                    "Wait before exposure (ms)": 20000
                }
            }
        }
    ]

### Multiple light engines and wavelengths
Each exposure can target a specific engine and wavelength:

    "Image settings list": [
        {
            "Image file": "0300.png",
            "Light engine": "visitech",
            "Light engine wavelength (nm)": 405
        },
        {
            "Image file": "0301.png",
            "Light engine": "wintech",
            "Light engine wavelength (nm)": 365
        }
    ]

### X/Y stages, stitching, grayscale correction, and mirroring
Use x/y offsets per exposure to enable stitching or scanning, and enable grayscale correction per image:

    "Image settings list": [
        {
            "Image file": "0400.png",
            "Image x offset (um)": 0,
            "Image y offset (um)": 0,
            "Do grayscale correction": true,
            "Mirror image short axis": false,
            "Mirror image long axis": false
        },
        {
            "Image file": "0400.png",
            "Image x offset (um)": 2500,
            "Image y offset (um)": 0,
            "Do grayscale correction": true
        }
    ]


<a rel="license" href="http://creativecommons.org/licenses/by/4.0/"><img alt="Creative Commons License" style=" border-width:0" src="https://i.creativecommons.org/l/by/4.0/88x31.png" /></a><br />This work is  licensed under a <a rel="license" href="http://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 International License</a>.

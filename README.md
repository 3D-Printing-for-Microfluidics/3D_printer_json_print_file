# SLA 3D Printer Control File Standard

The purpose of this repository is to document a file standard for conveying 3D print information to a SLA 3D printer for how to process each individual image of a print. Traditionally SLA 3D printers only expose a single image per layer, and have the same layer thickness for each layer. Control files following the format we outline in this repository will allow each layer to be comprised of multiple images, with the ability to customize what each image's exposure time is, as well as customizing each layer's thickness.

Overall, following this file standard gives a much higher degree of control over how a design is printed compared to traditional 3D printing methods.

### Example API

For convenience, a python class that contains a basic API for interfacing with the file format has been included in the repository (see `ControlFile.py`). It should be straightforward to incorporate into a preexisting python project, however, due to the inherent variability between 3D printer setups, values in the main dictionary that relate directly to the 3D printing mechanism itself have intentionally been left undefined so that the standard can be adapted to any 3D printing mechanism that offers the required operational flexibility.

## File format and explanation

This information can also be found in `example.json`
```
{
  "Design": {
    "Purpose": "String with short statement about design's purpose.",
    "Description": "String containing description of design to be printed with this JSON file. Could be multi-line by using '\n' to separate lines.",
    "Resin": "Resin that this design is intended to be used with. Example: PEGDA with 2% NPS and 1% Irgacure 819.",
    "3D printer": "3D printer that this design is intended to be printed on.",
    "Design file": "<filename> (OpenSCAD or other 3D CAD file containing design)",
    "STL file": "<filename>",
    "Slicer": "Specify which slicer was used to create png images from STL file.",
    "Date": "Date file was sliced."
  },
  "Header": {
    "Comment": "This section contains information about the schema and the directory where to find images, which is specified relative to the directory in which this json file resides. If the json file \nis in the same directory as the png images, this would be `.`",
    "Schema version": "0.1",
    "Image directory": "slices"
  },
  "Default settings": {
    "Comment": "Default settings for the Printer. Unless otherwise defined in the layer, these are the values that are to be used for each layer.",
    "Light engine power setting": 100,
    "Build stage movement Speed (mm/min)": 400,
    "Separation mechanism movement speed (mm/min)": 400,
    "Layer thickness (um)": 10,
    "Layer exposure time (ms)": 400,
    "Number of duplications": 1
  },
  "Layers": [
    {
      "Images": [
        "filename000.png"
      ],
      "Layer exposure times (ms)": [
        20000
      ],
      "Layer thickness (um)": 20,
      "Comment": "This layer has defined a custom thickness, which will impact the distance that the build platform moves."
    },
    {
      "Images": [
        "filename000.png"
      ],
      "Layer exposure times (ms)": [
        10000
      ],
      "Number of duplications": 2,
      "Comment": "This layer needs to be reproduced twice beyond the initial exposure."
    },
    {
      "Images": [
        "filename000.png"
      ],
      "Layer exposure times (ms)": [
        5000
      ],
      "Power Setting": 200,
      "Comment": "This layer requires the LED power setting to be higher than the default."
    },
    {
      "Images": [
        "filename000.png"
      ],
      "Layer exposure times (ms)": [
        1000
      ]
    },
    {
      "Images": [
        "filename001.png"
      ]
    },
    {
      "Images": [
        "filename002.png"
      ]
    },
    {
      "Images": [
        "filename003.png"
      ]
    },
    {
      "Images": [
        "filename004.png",
        "filename004a.png"
      ],
      "Layer exposure times (ms)": [
        400,
        200
      ],
      "Comment": "Channel layer 1"
    },
    {
      "Images": [
        "filename005.png",
        "filename005a.png"
      ],
      "Layer exposure times (ms)": [
        400,
        200
      ],
      "Comment": "Channel layer 2"
    },
    {
      "Images": [
        "filename006.png",
        "filename006a.png"
      ],
      "Layer exposure times (ms)": [
        400,
        200
      ],
      "Comment": "Channel layer 3"
    },
    {
      "Images": [
        "filename007.png",
        "filename007a.png"
      ],
      "Layer exposure times (ms)": [
        400,
        200
      ],
      "Comment": "Channel ceiling layer 1"
    },
    {
      "Images": [
        "filename008.png",
        "filename008a.png"
      ],
      "Layer exposure times (ms)": [
        400,
        200
      ],
      "Comment": "Channel ceiling layer 2"
    },
    {
      "Images": [
        "filename009.png",
        "filename009a.png"
      ],
      "Layer exposure times (ms)": [
        400,
        200
      ],
      "Comment": "Channel ceiling layer 3"
    },
    {
      "Layer thickness (um)": 5,
      "Images": [
        "filename010.png",
        "filename010a.png"
      ],
      "Layer exposure times (ms)": [
        250,
        150
      ]
    },
    {
      "Layer thickness (um)": 7.5,
      "Images": [
        "filename011.png",
        "filename011a.png"
      ],
      "Layer exposure times (ms)": [
        300,
        175
      ]
    },
    {
      "Layer thickness (um)": 8,
      "Images": [
        "filename012.png",
        "filename012a.png"
      ],
      "Layer exposure times (ms)": [
        350,
        190
      ]
    },
    {
      "Images": [
        "filename013.png"
      ]
    },
    {
      "Images": [
        "filename014.png"
      ]
    },
    {
      "Images": [
        "filename015.png"
      ]
    }
  ]
}
```

<a rel="license" href="http://creativecommons.org/licenses/by/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 International License</a>.

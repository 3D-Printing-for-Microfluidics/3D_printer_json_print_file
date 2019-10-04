# SLA 3D Printer Control File Standard

The purpose of this repository is to document a file standard for conveying 3D print information to a SLA 3D printer for how to process each individual image of a print. Traditionally SLA 3D printers only expose a single image per layer, and have the same layer thickness for each layer. Control files following the format we outline in this repository will allow each layer to be comprised of multiple images, with the ability to customize what each image's exposure time is, as well as customizing each layer's thickness.

Overall, following this file standard gives a much higher degree of control over how a design is printed compared to traditional 3D printing methods.

### Example API

For convenience, a python class that contains a basic API for interfacing with the file format has been included in the repository (see `ControlFile.py`). It should be straightforward to incorporate into a preexisting python project, however, due to the inherent variability between 3D printer setups, values in the main dictionary that relate directly to the 3D printing mechanism itself have intentionally been left undefined so that the standard can be adapted to any 3D printing mechanism that offers the required operational flexibility.

## File format and explanation

This information can also be found in [`print_settings.py`](https://github.com/gregnordin/3D_printer_control/blob/master/printer_server/printer_server/printer/print_settings.py)

Standard for Print Job
======================
JSON File
---------
Boilerplate
^^^^^^^^^^^
The JSON file contains all the information needed for a print 
besides the images. Here is a most simplified version, namely, 
all the entries are necessary. ::
    {
      "Header": {
        "Schema version": "0.1",
        "Image directory": "slices"
      },
      "Default settings": {
        "Light engine power setting": 100,
        "Layer exposure time (ms)": 400,
        "Layer thickness (um)": 10,
        "Number of duplications": 1,
        "Solus command chain": [
          "WAIT 0.1",
          "BP UP 1 SPEED 300",
          "QW DOWN 6 SPEED 400",
          "WAIT 1.5",
          "BP UP 2 SPEED 400",
          "QW UP 6 SPEED 400",
          "BP DOWN 3 SPEED 400",
          "WAIT 1.5"
        ]
      },
      "Layers": [
        {
          "Images": [
            "0000.png"
          ]
        }
      ]
    }
**Explanation of all entries**
#. Header
    #. Schema version - for backward compatibility
    #. Image directory - relative the directory of JSON file
#. Default settings - Default values
    #. Light engine power setting - an integer between 0 and 1000
    #. Layer exposure time (ms)
    #. Layer thickness (um)
    #. Number of duplications - If a number of consective layers 
       share the same images and parameters, we can set 
       ``Number of duplications`` to reduce json file footprint.
    #. Solus command chain - command chain 
       to tell solus how to move BP and QW. 
       (Details: :ref:`solus_command_chain`)
#. Layers - a list of layer settings. Each item in the list 
   is corresponding to multiple layers, when 
   ``Number of duplications`` is greater than 1.
.. _solus_command_chain:
Solus command chain
^^^^^^^^^^^^^^^^^^^
The Solus movement starts from right after exposure, and ends 
right before another exposure. Here, a new API for moving build 
platform and quartz window is introduced. With the new API, any 
arbitrary combination of movements can be implemented by 
chaining a list of commands. 
**Command format examples**
* Wait (WAIT)
    * Wait 1.5 seconds
        * ``WAIT 1.5``
* Build Platform (BP)
    * Move build platform up 1 mm at 300 mm/min
        * ``BP UP 1 SPEED 300``
    * Move build platform down 1.5 mm at 400 mm/min
        * ``BP DOWN 1.5 SPEED 400``
* Quartz Window (QW)
    * Move quartz window up 2 mm at 500 mm/min
        * ``QW UP 1.5 SPEED 500``
    * Move quartz window down 1 mm at 600 mm/min
        * ``QW DOWN 1 SPEED 600``
**Rules**
We can almost chain commands however we want to, but there are 
still some rules.
* ``BP`` rules
    #. Speed must be positive integer.
    #. Max speed: 800 mm/min
    #. The total distance of ``BP UP`` should be the same as 
       ``BP DOWN``. 
    #. The build platform absolute position should always be 
       between layer position and 90 mm. 
* ``QW`` rules
    #. Speed must be positive integer.
    #. Max speed: 800 mm/min
    #. The total distance of ``QW UP`` should be the same as 
       ``QW DOWN``.
    #. The quartz window absolute position should always be 
       between 0 and 6 mm. 
.. Note::
    Because ``BP UP`` distance is equal to ``BP DOWN`` distance, 
    there is not a new layer of resin between the printed part 
    and the teflon film. But it is taken care of by 
    Solus.printCycle method, where it automatically reduce the 
    last ``BP DOWN`` distance by the layer thickness.
JSON with extra information and customized layer settings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Besides basic information, we can add detailed description under 
other entries. This extra information does not affect the print 
in any way. Example ::
    {
      "Design": {
        "Purpose": "String with short statement about design's 
                    purpose.",
        "Description": "String containing description of design 
                        to be printed with this JSON file. Could 
                        be multi-line by using '\\n' to separate 
                        lines.",
        "Resin": "Resin that this design is intended to be used 
                  with. Example: PEGDA with 2% NPS and 1% 
                  Irgacure 819.",
        "3D printer": "3D printer that this design is intended 
                       to be printed on.",
        "Design file": "<filename> (OpenSCAD or other 3D CAD file 
                        containing design)",
        "STL file": "<filename>",
        "Slicer": "Specify which slicer was used to create png 
                   images from STL file.",
        "Date": "Date file was sliced."
      },
      "Header": {
        "Comment": "This section contains information about the 
                    schema and the directory where to find images, 
                    which is specified relative to the directory 
                    in which this json file resides. If the json 
                    file is in the same directory as the png 
                    images, this would be `.`",
        "Schema version": "0.1",
        "Image directory": "slices"
      }
      "Default settings": {
        "Comment": "Default settings for the Printer. Unless 
                    otherwise defined in the layer, these are 
                    the values that are to be used for each 
                    layer.",
        "Light engine power setting": 100,
        "Layer exposure time (ms)": 400,
        "Layer thickness (um)": 10,
        "Number of duplications": 1,
        "Solus command chain": [
          "WAIT 0.1",
          "BP UP 1 SPEED 300",
          "QW DOWN 6 SPEED 400",
          "WAIT 1.5",
          "BP UP 2 SPEED 400",
          "QW UP 6 SPEED 400",
          "BP DOWN 3 SPEED 400",
          "WAIT 1.5"
        ]
      },
      "Layers": [
        {
          "Images": [
            "0000.png"
          ],
          "Layer exposure time (ms)": [
            20000
          ],
          "Layer thickness (um)": 20,
          "Comment": "This layer has a custom exposure time and 
                      layer thickness."
        },
        {
          "Images": [
            "0000.png"
          ],
          "Layer exposure time (ms)": [
            10000
          ],
          "Number of duplications": 2,
          "Comment": "This layer is duplicated twice, which means 
                      it is actually for layer 2 and 3."
        },
        {
          "Images": [
            "0000.png"
          ],
          "Layer exposure time (ms)": [
            5000
          ],
          "Light engine power setting": [
            200
          ],
          "Comment": "This layer has custom light engine power 
                      setting."
        },
        {
          "Images": [
            "0001.png",
            "0001a.png"
          ],
          "Comment": "This layer exposes 2 images using default 
                      settings."
        },
        {
          "Images": [
            "0002.png",
            "0002a.png"
          ],
          "Layer exposure time (ms)": [
            400,
            200
          ],
          "Comment": "This layer exposes 2 images with different 
                      exposure times."
        },
        {
          "Images": [
            "0003.png",
            "0003a.png"
          ],
          "Light engine power setting": [
            200,
            400,
          ],
          "Comment": "This layer exposes 2 images with different 
                      light engine power settings."
        },
        {
          "Images": [
            "0004.png",
            "0004a.png"
          ],
          "Layer exposure time (ms)": [
            400,
            200
          ],
          "Light engine power setting": [
            200,
            400,
          ],
          "Comment": "This layer exposes 2 images with different 
                      exposure times and light engine power 
                      settings."
        },
        {
          "Images": [
            "0005.png"
          ],
          "Solus command chain": [
            "WAIT 0.1",
            "BP UP 3 SPEED 300",
            "QW DOWN 6 SPEED 400",
            "WAIT 1.5",
            "QW UP 6 SPEED 400",
            "BP DOWN 3 SPEED 400",
            "WAIT 1.5"
          ],
          "Comment": "The layer has its own command chain to 
                      control Solus."
        },
        {
          "Images": [
            "0006.png"
          ],
          "Comment": "A normal layer"
        }
      ]
    }
We can customize any layer by override the default values. In 
the above JSON file, the first list item in ``Layers`` contains 
``Layer exposure time (ms)`` and ``Layer thickness (um)``, 
which means the first layer will have exposure time of 20000 ms 
and layer thickness of 20 um. Note that a number of consective 
layers can share one list item by making 
``Number of duplications`` greater than 1. The purpose is to 
reduce repetitive information. For instance, in the second list 
item above, ``Number of duplications`` is 2, which is mapped to 
layer 2 and 3. 
Also, a layer can expose however many images. For every image, 
you can set exposure times and light engine power settings, 
repectively. If so, every image must have an exposure time. Same 
for light engine power setting. 
Format of A Print Job
---------------------
To submit a print job to the 3D printer, a ZIP file is the only 
format the 3D printer accepts. This ZIP file should contain only 
one JSON file, named ``print_settings.json``, and all the images 
that will be used for this print job. The file structure in the 
ZIP file should be as following ::
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
The name of the JSON file must be ``print_settings.json``, and 
the names of the images and image folder name need to match what 
is specified in the json file. 
.. Note::
    After the ZIP file is extracted, the JSON file directory will 
    be used as the root directory. Image directory is relative 
    to the root directory. 
```

<a rel="license" href="http://creativecommons.org/licenses/by/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 International License</a>.

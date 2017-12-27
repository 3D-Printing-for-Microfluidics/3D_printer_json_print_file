import json, re, os, platform
import glob
from pathlib import Path

class Variables:
    """
    contains all the enviroment variables for the controller software
    """

    def __init__(self):
        # get the correct directory separator
        if platform.system() is 'Windows':
            self.slash = "\\"
        else:
            self.slash = "/"
        self.jsonVar = {
            "settings": {
                "myPrinterSettings": {}, # customize your variables here
                "general": {
                    "burn in time": 1000,
                    "burn in layers": 1,
                    "default exposure time ms": 100,
                    "default duplicates": 1,
                    "default thickness um": 5,
                    "image path": ""
                }
            },
            "layers": {} # stores layer information. This will be automatically generate when
                         # either self.createLayers or self.importJson is called
        }

        self.addGettersSetters()

    def getAll(self):
        return self.jsonVar


    ######################### settings #########################


    def getSettings(self):
        return self.jsonVar["setttings"]

    def getMyPrinterSettings(self):
        return self.jsonVar["settings"]["myPrinterSettings"]

    def setMyPrinterSettings(self, params):
        self.jsonVar["settings"]["myPrinterSettings"] = params

    def addGettersSetters(self):
        def makegetter(self, x, y):
            def func():
                return self.jsonVar["settings"][x][y]
            return func

        def makesetter(self, x, y):
            def func(arg):
                self.jsonVar["settings"][x][y] = arg
            return func

        for key in self.jsonVar['settings']['general']:
            self.__dict__['get{}'.format(key.title().replace(' ', ''))] = makegetter(self, 'general', key)
            self.__dict__['set{}'.format(key.title().replace(' ', ''))] = makesetter(self, 'general', key)

        for key in self.jsonVar['settings']['myPrinterSettings']:
            self.__dict__['get{}'.format(key.title().replace(' ', ''))] = makegetter(self, 'general', key)
            self.__dict__['set{}'.format(key.title().replace(' ', ''))] = makesetter(self, 'general', key)


    ######################### layers #########################


    def getLayers(self):
        return self.jsonVar["layers"]

    def getNumLayers(self):
        return len(self.getLayers())

    def getLayer(self, layerNum):
        return self.jsonVar["layers"][layerNum]

    def getLayerImageFiles(self, layerNum):
        return self.jsonVar["layers"][layerNum]["image files"]

    def getNumImages(self, layerNum):
        return len(self.getLayerImageFiles(layerNum))

    def getLayerExposureTimes(self, layerNum):
        return self.jsonVar["layers"][layerNum]["exposure times (ms)"]

    def getLayerThickness(self, layerNum):
        return self.jsonVar["layers"][layerNum]["thickness"]

    def getDuplicates(self, layerNum):
        """
        Even though this is stored as an array, all the values will be the same.
        """
        return self.jsonVar["layers"][layerNum]["duplicates"][0]

    def doesLayerExist(self, layerNum):
        if layerNum in self.jsonVar["layers"]:
            return True

    def setLayers(self, layers):
        self.jsonVar["layers"] = layers

    def setLayerImageFiles(self, layerNum, images):
        """
        images must be an array of strings
        """
        self.jsonVar["layers"][layerNum]["image files"] = images

    def setLayerExposureTimes(self, layerNum, times):
        """
        times must be an array of integers
        """
        self.jsonVar["layers"][layerNum]["exposure times (ms)"] = times

    def setLayerThickness(self, layerNum, thickness):
        """
        thickness must be an array of integers
        """
        self.jsonVar["layers"][layerNum]["thickness"] = thickness

    def setDuplicates(self, layerNum, num):
        self.jsonVar["layers"][layerNum]["duplicates"] = num

    def createLayers(self, imgDir):
        """
        Given an image directory, all values for the layers sub dictionary
        will be generated.
        """
        # reset the layers
        self.jsonVar['layers'] = {}
        # set the path
        self.setImagePath(imgDir)
        # get the layer names and put them in alpha numberical order
        imageNames = glob.glob(os.path.join(imgDir, '*.png'))
        for image in imageNames:
            # TODO: filter out any non-png items in the directory
            image = os.path.basename(image)
            layerNum = int(re.findall(r'\d+', image)[0])
            # determine if layer is in part of the burn in layer.
            # otherwise give it a regular exposure
            if layerNum < self.getBurnInLayers():
                burnIn = self.getBurnInTime()
            else:
                burnIn = self.getDefaultExposureTimeMs()
            # if the dictionary entry already exists
            if layerNum in self.jsonVar['layers']:
                self.jsonVar['layers'][layerNum]['image files'].append(image)
                self.jsonVar['layers'][layerNum]['exposure times (ms)'].append(
                    burnIn)
                self.jsonVar['layers'][layerNum]['thickness'].append(
                    self.getDefaultThicknessUm())
                self.jsonVar['layers'][layerNum]['duplicates'].append(
                    self.getDefaultDuplicates())
            # otherwise create a new dictionary entry
            else:
                self.jsonVar['layers'][layerNum] = {
                    "image files": [image],
                    "exposure times (ms)": [burnIn],
                    "thickness": [self.getDefaultThicknessUm()],
                    "duplicates": [1]
                }

    def getMyPrinterSettings(self, layerNum):
        """
        Returns all the settings under 'settings->solus'.

        Thickness also is added and set by default to the first thickness value in the specified layer's thickness
        array.

        In the case of 'general->variable thickness' being set to True, thickness value will need to be manually set.
        """
        settings = self.getMyPrinterSettings().copy()
        layer = self.getLayer(layerNum)
        # check if layer specifies a solus param
        for key in layer:
            if key in self.getSolus():
                settings[key] = layer[key]
        settings["thickness"] = self.getLayerThickness(layerNum)[0]
        print("my printer settings for layer: ", layerNum, " \n", settings)
        return settings

    def makeImagePath(self, image):
        return self.getImagePath() + self.slash + image


    ######################### Json #########################


    def exportJson(self, fileName):
        with open(fileName, 'w') as f:
            json.dump(self.jsonVar, f, indent=4)

    def importJson(self, fileName):
        """
        Raises ValueError if given a bad Json file
        A bad json file can include one that lists a not existant path or images
        """
        jsonfile = open(fileName)
        dic = json.load(jsonfile)
        try:
            # checks if the given imported path and associated files exist
            path = dic["settings"]["general"]["image path"] + self.slash
            for key, value in dic["layers"].items():
                for i in range(len(value["image files"])):
                    testFile = Path(path + value["image files"][i])
                    if not testFile.exists():
                        raise ValueError
            # assign values
            self.jsonVar["settings"] = dic["settings"]
            # add the layers in order, otherwise the dictionary shuffles them
            for i in range(len(dic["layers"])):
                self.jsonVar["layers"][i] = dic["layers"][str(i)]
        except ValueError as e:
            raise

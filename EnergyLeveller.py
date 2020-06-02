#!/opt/local/bin/python
# coding=UTF-8

"""
Energy Leveller version 2.0  (2019)

This code is shared under the MIT license Copyright 2019 James Furness.
You are free to use, modify and distribute the code, though recognition of my effort is appreciated!
"""
from __future__ import print_function
import sys
import os.path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def getEnergy(state):
    # sort key
    return state.energy

class Diagram:
    """
    Holds global values for the diagram and handles drawing.
    """
    def __init__(self, width, height, fontSize, outputName):
        self.width = width
        self.height = height
        self.outputName = outputName
        # latex font 
        plt.rcParams.update({'font.size': fontSize})
        plt.rcParams.update({'font.family': 'serif'})
        plt.rcParams.update({'text.usetex': True})

        # to be upgraded once I know all the answers
        # size of a font in the axis coordinates units
        self.fontSpacing = 0.12
        # extra space between text -- this is only a scaling factor
        self.interspacing = 0.4

        #self.fig = plt.figure(figsize=(self.width, self.height))
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111)
       
        self.columnWidth = 1.0
        
        self.statesList  = {}
        self.dashes      = [6.0,3.0] # ink, skip
        self.columns     = 0
        self.energyUnits = ""
        self.do_legend   = False
        self.COLORS      = {}
        

    def AddState(self, state):
        state.name = state.name.upper()
        state.color = state.color.upper()
        state.labelColor = state.labelColor.upper()
        state.linksTo = state.linksTo.upper()
        if state.legend is not None:
            self.do_legend = True
        if state.name not in self.statesList:
            self.statesList[state.name] = state
        else:
            print("ERROR: States must have unique names. State " + state.name + " is already in use!")
            raise ValueError("Non unique state names.")

    def DetermineEnergyRange(self):
        # this is never used
        if len(self.statesList) == 0:
            raise ValueError("No states in diagram.")
        maxE = -10E20
        minE = 10E20
        for state in self.statesList.keys():
            if state.energy > maxE:
                maxE = state.energy
            if state.energy < minE:
                minE = state.energy
        self.axesTop = maxE
        self.axesMin = minE
        self.axesOriginNormalised =  1+(minE / (maxE - minE)) 
        return [minE, maxE]

    def MakeLeftRightPoints(self):
        columnWidth = self.columnWidth

        for state in self.statesList.values():
            state.leftPointx = state.column*columnWidth + state.column*columnWidth/2.0
            state.leftPointy = state.energy
            state.rightPointx = state.leftPointx + columnWidth
            state.rightPointy = state.energy
            state.labelPosition = state.energy

    def MaxColumnNo(self):
        # find smallest and largest column number
        maxcol = -1
        for _, state in self.statesList.items():
            if state.column > maxcol:
                maxcol = state.column
        return maxcol

    def MinColumnNo(self):
        # find smallest and largest column number
        mincol = 100
        for state in self.statesList.values():
            if state.column < mincol:
                mincol = state.column
        return mincol

    def FindPositionHelperIsCrowded(self, column):
        fontSpacing = self.fontSpacing
        crowded = False
        # check for overlaps
        column.sort(key = getEnergy) 
        for i, state in enumerate(column):        
            if i > 0 and column[i-1].labelPosition + fontSpacing > state.labelPosition:
                column[i-1].isCrowded = True
                state.isCrowded = True 
                crowded = True
            else:
                state.isCrowded = False
        return column, crowded
    
    def ResolveCrowded(self, column):
        first_crowded = len(column)
        last_crowded = -1
        for i in range(len(column)):
            # he first is not yet detected
            if first_crowded == len(column):
                # first catch
                if column[i].isCrowded:
                    first_crowded = i
            # the last is not yet detected
            elif last_crowded == -1:
                # there is a catch 
                if not column[i].isCrowded:
                    last_crowded = i-1
                # or the end of the list
                elif i == len(column)-1:
                    last_crowded = i
                    
            # the last crowded was detected, time to make some space
            if last_crowded != -1:
                bottom = column[first_crowded].labelPosition
                top    = column[last_crowded].labelPosition + self.fontSpacing
                middle = bottom + (top-bottom)/2.0
                demand = (last_crowded - first_crowded + 1) * self.fontSpacing
                demand *= 1.4
                newStart= middle - 0.5 * demand
                for i in range(first_crowded, last_crowded+1):
                    # first `i` is first_crowded
                    # last `i` is last_crowded
                    howMuchUp = (i - first_crowded) * self.fontSpacing * 1.4
                    column[i].labelPosition = newStart + howMuchUp
                # make sure that labels fit into the graph
                newTop = column[last_crowded].labelPosition + self.fontSpacing  
                roof   = self.ax.get_ylim()[1]
                if newTop > roof:
                    stickOut = newTop - roof
                    # shift them down
                    for i in range(first_crowded, last_crowded + 1):
                        column[i].labelPosition -= stickOut
                # continue searching for conflicts
                last_crowded = -1
                first_crowded = len(column)
        return column
        
    def updatePositions(self, column):
        # brute force
        for i in range(len(column)):
            name = column[i].name
            for key, state in self.statesList.items() :
                if state.name == name:
                    self.statesList[key] = column[i]
                    break
        
    def FindLabelPosition(self):
        # make sure that labels don't overlap
        maxcol = self.MaxColumnNo()
        mincol = self.MinColumnNo()
        # go over each column and assing positions in each of them separately
        for c in range(mincol, maxcol+1):    
            column = []
            for key, state in self.statesList.items():
                if state.column == c:
                    column.append(state)
            if len(column) == 0:
                continue
            # loop over the states and push them away until you remove overlaps
            while True:
                column, crowded = self.FindPositionHelperIsCrowded(column)
                if not crowded:
                    self.updatePositions(column)
                    break
                # its crowded
                column = self.ResolveCrowded(column)

    def DrawCanvas(self):
    # Positions of text are manipulated so it has to be called more than once
        # set x lims
        maxcol = self.MaxColumnNo()
        xleft  = -0.5*self.columnWidth
        xright = (maxcol+2.5)*self.columnWidth
        self.ax.set_xlim(xleft, xright)
        self.ax.set_ylabel(str(self.energyUnits))
        self.ax.set_xticks([])
        self.fig.tight_layout()
        self.fig.canvas.draw()

    def DrawBars(self):
        #   Draw states' bars to indicate energy level
            # bar is only 2/7 of the state space
        for state in self.statesList.values():
            length = state.rightPointx - state.leftPointx
            left = state.leftPointx + 2.0/7.0*length
            right = state.leftPointx + 4.0/7.0*length
            self.ax.plot([left, right], 
                         [state.leftPointy, state.rightPointy], 
                         c=state.color, 
                         lw=3, 
                         ls='-')

    def DrawLabels(self):
        #   Draw states' labels to the right from energy bars
        length = self.columnWidth 
        xoffset = length*5.0/7.0
        
        for key, state in self.statesList.items():
            self.ax.text(state.leftPointx + xoffset, 
                    state.labelPosition,
                    state.label,
                    color=state.labelColor,
                    verticalalignment='center')

    def DrawEnergies(self):
        #   Draw states' energies to the left from energy bars
        length = self.columnWidth 
        xoffset = -length*1.75/7.0
        for state in self.statesList.values():
            self.ax.text(state.leftPointx + xoffset, 
                state.labelPosition,
                f"{state.energy:4.2f}",
                color=state.labelColor,
                verticalalignment='center')

    def DrawConnections(self):
        length = self.columnWidth 
        font = 0.14 * self.fontSpacing           
        for state in self.statesList.values():
            label = state.labelPosition
            energy = state.energy
            # aim at the middle of the text
            if energy != label:
                left = state.leftPointx 
                energyRight = length*1.1/7.0 
                barLeft = length*1.85/7.0 
                barRight = length*4.15/7.0
                labelLeft = length*4.85/7.0
                
                col = state.color
                lin = '-'
                wid = 0.5
                mar = ','
                
                self.ax.plot([left + energyRight, left + barLeft],
                    [label + font, energy], 
                    c = col, ls = lin, lw = wid, marker = mar)
                
                self.ax.plot([left + barRight, left + labelLeft],
                    [energy, label + font],
                    c = col, ls = lin, lw = wid, marker = mar)

    def Save(self):
        self.fig.savefig(fname = "singlets.eps", 
                         format = 'eps')

class State:
    def __init__(self):
        self.name        = ""
        self.color       = ""
        self.labelColor  = ""
        self.linksTo     = ""
        self.label       = ""
        self.legend      = None
        self.energy      = 0.0 
        self.normalisedPosition = 0.0
        self.column      = 1
        self.leftPointx  = 0
        self.leftPointy  = 0
        self.rightPointx = 0
        self.rightPointy = 0
        self.isCrowded   = False
        self.labelPosition= 0.0
        self.labelOffset = (0,0)
        self.textOffset  = (0,0)
        self.imageOffset = (0,0)
        self.imageScale  = 1.0
        self.image = None

######################################################################################################
#           Input reading block
######################################################################################################

def ReadInput(filename):
    try:
        inp = open(filename,'r')
    except:
        print("Error opening file. File: " + filename + " may not exist.")
        raise SystemExit("Could not open Input file: {:}".format(filename))

    stateBlock = False
    statesList = []
    width = 0
    height = 0
    fontSize = 8
    energyUnits = ""
    colorsToAdd = {}
    lc = 0
    for line in inp:
        lc += 1
        line = line.strip()
        if (len(line) > 0 and line.strip()[0] != "#"):
            if (stateBlock):
                if (line.strip()[0] == "{"):
                    print("Unexpected opening '{' within state block on line " + str(lc) + ".\nPossible forgotten closing '}'.")
                    raise ValueError("ERROR: Unexpected { on line " + str(lc))
                if (line.strip()[0] == "}"):
                    stateBlock = False
                else:
                    raw = line.split('=')
                    if (len(raw) != 2 and raw[0].upper().strip() != "LABEL"):
                        print(raw[0].strip())
                        print("Ignoring unrecognised line " + str(lc) + ":\n\t"+line)
                    else:
                        raw[0] = raw[0].upper().strip()
                        raw[1] = raw[1].strip()
                        if (raw[0] == "NAME"):
                            statesList[-1].name = raw[1].upper()
                        elif (raw[0] == "TEXTCOLOR" or raw[0] == "TEXTCOLOUR" or raw[0] == "TEXT-COLOUR" or raw[0] == "TEXT-COLOR" or raw[0] == "TEXT COLOUR" or raw[0] == "TEXT COLOR"):
                            statesList[-1].color = raw[1].upper()
                        elif (raw[0] == "LABEL"):
                            statesList[-1].label = ""
                            for i in range(1, len(raw)):
                                statesList[-1].label += raw[i]
                                if i < len(raw)-1:
                                    statesList[-1].label += " = "
                        elif (raw[0] == "LABELCOLOR" or raw[0] == "LABELCOLOUR"):
                            statesList[-1].labelColor = raw[1]
                        elif (raw[0] == "LINKSTO" or raw[0] == "LINKS TO"):
                            statesList[-1].linksTo = raw[1].upper()
                        elif (raw[0] == "COLUMN"):
                            try:
                                statesList[-1].column = int(raw[1])-1
                            except ValueError:
                                print("ERROR: Could not read integer for column number on line " + str(lc)+ ":\n\t"+line)
                        elif (raw[0] == "ENERGY"):
                            try:
                                statesList[-1].energy = float(raw[-1])
                            except ValueError:
                                print("ERROR: Could not read real number for energy on line " + str(lc)+ ":\n\t"+line)
                        elif (raw[0] == "LABELOFFSET" or raw[0] == "LABEL OFFSET" or raw[0] == "LABEL-OFFSET"):
                            raw[1] = raw[1].split(',')
                            try:
                                tx = float(raw[1][0])
                                ty = float(raw[1][1])
                                statesList[-1].labelOffset = (tx, ty)
                            except ValueError:
                                print("ERROR: Could not read real number for label offset on line " + str(lc)+ ":\n\t"+line)
                        elif (raw[0] == "TEXTOFFSET" or raw[0] == "TEXT OFFSET" or raw[0] == "TEXT-OFFSET"):
                            raw[1] = raw[1].split(',')
                            try:
                                tx = float(raw[1][0])
                                ty = float(raw[1][1])
                                statesList[-1].textOffset = (tx, ty)
                            except ValueError:
                                print("ERROR: Could not read real number for text offset on line " + str(lc)+ ":\n\t"+line)
                        elif raw[0] == "LEGEND":
                            statesList[-1].legend = raw[1]
                        elif raw[0] == "IMAGE":
                            try:
                                statesList[-1].image = plt.imread(raw[-1])
                            except IOError:
                                raise IOError("Failed to find image on line {:}".format(lc))
                        elif "IMAGE" in raw[0] and "OFFSET" in raw[0]:
                            raw[1] = raw[1].split(',')
                            try:
                                tx = float(raw[1][0])
                                ty = float(raw[1][1])
                                statesList[-1].imageOffset = (tx, ty)
                            except ValueError:
                                print("ERROR: Could not read real number for image offset on line " + str(lc)+ ":\n\t"+line)
                        elif "IMAGE" in raw[0] and "SCALE" in raw[0]:
                            try:
                                scale = float(raw[1])
                                if scale < 0.1:
                                    print("image scale cannot be < 0.1, setting to 0.1/")
                                statesList[-1].imageScale = max(scale, 0.1)
                            except ValueError:
                                print("ERROR: Could not read real number for image scale on line " + str(lc)+ ":\n\t"+line)
                        else:
                            print("Ignoring unrecognised line " + str(lc) + ":\n\t"+line)
            elif (line.strip()[0] == "{"):
                statesList.append(State())
                stateBlock = True   # we have entered a state block

            elif (line.strip()[0] == "}"):
                print("WARNING: Not expecting closing } on line: " + str(lc))

            else:
                raw = line.split('=')
                if (len(raw) != 2):
                    print("Ignoring unrecognised line " + str(lc) + ":\n\t"+line)
                else:
                    raw[0] = raw[0].upper().strip()
                    raw[1] = raw[1].strip().lstrip()
                    if (raw[0] == "WIDTH"):
                        try:
                            width = int(raw[1])
                        except ValueError:
                            print("ERROR: Could not read integer for diagram width on line " + str(lc)+ ":\n\t"+line)
                    elif (raw[0] == "HEIGHT"):
                        try:
                            height = int(raw[1])
                        except ValueError:
                            print("ERROR: Could not read integer for diagram height on line " + str(lc)+ ":\n\t"+line)
                    elif (raw[0] == "OUTPUT-FILE" or raw[0] == "OUTPUT"):
                        raw[1] = raw[1].lstrip()
                        if ( not raw[1].endswith('.pdf')):
                            print("WARNING: Output will be .pdf. Adding this to output file.\nFile will be saved as "+raw[1] + ".pdf")
                            outName = raw[1] + ".pdf"
                        else:
                            outName = raw[1]
                    elif (raw[0] == "ENERGY-UNITS" or raw[0] == "ENERGYUNITS" or raw[0] == "ENERGY UNITS"):
                        energyUnits = raw[1]
                    elif (raw[0] == "FONT-SIZE" or raw[0] == "FONTSIZE" or raw[0] == "FONT SIZE"):
                        try:
                            fontSize = int(raw[1])
                            plt.rcParams.update({'font.size': fontSize})
                        except ValueError:
                            print("ERROR: Could not read integer for font size on line " + str(lc)+ ":\n\t"+line)
                            print("Default will be used...")
                    else:
                        print("WARNING: Skipping unknown line " + str(lc) + ":\n\t" + line)
    if (stateBlock):
        print("WARNING: Final closing '}' is missing.")
    if (height == 0):
        print("ERROR: Image height not set! e.g.:\nheight = 500")
        raise ValueError("Height not set")
    if (width == 0):
        print("ERROR: Image width not set! e.g.:\nwidth = 500")
        raise ValueError("Width not set")
    if (outName == ""):
        print("ERROR: output file name not set! e.g.:\n output-file = example.pdf")
        raise ValueError("Output name not set")

    outDiagram = Diagram(width, height, fontSize, outName)
    outDiagram.energyUnits = energyUnits
    for color in colorsToAdd:
        outDiagram.COLORS[color] = colorsToAdd[color]
    maxColumn = 0
    for state in statesList:
        outDiagram.AddState(state)
        if (state.column > maxColumn):
            maxColumn = state.column
    outDiagram.columns = maxColumn + 1

    return outDiagram


######################################################################################################
#           Main driver function
######################################################################################################
def main():

    print("o=======================================================o")
    print("         Beginning Energy Level Diagram")
    print("o=======================================================o")
    if (len(sys.argv) == 1):
        print("\nI need an input file!\n")
        raise IOError("No Input file provided.")
    if (len(sys.argv) > 2):
        print("Incorrect arguments. Correct call:\npython EnergyLeveler.py <INPUT FILE>")
        raise ValueError("Incorrect Arguments.")

    diagram = ReadInput(sys.argv[1])
    diagram.MakeLeftRightPoints()
    diagram.DrawBars()
    diagram.DrawCanvas()
    diagram.FindLabelPosition()
    diagram.DrawLabels()
    diagram.DrawEnergies()
    diagram.DrawConnections()
    diagram.Save()

    print("o=======================================================o")
    print("         Image "+diagram.outputName+" made!")
    print("o=======================================================o")

if __name__ == "__main__":
    main()

#@ File(label="Select a input .msr file", style="file") msr_fn
#@ String (label="Channel names", value="Ch1, Ch2, Ch3") channel_names
#@ Float(label="Denosing (blurring sigma)", value=2.) sigma
#@ Boolean(label="Auto-threshold", value=True) is_auto_thresh
#@ String (visibility=MESSAGE, value="Without auto-threshold, you'll be asked to set manually") msg1
#@ Integer(label="Minimum area of region", value=10) min_area

import os
import sys
 
from java.io import File
from loci.plugins import BF
from ij.measure import ResultsTable
from ij.plugin.filter import ParticleAnalyzer as PA

from ij import IJ
from ij.plugin import ImageCalculator
from ij.gui import WaitForUserDialog
from ij.process import ImageConverter
from loci.plugins.in import ImporterOptions
from ij.plugin import RGBStackMerge


def open_test():
    imp1 = IJ.openImage("H:/projects/041_yoah_coloc/test_img/ch1.tif")
    imp2 = IJ.openImage("H:/projects/041_yoah_coloc/test_img/ch2.tif")
    imp3 = IJ.openImage("H:/projects/041_yoah_coloc/test_img/ch3.tif")
    
    return imp1, imp2, imp3

def open_msr(input_file):
    options = ImporterOptions()
    options.setId(input_file)
    #options.clearSeries()
    for s in [3,4,5]:
        options.setSeriesOn(s, True)
    imps = BF.openImagePlus(options)

    imp1 = imps[0]
    imp2 = imps[1]
    imp3 = imps[2] 
    
    return imp1, imp2, imp3


def auto_threshold(imp, is_auto_thresh, method="Otsu"):
    if is_auto_thresh:
        IJ.setAutoThreshold(imp, "{} dark".format(method))
        
    else:
        imp.show()
        IJ.run("Threshold...")
        # this is the method to wait the user set up the threshold
        WaitForUserDialog("Set manual threshold", "Use slider to adjust threshold and press OK").show()             
        
        thres_min = imp.getProcessor().getMinThreshold()
        thres_max = imp.getProcessor().getMaxThreshold()
        IJ.log("min threshold : "+str(thres_min))
        IJ.log("max threshold : "+str(thres_max))

        IJ.setThreshold(imp, thres_min, thres_max)
        imp.hide()
    #IJ.run(imp, "Convert to Mask", "")

def smooth(imp, sigma=1):
    IJ.run(imp, "Gaussian Blur...","sigma={}".format(sigma))
 

def apply_mask(imp, sigma, is_auto_thresh):
    smooth(imp, sigma)
    auto_threshold(imp, is_auto_thresh)


def analyze(imp, min_area):

    MAXSIZE = 1000000
    MINCIRCULARITY = 0.0
    MAXCIRCULARITY = 1.
    
    options = PA.SHOW_RESULTS + PA.SHOW_ROI_MASKS
    
    results = ResultsTable()
    
    p = PA(options, PA.AREA + PA.MEAN, results, min_area, MAXSIZE, MINCIRCULARITY, MAXCIRCULARITY)
    p.setHideOutputImage(True)

    p.analyze(imp)

    area   = list(results.getColumn(0))
    signal = list(results.getColumn(1))
    count  = len(area)

    total  = sum([a*s for a,s in zip(area, signal)])

    area   = sum(area)
    signal = total / count
    
    results.getResultsWindow().close()

    return count, area, signal


    

if __name__ in ["__builtin__", "__main__"]:
    
    #imp1, imp2, imp3 = open_msr(str(msr_fn))
    CN = [c.strip() for c in channel_names.split(",")]
    

    imp1, imp2, imp3 = open_test()

    msr_fn_base = os.path.basename(str(msr_fn))

    ImageConverter(imp1).convertToGray8()
    ImageConverter(imp2).convertToGray8()
    ImageConverter(imp3).convertToGray8()
    
#    imp1.show()
#    imp2.show()
#    imp3.show()

    apply_mask(imp1, sigma, is_auto_thresh)
    apply_mask(imp2, sigma, is_auto_thresh)
    apply_mask(imp3, sigma, is_auto_thresh)

    results = ResultsTable()
    results.setHeading(0, "Channel")
    results.setHeading(1, "Count")
    results.setHeading(2, "Surface area")
    results.setHeading(3, "Surface signal")
    

    def add_to_table(channel, c, a, s):
        results.incrementCounter()
        results.setValue(0, results.getCounter()-1, channel)
        results.addValue(1, c)
        results.addValue(2, a)
        results.addValue(3, s)
        results.setLabel(msr_fn_base, results.getCounter()-1)
         
    c, a,s = analyze(imp1, min_area)
    add_to_table(CN[0], c, a, s) 

    c,a,s = analyze(imp2, min_area)
    add_to_table(CN[1], c, a,s)
    
    c,a,s = analyze(imp3, min_area)
    add_to_table(CN[2], c, a,s)

    IJ.run(imp1, "Convert to Mask", "");
    IJ.run(imp2, "Convert to Mask", "");
    IJ.run(imp3, "Convert to Mask", "");
    
    ic = ImageCalculator()
    imp12  = ic.run("Muliply create", imp1,  imp2)
    imp13  = ic.run("Muliply create", imp1,  imp3)
    imp23  = ic.run("Muliply create", imp2,  imp2)
    imp123 = ic.run("Muliply create", imp12, imp3)

    c,a,s = analyze(imp12, 0)
    add_to_table("{}+{}".format(CN[0],CN[1]), c, a, -1)

    c,a,s = analyze(imp13, 0)
    add_to_table("{}+{}".format(CN[0],CN[2]), c, a, -1)

    c,a,s = analyze(imp23, 0)
    add_to_table("{}+{}".format(CN[1],CN[2]), c, a, -1)

    c,a,s = analyze(imp123, 0)
    add_to_table("{}+{}+{}".format(CN[0],CN[1], CN[2]), c, a, -1)

    results.show("Surfaces")
    
    imp_merge = RGBStackMerge.mergeChannels([imp1, imp2, imp3, imp12, imp13, imp23, imp123], False)

    imp_merge.show()

    
        

    print("Done")
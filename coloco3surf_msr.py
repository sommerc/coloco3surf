#@ File(label="Select a input .msr file", style="file") msr_fn
#@ String (label="Channel names", value="Ch1, Ch2, Ch3") channel_names
#@ Float(label="Denosing (blurring sigma)", value=1.5) sigma
#@ Boolean(label="Auto-threshold", value=True) is_auto_thresh
#@ String (visibility=MESSAGE, value="Without auto-threshold, you'll be asked to set it manually") msg1
#@ Integer(label="Minimum area of region (px)", value=64) min_area
#@ Boolean(label="Save raw channels as tif", value=False) save_raw
#@ Boolean(label="Save surfaces as tif    ", value=Fasle) save_surf

import os
import sys
 
from java.io import File
from loci.plugins import BF
from ij.measure import ResultsTable
from ij.plugin.filter import ParticleAnalyzer as PA

from ij import IJ
from ij import WindowManager
from ij.plugin import ImageCalculator
from ij.gui import WaitForUserDialog
from ij.process import ImageConverter
from loci.plugins.in import ImporterOptions
from ij.plugin import RGBStackMerge
from ij.process import StackStatistics

def open_test():
    imp1 = IJ.openImage("H:/projects/041_yoah_coloc/test_img/ch1.tif")
    imp2 = IJ.openImage("H:/projects/041_yoah_coloc/test_img/ch2.tif")
    imp3 = IJ.openImage("H:/projects/041_yoah_coloc/test_img/ch3.tif")
    
    return imp1, imp2, imp3

def open_msr(input_file):
    IJ.log("Reading images from {}".format(input_file))
    options = ImporterOptions()
    options.setId(input_file)
    #options.clearSeries()
    for s in [2,3,4,5]:
        options.setSeriesOn(s, True)
    imps = BF.openImagePlus(options)

    if len(imps) == 4:
        imp1 = imps[2]
        imp2 = imps[1]
        imp3 = imps[3] 
    elif len(imps) == 2:
        IJ.log(" -- Only two channels found. Replicating first as third.")
        imp1 = imps[1]
        imp2 = imps[0]
        imp3 = imps[0]
    else:
        raise RuntimeError("unknown channels")


    widths  = set([imp1.width, imp2.width, imp3.width])
    heights = set([imp1.height, imp2.height, imp3.height])

    if len(widths) > 1 or len(heights) > 1:
        IJ.log(" -- Resolution of images does not match. Resampling to highest resolution")
        new_width = max(widths)
        new_height = max(heights)

        imp1 = imp1.resize(new_width, new_height, "bilinear")
        imp2 = imp2.resize(new_width, new_height, "bilinear")
        imp3 = imp3.resize(new_width, new_height, "bilinear")
        

    
       
    
    return imp1, imp2, imp3

def signed2unsigned16(imp):
    stack = imp.getStack()
    if stack.isVirtual():
        IJ.error("Non-virtual stack required");
    cal = imp.getCalibration()
    if not cal.isSigned16Bit():
        return
        IJ.error("Signed 16-bit image required");
    cal.disableDensityCalibration()
    ip = imp.getProcessor()
    min = ip.getMin()
    max = ip.getMax()
    stats = StackStatistics(imp)
    minv = stats.min
    for i in range(stack.getSize()):
        ip = stack.getProcessor(i+1)
        ip.add(-minv)
    
    imp.setStack(stack)
    ip = imp.getProcessor()
    ip.setMinAndMax(min-minv, max-minv)
    imp.updateAndDraw()

def auto_threshold(imp, ch_name, is_auto_thresh, method="IsoData"):
    if is_auto_thresh:
        IJ.setAutoThreshold(imp, "{} dark".format(method))
        thres_min = imp.getProcessor().getMinThreshold()
    else:
        imp.show()
        IJ.run("Threshold...")
        # this is the method to wait the user set up the threshold
        wu = WaitForUserDialog("Set manual threshold for {}".format(ch_name), "Use slider to adjust threshold and press OK")
        wu.show()             
        
        thres_min = imp.getProcessor().getMinThreshold()
        thres_max = imp.getProcessor().getMaxThreshold()

        IJ.log(" -- {}: Min threshold {}".format(ch_name, thres_min))

        IJ.setThreshold(imp, thres_min, thres_max)
        imp.hide()
        WindowManager.getWindow("Threshold").close()

    return thres_min
        

def smooth(imp, sigma=1):
    IJ.run(imp, "Gaussian Blur...","sigma={}".format(sigma))

def apply_mask(imp, sigma, ch_name, is_auto_thresh):
    smooth(imp, sigma)
    thres_min = auto_threshold(imp, ch_name, is_auto_thresh)
    return thres_min

def analyze(imp, min_area):
    MAXSIZE = 1000000000000
    MINCIRCULARITY = 0.0
    MAXCIRCULARITY = 1.
    
    options = PA.SHOW_MASKS 
    
    temp_results = ResultsTable()
    
    p = PA(options, PA.AREA + PA.MEAN, temp_results, min_area, MAXSIZE, MINCIRCULARITY, MAXCIRCULARITY)
    p.setHideOutputImage(True)

    p.analyze(imp)

    if temp_results.getCounter() == 0:
        areas   = []
        signals = []
    else:
        areas   = list(temp_results.getColumn(0))
        signals = list(temp_results.getColumn(1))
    
    count  = len(areas)
    area   = sum(areas)

    total = 0
    if area > 0:
        total  = sum([a*s for a,s in zip(areas, signals)]) / area
      

    return p.getOutputImage(), count, area, total

def main():
    DEBUG = False
    
    CN = [c.strip() for c in channel_names.split(",")]

    if DEBUG:
        imp1, imp2, imp3 = open_test()
    else:
        imp1, imp2, imp3 = open_msr(str(msr_fn))
    
    msr_fn_base = os.path.basename(str(msr_fn))

    signed2unsigned16(imp1)
    signed2unsigned16(imp2)
    signed2unsigned16(imp3)

    imp1.updateAndDraw()
    imp2.updateAndDraw()
    imp3.updateAndDraw()

    IJ.run(imp1, "Enhance Contrast", "saturated=0.35")
    IJ.run(imp2, "Enhance Contrast", "saturated=0.35")
    IJ.run(imp3, "Enhance Contrast", "saturated=0.35")

    cal = imp1.getCalibration()
    IMAGE_AREA_UM = cal.pixelWidth * imp1.getWidth() * cal.pixelHeight * imp1.getHeight()

    t1 = apply_mask(imp1, sigma, CN[0], is_auto_thresh)
    t2 = apply_mask(imp2, sigma, CN[1], is_auto_thresh)
    t3 = apply_mask(imp3, sigma, CN[2], is_auto_thresh)

    results = ResultsTable()
    results.setHeading(0, "Channel")
    results.setHeading(1, "Count")
    results.setHeading(2, "Surface area (um)")
    results.setHeading(3, "Surface area (%)")
    results.setHeading(4, "Surface signal")    
    #results.setHeading(5, "Threshold used")    

    def add_to_table(channel, c, a, s):
        results.incrementCounter()
        results.setValue(0, results.getCounter()-1, channel)
        results.addValue(1, c)
        results.addValue(2, a)
        results.addValue(3, 100 * a /IMAGE_AREA_UM)
        results.addValue(4, s)
        #results.setLabel(msr_fn_base, results.getCounter()-1)

    imp1_mask, c,a,s = analyze(imp1, min_area)
    add_to_table(CN[0], c, a, s) 
    #results.addValue(4, t1)

    imp2_mask, c,a,s = analyze(imp2, min_area)
    add_to_table(CN[1], c, a,s)
    #results.addValue(4, t2)
    
    imp3_mask, c,a,s = analyze(imp3, min_area)
    add_to_table(CN[2], c, a,s)
    #results.addValue(4, t3)

#    IJ.run(imp1, "Enhance Contrast", "saturated=0.35")
#    IJ.run(imp2, "Enhance Contrast", "saturated=0.35")
#    IJ.run(imp3, "Enhance Contrast", "saturated=0.35")

    imp_raw = RGBStackMerge.mergeChannels([imp1, imp2, imp3], True)

    luts = list(imp_raw.getLuts())
    imp_raw.setLuts([luts[2], luts[0], luts[1]] )
    
    imp_raw.setTitle(msr_fn_base )
    imp_raw.show()

    if save_raw:
        save_base_fn = os.path.splitext(str(msr_fn))[0]
        IJ.save(imp_raw, save_base_fn + ".tif")
    

    IJ.run(imp1, "Convert to Mask", "")
    IJ.run(imp2, "Convert to Mask", "")
    IJ.run(imp3, "Convert to Mask", "")
    
    ic = ImageCalculator()
    imp12  = ic.run("Muliply create", imp1,  imp2)
    imp13  = ic.run("Muliply create", imp1,  imp3)
    imp23  = ic.run("Muliply create", imp2,  imp3)
    imp123 = ic.run("Muliply create", imp12, imp3)

    imp12_mask, c,a,s = analyze(imp12, min_area)
    add_to_table("{}+{}".format(CN[0],CN[1]), c, a, -1)

    imp13_mask, c,a,s = analyze(imp13, min_area)
    add_to_table("{}+{}".format(CN[0],CN[2]), c, a, -1)

    imp23_mask,c,a,s = analyze(imp23, min_area)
    add_to_table("{}+{}".format(CN[1],CN[2]), c, a, -1)

    imp123_mask,c,a,s = analyze(imp123, min_area)
    add_to_table("{}+{}+{}".format(CN[0],CN[1], CN[2]), c, a, -1)

    title = "Coloco3surf {}".format(msr_fn_base)
    results.show(title)
    
    imp_merge = RGBStackMerge.mergeChannels([imp1_mask, imp2_mask, imp3_mask, imp12_mask, imp13_mask, imp23_mask, imp123_mask], False)

    luts = list(imp_merge.getLuts())
    imp_merge.setLuts([luts[2], luts[0], luts[1]] + luts[3:])
    

    imp_merge.setTitle(title)
    imp_merge.show()

    if save_surf:
        save_base_fn = os.path.splitext(str(msr_fn))[0]
        IJ.save(imp_merge, save_base_fn + "_surfaces.tif")

    IJ.log("Done")

    
if __name__ in ["__builtin__", "__main__"]:
    main()
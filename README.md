# coloco3surf
A Fiji script for *colocolization* of up to 3 channels by automatic or user assisted thresholding.

Each channel can be smoothed and is thresholded. Statistics of the region areas and their overlap over all combinations of channels is computed and exported as csv.

## Installation and usage
1. Download `coloco3surf.py` (.tif) or `coloco3surf_msr.py` (.msr) script
2. Drag&Drop on Fiji
3. Press "Run"
= A graphical user dialog will pop up to enter the following inputs:

## Inputs
* `coloco3surf.py`
  * Drop-down to select the images for channel 1-3

* `coloco3surf_msr.py`
  * Path to .msr file
  * Names for the 3 channels (as they will appear in the output)

* Use Gaussian smoothing before thresholding
* Auto-threshold
* Minimum size of regions after thresholding
* Saving options



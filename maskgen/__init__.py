import matplotlib
matplotlib.use("TkAgg")
from pkg_resources import get_distribution
__version__ = get_distribution('maskgen').version
from loghandling import set_logging
set_logging()
import software_loader
from image_wrap import ImageWrapper
from maskgen_loader import MaskGenLoader
maskGenPreferences = MaskGenLoader()



import numpy as np
from ..containers import ConcentrationContainer
from .hillas import camera_to_shower_coordinates


def concentration(geom, image, hillas_parameters):
    """
    Calculate concentraion values.

    Concentrations are ratios of the amount of light in certain
    areas to the full intensity of the image.

    These features are usefull for g/h separation and energy estimation.
    """

    h = hillas_parameters

    delta_x = geom.pix_x - h.x
    delta_y = geom.pix_y - h.y

    # sort pixels by distance to cog
    cog_pixels = np.argsort(delta_x ** 2 + delta_y ** 2)
    conc_cog = np.sum(image[cog_pixels[:3]]) / h.intensity

    if hillas_parameters.width != 0:
        # get all pixels inside the hillas ellipse
        longi, trans = camera_to_shower_coordinates(geom.pix_x, geom.pix_y, h.x, h.y, h.psi)
        mask_core = (longi ** 2 / h.length ** 2) + (trans ** 2 / h.width ** 2) <= 1.0
        conc_core = image[mask_core].sum() / h.intensity
    else:
        conc_core = 0.0

    concentration_pixel = image.max() / h.intensity

    return ConcentrationContainer(
        cog=conc_cog,
        core=conc_core,
        pixel=concentration_pixel,
    )

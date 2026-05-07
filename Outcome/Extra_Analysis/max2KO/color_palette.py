"""
Okabe-Ito Color Palette for Scientific Figures
===============================================

The gold standard colorblind-friendly palette, recommended by Nature Methods.
Developed by Masataka Okabe and Kei Ito.

These colors remain distinguishable for people with all common types of
color vision deficiency (CVD), including protanopia, deuteranopia, and tritanopia.

Reference: https://jfly.uni-koeln.de/color/
"""

# Okabe-Ito Primary Palette (8 colors + black)
OKABE_ITO = {
    'orange':      '#E69F00',
    'sky_blue':    '#56B4E9',
    'green':       '#009E73',  # Bluish green
    'yellow':      '#F0E442',
    'blue':        '#0072B2',
    'vermillion':  '#D55E00',  # Red-orange
    'purple':      '#CC79A7',  # Reddish purple
    'grey':        '#999999',
    'black':       '#000000',
}

# Extended palette with amber
OKABE_ITO_EXTENDED = {
    **OKABE_ITO,
    'amber':       '#F5C710',
}

# Organized for 3-group comparisons (Flash-P, PC-Cleaned, PC-RAW)
# Each group has 3 colors for 3 methods (Algebraic, ODE, RWR)

FLASHP_COLORS = {
    'algebraic': '#0072B2',  # Blue
    'ode':       '#009E73',  # Bluish green
    'rwr':       '#56B4E9',  # Sky blue
}

PC_CLEANED_COLORS = {
    'algebraic': '#E69F00',  # Orange
    'ode':       '#F5C710',  # Amber
    'rwr':       '#F0E442',  # Yellow
}

PC_RAW_COLORS = {
    'algebraic': '#D55E00',  # Vermillion
    'ode':       '#CC79A7',  # Purple
    'rwr':       '#999999',  # Grey
}

# As lists for matplotlib
FLASHP_LIST = ['#0072B2', '#009E73', '#56B4E9']      # Blue, Green, Sky blue
PC_CLEANED_LIST = ['#E69F00', '#F5C710', '#F0E442']  # Orange, Amber, Yellow
PC_RAW_LIST = ['#D55E00', '#CC79A7', '#999999']      # Vermillion, Purple, Grey

# Alternative: Method-based coloring (same method = same hue, different saturation)
# This groups by validation method rather than by network source
METHOD_COLORS = {
    'algebraic': {'flashp': '#0072B2', 'pc_clean': '#56B4E9', 'pc_raw': '#A6D8F0'},
    'ode':       {'flashp': '#009E73', 'pc_clean': '#66C2A5', 'pc_raw': '#B2D8CE'},
    'rwr':       {'flashp': '#D55E00', 'pc_clean': '#FC8D62', 'pc_raw': '#FDCDAC'},
}

# For simple 3-category comparisons
THREE_CATEGORY = {
    'flashp':     '#0072B2',  # Blue
    'pc_cleaned': '#E69F00',  # Orange
    'pc_raw':     '#D55E00',  # Vermillion
}

# For binary comparisons
BINARY = {
    'primary':   '#0072B2',  # Blue
    'secondary': '#E69F00',  # Orange
}

# Sequential palette for heatmaps (use viridis from matplotlib instead)
# For diverging data, use colorspace or seaborn diverging palettes

def get_flashp_colors():
    """Return Flash-P colors as list."""
    return FLASHP_LIST

def get_pc_cleaned_colors():
    """Return PC-Cleaned colors as list."""
    return PC_CLEANED_LIST

def get_pc_raw_colors():
    """Return PC-RAW colors as list."""
    return PC_RAW_LIST

def get_all_9_colors():
    """Return all 9 colors for the complete comparison."""
    return FLASHP_LIST + PC_CLEANED_LIST + PC_RAW_LIST


if __name__ == "__main__":
    # Print palette for reference
    print("Okabe-Ito Palette for Flash-P Figures")
    print("=" * 50)
    print("\nFlash-P colors:")
    for name, color in FLASHP_COLORS.items():
        print(f"  {name}: {color}")
    print("\nPC-Cleaned colors:")
    for name, color in PC_CLEANED_COLORS.items():
        print(f"  {name}: {color}")
    print("\nPC-RAW colors:")
    for name, color in PC_RAW_COLORS.items():
        print(f"  {name}: {color}")

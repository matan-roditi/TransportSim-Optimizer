"""
Static configuration data for the Herzliya simulation environment.
Contains GPS bounding boxes for all major neighborhoods.
"""

HERZLIYA_NEIGHBORHOODS = {
    # Beachside residential strip (west of Ramat Yam road)
    "Herzliya_Pituach": {"weight": 1.0, "bounds": {"lat": [32.168, 32.183], "lon": [34.799, 34.808]}},
    # Tech / business park (Park Azorim, Silicon Wadi) — higher weight = more commuters
    "Herzliya_Pituach_Business": {"weight": 2.0, "bounds": {"lat": [32.155, 32.168], "lon": [34.803, 34.818]}},
    "Marina": {"weight": 1.0, "bounds": {"lat": [32.158, 32.165], "lon": [34.795, 34.805]}},
    "Nof_Yam": {"weight": 1.0, "bounds": {"lat": [32.174, 32.183], "lon": [34.805, 34.815]}},
    "Herzliya_B": {"weight": 1.0, "bounds": {"lat": [32.170, 32.185], "lon": [34.815, 34.825]}},
    "Green_Herzliya": {"weight": 1.0, "bounds": {"lat": [32.170, 32.180], "lon": [34.830, 34.845]}},
    "Young_Herzliya": {"weight": 1.0, "bounds": {"lat": [32.155, 32.165], "lon": [34.830, 34.845]}},
    "Galil_Yam": {"weight": 1.0, "bounds": {"lat": [32.145, 32.155], "lon": [34.825, 34.835]}},
    "City_Center": {"weight": 1.0, "bounds": {"lat": [32.160, 32.170], "lon": [34.835, 34.845]}},
    "Neve_Yisrael": {"weight": 1.0, "bounds": {"lat": [32.150, 32.160], "lon": [34.840, 34.850]}},
    "Neve_Amirim": {"weight": 1.0, "bounds": {"lat": [32.145, 32.155], "lon": [34.845, 34.855]}},
    "Shikun_Darom": {"weight": 1.0, "bounds": {"lat": [32.155, 32.165], "lon": [34.845, 34.855]}},
    "Neve_Amal": {"weight": 1.0, "bounds": {"lat": [32.160, 32.175], "lon": [34.850, 34.865]}},
    "Yad_HaTisha": {"weight": 1.0, "bounds": {"lat": [32.176, 32.183], "lon": [34.845, 34.855]}},
    "Gan_Rashal": {"weight": 1.0, "bounds": {"lat": [32.176, 32.183], "lon": [34.835, 34.845]}},
    "Neve_Oved": {"weight": 1.0, "bounds": {"lat": [32.170, 32.180], "lon": [34.845, 34.855]}},
    "Train_Station": {"weight": 1.0, "bounds": {"lat": [32.160, 32.165], "lon": [34.810, 34.820]}},
}
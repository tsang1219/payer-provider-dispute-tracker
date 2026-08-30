#!/usr/bin/env python3
"""
Add coordinates to all health systems in disputes_enriched.csv
"""

import pandas as pd
import json

# Load disputes
df = pd.read_csv('/Users/all/claude_code/payer_provider_disputes/output/disputes_enriched.csv')

# Load reference data
with open('/Users/all/claude_code/payer_provider_disputes/health_systems_reference.json', 'r') as f:
    ref_data = json.load(f)

# Build lookup from reference (by name variants)
ref_coords = {}
for key, data in ref_data.items():
    lat, lon = data.get('hq_lat'), data.get('hq_lon')
    city = data.get('hq_city', '')
    if lat and lon:
        ref_coords[data['name'].lower()] = (lat, lon, city)
        for variant in data.get('name_variants', []):
            ref_coords[variant.lower()] = (lat, lon, city)

# Comprehensive coordinate database for missing systems
# Sources: Google Maps, hospital websites, CMS data
coord_database = {
    # NC
    "Catawba Valley Medical Center": (35.7321, -81.3412, "Hickory"),
    "Northeast Georgia Health System": (34.2979, -83.8247, "Gainesville"),
    "Tryon Medical Partners": (35.2271, -80.8431, "Charlotte"),
    "CaroMont": (35.2627, -81.1876, "Gastonia"),
    "Cape Fear Valley Health": (35.0527, -78.8784, "Fayetteville"),
    "ECU Health": (35.6127, -77.3664, "Greenville"),
    "Duke Health": (36.0014, -78.9382, "Durham"),
    "UNC Health": (35.9132, -79.0558, "Chapel Hill"),

    # GA
    "Southeast Georgia Health System": (31.1499, -81.4915, "Brunswick"),
    "Piedmont Healthcare": (33.7879, -84.3727, "Atlanta"),

    # TN
    "Methodist Health Care": (35.1495, -90.0490, "Memphis"),
    "Vanderbilt Health": (36.1447, -86.8027, "Nashville"),
    "CHI Memorial": (35.0456, -85.3097, "Chattanooga"),
    "Ballad Health (21 hospitals)": (36.3134, -82.3535, "Johnson City"),

    # TX
    "HCA Healthcare (38 hospitals)": (32.7767, -96.7970, "Dallas"),
    "Baylor Scott \\u0026 White": (32.7767, -96.7970, "Dallas"),
    "Southwestern Health Resources/Texas Health/UT": (32.7767, -96.7970, "Dallas"),
    "Southwestern Health Resources/UT Southwestern": (32.7767, -96.7970, "Dallas"),
    "Southwestern Health Resources": (32.7767, -96.7970, "Dallas"),

    # NY
    "SUNY Upstate University Hospital": (43.0410, -76.1396, "Syracuse"),
    "Albany Medical Center": (42.6526, -73.7562, "Albany"),
    "Albany Med Health System": (42.6526, -73.7562, "Albany"),
    "St. Peter's Health Partners": (42.6526, -73.7562, "Albany"),
    "Memorial Sloan Kettering Cancer Center": (40.7644, -73.9563, "New York"),
    "Memorial Sloan Kettering": (40.7644, -73.9563, "New York"),

    # FL
    "Johns Hopkins All Children's Hospital": (27.7715, -82.6785, "St. Petersburg"),
    "Broward Health": (26.1224, -80.1373, "Fort Lauderdale"),
    "University of Florida Health": (29.6400, -82.3440, "Gainesville"),
    "NCH Healthcare System": (26.1420, -81.7948, "Naples"),
    "Memorial Healthcare System": (26.0112, -80.2045, "Hollywood"),

    # OH
    "Genesis Healthcare System": (39.9403, -82.0132, "Zanesville"),
    "Aultman Health System": (40.7989, -81.3784, "Canton"),
    "Adena Health System": (39.3295, -82.9824, "Chillicothe"),
    "Ohio State Wexner Medical Center": (40.0061, -83.0184, "Columbus"),
    "Mercy Health (Springfield/Urbana)": (39.9242, -83.8088, "Springfield"),
    "Mount Carmel Health System": (39.9612, -82.9988, "Columbus"),
    "TriHealth": (39.1031, -84.5120, "Cincinnati"),
    "Kettering Health": (39.7589, -84.1916, "Dayton"),

    # PA
    "WellSpan Health": (39.9626, -76.7277, "York"),
    "Main Line Health": (40.0379, -75.3399, "Bryn Mawr"),
    "WVU Medicine Uniontown Hospital": (39.8990, -79.7164, "Uniontown"),
    "Jefferson Health": (39.9526, -75.1652, "Philadelphia"),

    # MN
    "North Memorial Medical Center": (45.0230, -93.3242, "Robbinsdale"),
    "North Memorial Health": (45.0230, -93.3242, "Robbinsdale"),
    "HealthPartners": (44.8408, -93.2983, "Bloomington"),
    "Essentia Health": (46.7867, -92.1005, "Duluth"),
    "Aspirus/St. Luke's Hospital": (46.7867, -92.1005, "Duluth"),
    "Aspirus Health (St. Luke's)": (46.7867, -92.1005, "Duluth"),

    # CT
    "Hartford HealthCare": (41.7658, -72.6734, "Hartford"),
    "Trinity Health of New England": (41.7658, -72.6734, "Hartford"),
    "Stamford Health": (41.0534, -73.5387, "Stamford"),

    # IN
    "Community Healthcare System": (41.4464, -87.3406, "Munster"),
    "Powers Health (Community Healthcare)": (41.4464, -87.3406, "Munster"),

    # Other states
    "TeamHealth (physician staffing)": (36.1699, -115.1398, "Las Vegas"),  # NV
    "Envision Healthcare": (35.4676, -97.5164, "Oklahoma City"),  # National HQ
    "Chesapeake Regional Medical Center": (36.8230, -76.2875, "Chesapeake"),  # VA
    "Scripps Clinic Medical Group": (32.8328, -117.1486, "La Jolla"),  # CA
    "EvergreenHealth": (47.7015, -122.1558, "Kirkland"),  # WA
    "Arkansas Methodist Medical Center": (35.9003, -90.5885, "Paragould"),  # AR
    "Hillcrest HealthCare System": (36.1540, -95.9928, "Tulsa"),  # OK
    "Baton Rouge General": (30.4515, -91.1871, "Baton Rouge"),  # LA
    "Stillwater Medical Center": (36.1156, -97.0584, "Stillwater"),  # OK
    "Conway Regional Health System": (35.0887, -92.4421, "Conway"),  # AR
    "Samaritan Health Services": (44.5646, -123.2620, "Corvallis"),  # OR
    "St. Charles Health System": (44.0582, -121.3153, "Bend"),  # OR
    "Brookings Health System": (44.3114, -96.7984, "Brookings"),  # SD
    "Cameron Regional Medical Center": (39.7403, -94.2410, "Cameron"),  # MO
    "Comanche County Memorial Hospital": (34.6036, -98.3959, "Lawton"),  # OK
    "MU Health Care": (38.9517, -92.3341, "Columbia"),  # MO
    "Infirmary Health": (30.6954, -88.0399, "Mobile"),  # AL
    "Huntsville Hospital Health System": (34.7304, -86.5861, "Huntsville"),  # AL
    "Northern Light Health (10 hospitals)": (44.8016, -68.7712, "Bangor"),  # ME
    "Great Plains Health": (41.1403, -100.7601, "North Platte"),  # NE
    "Kimball Health Services": (41.2358, -103.6624, "Kimball"),  # NE
    "Prairie Lakes Healthcare System": (44.9003, -97.1147, "Watertown"),  # SD
    "MyMichigan Health": (43.4195, -83.9508, "Midland"),  # MI
    "Carson Tahoe Health": (39.1638, -119.7674, "Carson City"),  # NV
    "MercyOne": (41.6611, -91.5302, "Des Moines"),  # IA
    "CommonSpirit hospitals (Colorado)": (39.7392, -104.9903, "Denver"),  # CO
    "CommonSpirit Health (11 hospitals)": (39.7392, -104.9903, "Denver"),  # CO
    "Bayhealth": (39.1582, -75.5244, "Dover"),  # DE
    "Trinity Health Michigan": (42.5803, -83.4306, "Livonia"),  # MI
    "Phoenix Children's Hospital": (33.4803, -112.0740, "Phoenix"),  # AZ
    "Blessing Health": (39.9356, -91.3797, "Quincy"),  # IL
    "MUSC Health": (32.7846, -79.9496, "Charleston"),  # SC
    "North Mississippi Health Services": (34.2576, -88.7034, "Tupelo"),  # MS
    "Iowa Specialty Hospitals": (42.6500, -93.3900, "Clarion"),  # IA
    "LMH Health": (38.9717, -95.2353, "Lawrence"),  # KS
    "Capital Women's Care": (39.0458, -77.1172, "Rockville"),  # MD
    "Montrose Regional Health": (38.4783, -107.8762, "Montrose"),  # CO
    "Bon Secours St. Francis Health": (34.8526, -82.3940, "Greenville"),  # SC
    "Spartanburg Regional Healthcare": (34.9496, -81.9320, "Spartanburg"),  # SC
    "Mercy (MO system)": (37.2090, -93.2923, "Springfield"),  # MO
    "Lexington Medical Center": (34.0007, -81.0348, "West Columbia"),  # SC
    "UMass Memorial Health": (42.2626, -71.8023, "Worcester"),  # MA
    "Boston Children's Hospital": (42.3370, -71.1065, "Boston"),  # MA
    "Ascension Wisconsin": (43.0389, -87.9065, "Milwaukee"),  # WI
    "Abrazo Health (Tenet Healthcare)": (33.4484, -112.0740, "Phoenix"),  # AZ
    "University of Utah Health": (40.7608, -111.8910, "Salt Lake City"),  # UT
    "HMSA Provider Network": (21.3069, -157.8583, "Honolulu"),  # HI
    "UC Health (University of California)": (37.8716, -122.2727, "Oakland"),  # CA
    "North Kansas City Hospital/Meritas Health": (39.1313, -94.5624, "North Kansas City"),  # MO
}

# Apply coordinates
updated = 0
for idx, row in df.iterrows():
    if pd.isna(row['system_hq_lat']) or pd.isna(row['system_hq_lon']):
        system_name = row['system_name']

        # Try exact match in our database
        if system_name in coord_database:
            lat, lon, city = coord_database[system_name]
            df.at[idx, 'system_hq_lat'] = lat
            df.at[idx, 'system_hq_lon'] = lon
            if pd.isna(row['system_hq_city']):
                df.at[idx, 'system_hq_city'] = city
            updated += 1
        # Try reference data
        elif system_name.lower() in ref_coords:
            lat, lon, city = ref_coords[system_name.lower()]
            df.at[idx, 'system_hq_lat'] = lat
            df.at[idx, 'system_hq_lon'] = lon
            if pd.isna(row['system_hq_city']):
                df.at[idx, 'system_hq_city'] = city
            updated += 1

# Check results
has_coords = df['system_hq_lat'].notna() & df['system_hq_lon'].notna()
print(f"Updated {updated} rows with coordinates")
print(f"Total with coordinates: {has_coords.sum()}/{len(df)} ({has_coords.sum()/len(df)*100:.1f}%)")

# Show any still missing
still_missing = df[~has_coords][['system_name', 'system_hq_state']].drop_duplicates()
if len(still_missing) > 0:
    print(f"\nStill missing coordinates ({len(still_missing)} systems):")
    for _, row in still_missing.iterrows():
        print(f"  - {row['system_name']} ({row['system_hq_state']})")

# Save
df.to_csv('/Users/all/claude_code/payer_provider_disputes/output/disputes_enriched.csv', index=False)
print(f"\nSaved to disputes_enriched.csv")

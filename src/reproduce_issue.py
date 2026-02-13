
import pandas as pd
import json
import os
import sys

# Import the parser function (need to add path to sys.path)
sys.path.append(r"c:\Users\Ritik\OneDrive\Desktop\osbridge\OsBridgeLCCA\src")
from osbridgelcca.desktop_app.main_template import parse_and_validate_excel

def create_dummy_excel():
    data = {
        'CID#Name': ['Test Item'],
        'CID#Quantity': [100],
        'CID#Unit': ['kg'],
        'CID#Rate': [50],
        'CID#Rate_Src': ['Test'],
        'CID#Carbon_Emission_Src': ['Test'],
        'CID#Carbon_Emission_Units': ['KgC02e/kg'] # Note the zero and capital K
    }
    df = pd.DataFrame(data)
    # Add header row for 'Section Name' identification?
    # The parser expects:
    # Row 0: Type Name (e.g. Excavation)
    # Row 1: Headers (CID#...)
    # But pd.read_excel header=None
    
    # Let's construct a dataframe that looks like the excel structure
    # Row 0: "Excavation", None, None...
    # Row 1: CID#Name, CID#Quantity...
    # Row 2: Val, Val...
    
    rows = []
    # Row 0
    rows.append(["Excavation"] + [None]*6)
    # Row 1
    rows.append(["CID#Name", "CID#Quantity", "CID#Unit", "CID#Rate", "CID#Rate_Src", "CID#Carbon_Emission_Src", "CID#Carbon_Emission_Units"])
    # Row 2
    rows.append(["Test Item", 100, "kg", 50, "Test", "Test", "KgC02e/kg"])
    
    df_out = pd.DataFrame(rows)
    
    file_path = "test_input.xlsx"
    df_out.to_excel(file_path, index=False, header=False)
    return file_path

def test_parser():
    file_path = create_dummy_excel()
    print(f"Created {file_path}")
    
    try:
        result = parse_and_validate_excel(file_path)
        print("Parser Output:")
        print(json.dumps(result, indent=2))
        
        # Check the value
        parsed_data = result['parsed_data']
        if parsed_data:
            item = parsed_data[0]['data'][0]
            unit = item.get('carbon_emission_units')
            print(f"\nExtracted Unit: '{unit}'")
            print(f"repr(unit): {repr(unit)}")
            
            if unit == "kgCO\u2082e/kg":
                print("MATCH: It is reading it as kgCO₂e/kg")
            elif unit == "KgC02e/kg":
                print("MATCH: It is reading it as KgC02e/kg (No conversion)")
            else:
                print("MISMATCH: Reading as something else")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    test_parser()

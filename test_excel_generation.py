#!/usr/bin/env python3
"""
Test script to verify Excel generation functionality
"""

import pandas as pd
from io import StringIO
import os

def test_excel_generation():
    """Test Excel generation with sample data"""
    
    # Test data
    test_data = "nombre,edad,ciudad\nJuan,25,Buenos Aires\nAna,30,Córdoba\nPedro,28,Rosario"
    
    print("Testing Excel generation...")
    print(f"Input data:\n{test_data}")
    
    try:
        # Check if openpyxl is available
        import openpyxl
        print("✓ openpyxl module found")
        
        # Create DataFrame
        df = pd.read_csv(StringIO(test_data))
        print(f"✓ DataFrame created with {len(df)} rows")
        
        # Generate Excel file
        filename = "test_output.xlsx"
        df.to_excel(filename, index=False, engine='openpyxl')
        
        # Check if file was created
        if os.path.exists(filename):
            print(f"✓ Excel file created successfully: {filename}")
            print(f"  File size: {os.path.getsize(filename)} bytes")
            
            # Read back the Excel file to verify
            df_read = pd.read_excel(filename, engine='openpyxl')
            print(f"✓ Excel file can be read back: {len(df_read)} rows")
            
            return True
        else:
            print("❌ Excel file was not created")
            return False
            
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Run: pip install openpyxl")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_excel_generation()
    if success:
        print("\n🎉 Excel generation test passed!")
    else:
        print("\n❌ Excel generation test failed!")

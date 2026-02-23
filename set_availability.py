import pandas as pd
import os
import sys

EXCEL_FILE = "actives.xlsx"

def main():
    if not os.path.exists(EXCEL_FILE):
        print(f"Error: {EXCEL_FILE} not found.")
        sys.exit(1)

    df = pd.read_excel(EXCEL_FILE)
    if "availability" not in df.columns:
        df["availability"] = 1
        print("Added new 'availability' column with default value 1 (available).")

    while True:
        print("\n--- Current Availability Options ---")
        for i, row in df.iterrows():
            status = "Available " if int(row["availability"]) == 1 else "Unavailable"
            print(f"[{i}] {row['name']:<20} - {status}")
            
        quit_idx = len(df)
        print(f"[{quit_idx}] Quit")
        
        try:
            choice = input("\nEnter the number of the person to toggle their availability (or Quit to exit): ").strip()
            
            if choice == str(quit_idx) or choice.lower() in ('q', 'quit'):
                print("Saving changes and exiting...")
                break
                
            idx = int(choice)
            if 0 <= idx < len(df):
                current_status = int(df.at[idx, "availability"])
                new_status = 0 if current_status == 1 else 1
                df.at[idx, "availability"] = new_status
                
                name = df.at[idx, 'name']
                new_status_str = "Available" if new_status == 1 else "Unavailable"
                print(f"✅ Toggled '{name}' to {new_status_str}.")
            else:
                print("Invalid number. Please try again.")
                
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    # Save to Excel before quitting
    df.to_excel(EXCEL_FILE, index=False)
    print(f"Saved changes to {EXCEL_FILE}.")

if __name__ == "__main__":
    main()

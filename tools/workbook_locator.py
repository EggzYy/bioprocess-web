#!/usr/bin/env python3
"""
Workbook Locator - Maps facility names to Excel workbook files.

This module helps find the correct Excel file for a given facility name,
handling variations in naming and multiple search paths.
"""

import os
import glob
import json
from pathlib import Path
from typing import List, Optional, Dict


# Facility name to file pattern mapping
FACILITY_MAPPINGS = {
    "Facility 1 - Yogurt Cultures (10 TPA)": "*Facility1*Yogurt*10TPA*calc.xlsx",
    "Facility 2 - Lacto/Bifido (10 TPA)": "*Facility2*Lacto*10TPA*calc.xlsx",
    "Facility 3 - Bacillus Spores (10 TPA)": "*Facility3*Bacillus*10TPA*calc.xlsx",
    "Facility 4 - Yeast Based Probiotic (10 TPA)": "*Facility4*Yeast*10TPA*calc.xlsx",
    "Facility 5 - ALL IN (40 TPA)": "*Facility5*ALL*40TPA*calc.xlsx",
    # Alternative names (without parentheses)
    "Facility 1 - Yogurt Cultures": "*Facility1*Yogurt*10TPA*calc.xlsx",
    "Facility 2 - Lacto/Bifido": "*Facility2*Lacto*10TPA*calc.xlsx",
    "Facility 3 - Bacillus Spores": "*Facility3*Bacillus*10TPA*calc.xlsx",
    "Facility 4 - Yeast Based Probiotic": "*Facility4*Yeast*10TPA*calc.xlsx",
    "Facility 5 - ALL IN": "*Facility5*ALL*40TPA*calc.xlsx",
    # Short names
    "Facility 1": "*Facility1*calc.xlsx",
    "Facility 2": "*Facility2*calc.xlsx",
    "Facility 3": "*Facility3*calc.xlsx",
    "Facility 4": "*Facility4*calc.xlsx",
    "Facility 5": "*Facility5*calc.xlsx",
}


def find_workbook(facility_name: str, search_roots: Optional[List[str]] = None) -> str:
    """
    Find the Excel workbook for a given facility name.

    Args:
        facility_name: Name of the facility (e.g., "Facility 1 - Yogurt Cultures (10 TPA)")
        search_roots: List of directories to search. Defaults to current dir and parent.

    Returns:
        Absolute path to the workbook file

    Raises:
        FileNotFoundError: If no matching file is found
        ValueError: If multiple matching files are found
    """
    # Default search paths - only current directory to avoid duplicates
    if search_roots is None:
        current_dir = Path.cwd()
        search_roots = [
            str(current_dir),  # Current directory only
        ]

    # Get the glob pattern for this facility
    pattern = FACILITY_MAPPINGS.get(facility_name)
    if not pattern:
        # Try to be flexible with naming
        facility_name_normalized = facility_name.strip()
        pattern = FACILITY_MAPPINGS.get(facility_name_normalized)

        if not pattern:
            raise ValueError(
                f"Unknown facility name: {facility_name}. "
                f"Known facilities: {list(FACILITY_MAPPINGS.keys())}"
            )

    # Search for files matching the pattern
    matches = []
    for root in search_roots:
        root_path = Path(root)
        if not root_path.exists():
            continue

        # Search in root directory
        for file in glob.glob(os.path.join(root, pattern)):
            abs_path = os.path.abspath(file)
            if abs_path not in matches:
                matches.append(abs_path)

    # Handle results
    if len(matches) == 0:
        searched_paths = "\n  ".join(search_roots)
        raise FileNotFoundError(
            f"No workbook found for facility '{facility_name}'\n"
            f"Pattern: {pattern}\n"
            f"Searched in:\n  {searched_paths}"
        )
    elif len(matches) > 1:
        matches_list = "\n  ".join(matches)
        raise ValueError(
            f"Multiple workbooks found for facility '{facility_name}':\n  {matches_list}\n"
            f"Please ensure only one matching file exists."
        )

    return matches[0]


def discover_workbooks(search_dir: str = ".") -> Dict[str, str]:
    """
    Discover all Excel workbooks in a directory matching the naming pattern.

    Args:
        search_dir: Directory to search

    Returns:
        Dictionary mapping facility names to file paths
    """
    workbooks = {}
    search_path = Path(search_dir)

    # Look for all calc.xlsx files
    for xlsx_file in search_path.glob("*calc.xlsx"):
        # Try to determine which facility this is
        filename = xlsx_file.name

        # Simple pattern matching based on filename content
        if "Facility1" in filename:
            workbooks["Facility 1 - Yogurt Cultures (10 TPA)"] = str(
                xlsx_file.absolute()
            )
        elif "Facility2" in filename:
            workbooks["Facility 2 - Lacto/Bifido (10 TPA)"] = str(xlsx_file.absolute())
        elif "Facility3" in filename:
            workbooks["Facility 3 - Bacillus Spores (10 TPA)"] = str(
                xlsx_file.absolute()
            )
        elif "Facility4" in filename:
            workbooks["Facility 4 - Yeast Based Probiotic (10 TPA)"] = str(
                xlsx_file.absolute()
            )
        elif "Facility5" in filename:
            if "40TPA" in filename:
                workbooks["Facility 5 - ALL IN (40 TPA)"] = str(xlsx_file.absolute())
            else:
                workbooks["Facility 5 - ALL IN"] = str(xlsx_file.absolute())

    return workbooks


def update_workbook_registry(registry_path: str = "data/original_workbooks.json"):
    """
    Update the workbook registry JSON file with discovered workbooks.

    Args:
        registry_path: Path to the registry JSON file
    """
    # Discover workbooks in current directory
    discovered = discover_workbooks(".")

    # Also check parent directory
    parent_discovered = discover_workbooks("..")

    # Merge discoveries (prefer local over parent)
    all_workbooks = {**parent_discovered, **discovered}

    # Load existing registry if it exists
    registry_path = Path(registry_path)
    if registry_path.exists():
        with open(registry_path, "r") as f:
            registry = json.load(f)
    else:
        registry = {"workbooks": []}

    # Update paths in registry
    for item in registry["workbooks"]:
        facility = item["facility"]

        # Find matching discovered workbook
        for discovered_name, discovered_path in all_workbooks.items():
            if facility in discovered_name or discovered_name in facility:
                item["path"] = discovered_path
                item["discovered"] = True
                break

    # Save updated registry
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2)

    return registry


def list_available_facilities():
    """
    List all available facilities with their workbook paths.

    Returns:
        List of tuples (facility_name, file_path)
    """
    discovered = discover_workbooks(".")
    parent_discovered = discover_workbooks("..")

    # Merge discoveries
    all_workbooks = {**parent_discovered, **discovered}

    # Sort by facility name
    return sorted(all_workbooks.items())


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Test finding a specific facility
        facility = " ".join(sys.argv[1:])
        try:
            path = find_workbook(facility)
            print(f"Found workbook for '{facility}':")
            print(f"  Path: {path}")
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}")
    else:
        # List all available facilities
        print("Available facilities and their workbooks:")
        print("=" * 80)

        facilities = list_available_facilities()
        if facilities:
            for facility, path in facilities:
                print(f"\n{facility}:")
                print(f"  {path}")
        else:
            print("No workbooks found in current or parent directory")

        print("\n" + "=" * 80)
        print("Usage: python workbook_locator.py [facility name]")
        print("Example: python workbook_locator.py 'Facility 1'")

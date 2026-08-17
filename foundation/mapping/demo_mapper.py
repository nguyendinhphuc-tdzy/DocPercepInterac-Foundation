"""Hard-coded Mapping Engine for GTPS Demo (Lineage tracking)"""
import sys
from pathlib import Path

# Add foundation to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from perception.parser import extract_geometry
from mapping.lineage import LineageLogger
from mapping.writeback import WritebackEngine

# Hard-coded rules simulating the GTPS use case:
# Map specific Excel cells (source) to specific Word tables/paragraphs (target)
DEMO_RULES = {
    # 1. Provision of processing services amount
    "RPTs!E8": ["table:6:376644e1_row:1_col:4"],
    
    # 2. Provision of processing services %
    "RPTs!F8": ["table:6:376644e1_row:1_col:5"],
    
    # 3. Net Sales
    "Financial Analysis!D7": ["table:10:b50165a2_row:2_col:2"],
}

def build_docx_anchor(block) -> str:
    if block.get("table_index") is not None:
        t_hash = block.get("table_hash", "")
        return f"table:{block['table_index']}:{t_hash}_row:{block['row_index']}_col:{block['col_index']}"
    elif block.get("paragraph_index") is not None:
        return f"para:{block['paragraph_index']}"
    return "unknown_docx_anchor"

def build_xlsx_anchor(block) -> str:
    return f"{block.get('sheet_name')}!{block.get('cell_address')}"

def run_demo_mapping(excel_path: str, docx_path: str):
    print("="*60)
    print("GTPS DEMO - MAPPING ENGINE")
    print("="*60)
    
    logger = LineageLogger()
    
    print(f"1. Parsing Source Excel: {Path(excel_path).name}")
    source_blocks = extract_geometry(excel_path)
    
    print(f"2. Parsing Target Word: {Path(docx_path).name}")
    target_blocks = extract_geometry(docx_path)
    
    print("\n3. Applying Rules & Logging Lineage...")
    
    # Index source blocks by anchor
    source_map = {build_xlsx_anchor(b): b["text"] for b in source_blocks if b.get("sheet_name")}
    
    mapped_count = 0
    patches = []
    for source_anchor, target_anchors in DEMO_RULES.items():
        if source_anchor in source_map:
            value = source_map[source_anchor]
            for t_anchor in target_anchors:
                # Log the mapping
                logger.log_mapping(
                    target_anchor=t_anchor,
                    target_value=value,
                    source_file=Path(excel_path).name,
                    source_anchor=source_anchor,
                    confidence=1.0
                )
                mapped_count += 1
                patches.append((t_anchor, value))
        else:
            print(f"  [!] Source anchor not found in Excel: {source_anchor}")
            
    if patches:
        print("\n4. Writing patched values to Target Word...")
        engine = WritebackEngine()
        output_path = str(Path(docx_path).with_name(f"{Path(docx_path).stem}_patched.docx"))
        engine.apply_patches_docx(docx_path, patches, output_path)
            
    print(f"\nDone. Successfully mapped {mapped_count} elements.")
    print(f"Logs saved to {logger.log_dir}")

if __name__ == "__main__":
    base = Path(r"c:\Users\PC\Downloads\DocPercepInterac Foundation\anonymize client\Demo files\Demo files")
    excel = base / "FA&RPTS & Appendix I" / "FA&RPTs" / "HMV-FA&RPT FY2024.xlsx"
    docx = base / "Compare LF" / "HMV-26-Final-Local File for FY2024-EN-R2901KPMG_drifted.docx"
    
    if excel.exists() and docx.exists():
        run_demo_mapping(str(excel), str(docx))
    else:
        print("Demo files not found!")

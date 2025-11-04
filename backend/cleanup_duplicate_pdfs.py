#!/usr/bin/env python3
"""
Cleanup script to remove duplicate PDF files from the books directory.
Keeps the first occurrence of each unique file (by content hash).
"""

import hashlib
import asyncio
from pathlib import Path
from typing import Dict, List
import aiofiles
from config.settings import settings

async def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file."""
    sha256_hash = hashlib.sha256()
    async with aiofiles.open(file_path, "rb") as f:
        while chunk := await f.read(8192):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

async def find_duplicates(books_dir: Path) -> Dict[str, List[Path]]:
    """Find all duplicate PDFs grouped by content hash."""
    hash_to_files: Dict[str, List[Path]] = {}
    
    pdf_files = list(books_dir.glob("*.pdf"))
    print(f"Scanning {len(pdf_files)} PDF files...")
    
    for pdf_file in pdf_files:
        try:
            file_hash = await compute_file_hash(pdf_file)
            if file_hash not in hash_to_files:
                hash_to_files[file_hash] = []
            hash_to_files[file_hash].append(pdf_file)
            print(f"  {pdf_file.name}: {file_hash[:8]}...")
        except Exception as e:
            print(f"  Error processing {pdf_file.name}: {str(e)}")
    
    # Filter to only duplicates
    duplicates = {h: files for h, files in hash_to_files.items() if len(files) > 1}
    return duplicates

async def cleanup_duplicates(dry_run: bool = True):
    """Remove duplicate PDF files, keeping the first occurrence."""
    books_dir = Path(settings.BOOKS_DIR)
    
    if not books_dir.exists():
        print(f"Books directory not found: {books_dir}")
        return
    
    print(f"\n{'DRY RUN - ' if dry_run else ''}Scanning books directory: {books_dir}")
    print("=" * 80)
    
    duplicates = await find_duplicates(books_dir)
    
    if not duplicates:
        print("\n✓ No duplicate PDFs found!")
        return
    
    print(f"\n{'DRY RUN - ' if dry_run else ''}Found {len(duplicates)} sets of duplicates:")
    print("=" * 80)
    
    total_duplicates = 0
    total_size_saved = 0
    
    for file_hash, files in duplicates.items():
        # Sort by filename to have consistent ordering
        files.sort(key=lambda f: f.name)
        
        keeper = files[0]
        dupes = files[1:]
        
        print(f"\n[{file_hash[:8]}] Keeping: {keeper.name}")
        
        for dupe in dupes:
            size = dupe.stat().st_size / (1024 * 1024)  # MB
            print(f"  {'[DRY RUN] Would remove' if dry_run else 'Removing'}: {dupe.name} ({size:.2f} MB)")
            
            if not dry_run:
                try:
                    dupe.unlink()
                    print(f"    ✓ Deleted")
                except Exception as e:
                    print(f"    ✗ Error: {str(e)}")
            
            total_duplicates += 1
            total_size_saved += size
    
    print("\n" + "=" * 80)
    print(f"Summary:")
    print(f"  Duplicate groups: {len(duplicates)}")
    print(f"  Duplicate files: {total_duplicates}")
    print(f"  Space saved: {total_size_saved:.2f} MB")
    
    if dry_run:
        print(f"\n⚠️  This was a DRY RUN. No files were deleted.")
        print(f"   Run with --execute to actually remove duplicates.")

async def main():
    """Main entry point."""
    import sys
    
    dry_run = "--execute" not in sys.argv
    
    if not dry_run:
        print("⚠️  WARNING: This will DELETE duplicate PDF files!")
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != "yes":
            print("Cancelled.")
            return
    
    await cleanup_duplicates(dry_run=dry_run)

if __name__ == "__main__":
    asyncio.run(main())

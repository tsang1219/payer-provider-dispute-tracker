# Search Query Worksheet Guide

## Files Created

1. **`search_query_worksheet.csv`** - Main worksheet with 149 disputes needing research
2. **`process_worksheet_results.py`** - Script to process completed research and update enriched CSV

## How to Use

### Step 1: Open the Worksheet

Open `search_query_worksheet.csv` in Excel, Numbers, Google Sheets, or any spreadsheet app.

### Step 2: Research Each Dispute

For each dispute:

1. **Use the recommended query** (column `recommended_query`) to search on Google/Bing
   - Copy the query exactly - it's formatted for best results
   - Alternative queries are in `query_2`, `query_3`, `query_4` if needed

2. **Fill in the research columns:**
   - `search_result_url` - Paste the URL of the article/website you found
   - `article_text_excerpt` - Copy/paste relevant text from the article (optional but helpful)
   - `found_patient_count` - Enter the number (e.g., "80000" or "80,000")
   - `found_oon_date` - Enter date if found (e.g., "October 3, 2021" or "2021-10-03")
   - `found_resolution_date` - Enter resolution date if dispute is resolved
   - `notes` - Any additional notes or observations

3. **Mark as processed:**
   - Put "YES", "Y", "X", or "DONE" in the `processed` column when finished

### Step 3: Process Results

After you've researched and filled in data:

```bash
python3 process_worksheet_results.py search_query_worksheet.csv
```

This will:
- Read all rows marked as processed
- Extract patient counts, dates from your data
- Also extract from `article_text_excerpt` if you provided it
- Update `disputes_enriched.csv` automatically
- Add URLs to `primary_source_url` and `additional_sources` fields
- Update completeness scores
- Add enrichment notes

### Step 4: Verify Results

Check `output/disputes_enriched.csv` to see the updated data. The URLs will be in:
- `primary_source_url` - Main source URL
- `additional_sources` - JSON array of additional URLs (if multiple)

## Column Descriptions

### Input Columns (for reference)
- `dispute_id` - Unique ID
- `dispute_name` - Name of dispute
- `system_name` - Health system name
- `insurer_name` - Insurance company name
- `year` - Year of dispute
- `state` - State abbreviation
- `outcome_status` - Resolved, OON-Ongoing, etc.
- `recommended_query` - **Use this to search**
- `query_2`, `query_3`, `query_4` - Alternative queries
- `missing_patients`, `missing_oon_date`, `missing_resolution_date` - What's missing

### Output Columns (you fill these)
- `search_result_url` - **URL of article/website found**
- `article_text_excerpt` - Text from article (optional, but helps with extraction)
- `found_patient_count` - Number of patients (e.g., "80000")
- `found_oon_date` - Out-of-network date (e.g., "October 3, 2021")
- `found_resolution_date` - Resolution date if resolved
- `notes` - Your notes
- `processed` - Mark "YES" when done

## Tips

1. **Start with recommended query** - It's optimized for best results
2. **Copy article text** - Paste relevant text in `article_text_excerpt` - the script will extract data automatically
3. **Date formats** - Accepts various formats (October 3, 2021, 2021-10-03, Oct 3 2021)
4. **URL format** - Paste full URL (https://...)
5. **Batch processing** - Process multiple disputes, then run the script once
6. **Check `disputes_enriched.csv`** - URLs will appear in `primary_source_url` and `additional_sources` fields

## Example

Row 1:
- `recommended_query`: "Dignity Health" "Anthem Blue Cross" contract dispute 2021 patients affected
- Search Google with this query
- Find article at: https://www.beckershospitalreview.com/...
- Copy relevant text from article
- Fill in:
  - `search_result_url`: https://www.beckershospitalreview.com/...
  - `article_text_excerpt`: [paste article text]
  - `found_patient_count`: 50000 (or let script extract from text)
  - `found_oon_date`: August 1, 2021 (or let script extract from text)
  - `processed`: YES

After processing, the URL will appear in `disputes_enriched.csv` in the `primary_source_url` column.



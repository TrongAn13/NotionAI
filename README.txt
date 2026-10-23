NOTION 5-TEMPLATE BUILDER — WINDOWS

1. Extract this ZIP to a folder on your computer.
2. Install Python 3.10+ if not installed (https://www.python.org/downloads/).
3. Open PowerShell in the extracted folder.
4. Run: py build_notion.py
   (or: python build_notion.py)
5. Paste your Notion integration token into the hidden terminal prompt.
6. Type CREATE to confirm.
7. Open My Template Store in Notion and review the five created pages.

The integration must have access to My Template Store and permission to read, insert, and update content.
The script creates new pages/databases; it never deletes anything. Re-running may create duplicates.
Keep your API token secret. It is not saved to a file by this script.

LIMITATIONS
- Basic databases, sample records and page content are created automatically.
- Notion database views, advanced dashboard layouts, formulas and relations may require manual setup.
- If an API call fails partway through, previously created items remain.
- You must review, test, and style the pages before selling.

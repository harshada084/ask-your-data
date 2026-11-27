# AI "Ask Your Data" Analyst

Ask a business question in plain English and get the SQL, the result and, where suitable, a chart.
Built on the Olist Brazilian e-commerce dataset.

![App screenshot](docs/app.png)

## Business problem
Managers who don't write SQL have to wait for an analyst to answer routine questions.
This project explores answering them in plain English, using agreed business definitions.

## How it works
1. Python loads 9 CSV files into DuckDB.
2. dbt creates clean tables and runs data tests.
3. `metrics.yml` defines business terms such as revenue and late delivery rate.
4. Gemini receives the question, table and column names, and definitions, then writes SQL.
5. The app checks the SQL, runs it on DuckDB and shows the result in Streamlit.

**Tools:** Python, SQL, DuckDB, dbt, Gemini API, Streamlit

## Results
| Finding | Value |
|---|---|
| Orders loaded | 99,441 |
| Product revenue, delivered orders (without freight) | R$ 13,221,498.11 |
| Average order value | R$ 137.04 |
| Late delivery rate | 6.77% |
| Delivered orders with no delivery date | 8 (flagged, excluded from delivery metrics) |

## AI accuracy test
| Setup | Passed |
|---|---|
| With business definitions | 10/10 |
| Without business definitions | 5/10 |

The five failures without definitions were all revenue or late delivery questions.
Details are in the `tests` folder.

## Safety
- The database is opened read-only
- Only a single SELECT statement is allowed
- SQL cannot access other files
- Data rows are not sent to the AI

## Limitations
- Only 10 test questions, with one run per setup
- Reference answers follow this project's own definitions
- The AI can misread a question, so check the SQL for important decisions
- Data covers 2016-2018 and has no product costs, so profit cannot be calculated
- Runs locally

## Setup (Windows)
1. Download [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and put the CSV files in `data/raw/`.
2. Install and build:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src/load_data.py
cd dbt_olist
dbt build
cd ..
```
3. Create a `.env` file in the project folder:
```
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-3.5-flash-lite
```
4. Run:
```bash
streamlit run app/app.py
python src/evaluate.py
python src/evaluate.py --no-definitions
```

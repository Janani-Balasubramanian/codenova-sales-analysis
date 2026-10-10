"""Build and execute all notebook code cells in a local IPython interpreter."""
from pathlib import Path
import nbformat as nbf
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.capture import capture_output
from traitlets.config import Config
import os

ROOT=Path(__file__).resolve().parent
md=nbf.v4.new_markdown_cell
code=nbf.v4.new_code_cell

def main():
    nb=nbf.v4.new_notebook()
    nb.metadata.kernelspec=dict(display_name='Python 3',language='python',name='python3')
    nb.cells=[
        md('''# Retail Sales Analysis
### CodeNova Batch 01 - Task 1

**Dataset:** fictional retail orders across four regions of India, January 2024-December 2025. All monetary values are INR. This is an educational analysis of synthetic data, not evidence about actual markets.

**Questions:** Which categories drive sales and margins? How do monthly, quarterly and seasonal results differ? Where is revenue concentrated? Are the conclusions sensitive to data cleaning and bulk purchases?

The companion Task 2 project generated and cleaned the data. The standalone copies bundled here let this notebook run independently. Prices/costs are fixed in the synthetic catalog; one row is one completed order for one product, with one or more units. No refunds, taxes, shipping, operating expenses or customer demographics are modeled.'''),
        code('''from pathlib import Path
import hashlib, json, sys
import pandas as pd
from IPython.display import display, Image, Markdown
from analysis import run, ROOT
pd.set_option('display.max_columns', 12)
df, tables, metrics, checks, sensitivity, exclusion = run()
print('Python:', sys.version.split()[0])
print('Dataset SHA-256:', hashlib.sha256((ROOT/'data/sales_clean.csv').read_bytes()).hexdigest())
print(f'{len(df):,} orders; {df.order_date.min().date()} to {df.order_date.max().date()}')
display(df.head())'''),
        md('''## 1. Validate the analysis input
The cleaner handles missing fields, duplicate/conflicting IDs, invalid dates and types, reference-based recovery, and IQR flags. Here we verify the analysis contract again. `Unspecified` is an explicit unknown region; no orders disappear from geographic aggregation.'''),
        code('''assert df.order_id.is_unique
assert df.isna().sum().sum() == 0
assert df.order_date.between('2024-01-01', '2025-12-31').all()
assert df.month.nunique() == 24
assert df.discount_pct.between(0,100).all()
display(pd.DataFrame({'dtype':df.dtypes.astype(str), 'nulls':df.isna().sum()}))
display(df[['quantity','discount_pct','gross_paise','net_paise','profit_paise']].describe())'''),
        md('''## 2. Metric definitions
- **Total gross revenue:** sum(quantity x unit price), before discounts.
- **Net revenue:** gross revenue minus discounts. Discounts round half-up to the nearest paise per order.
- **Gross profit:** net revenue minus quantity x unit cost. This is not operating/net profit.
- **Gross profit margin:** total gross profit / total net revenue x 100. Do not average row margins.
- **Average order value (AOV):** total net revenue / distinct completed orders.
- **Unit volume:** total quantity.

All monetary aggregations use integer paise. INR conversion occurs only for display. One lakh = INR 100,000.'''),
        code('''kpis = pd.DataFrame([
    ('Gross revenue (INR)', metrics['gross_paise']/100),
    ('Discounts (INR)', metrics['discount_paise']/100),
    ('Net revenue (INR)', metrics['net_paise']/100),
    ('Cost of goods (INR)', metrics['cost_paise']/100),
    ('Gross profit (INR)', metrics['profit_paise']/100),
    ('Gross margin (%)', metrics['margin_pct']),
    ('Average order value (INR)', metrics['aov_inr']),
    ('Orders', metrics['orders']), ('Units', metrics['units'])], columns=['Metric','Value'])
display(kpis.style.format({'Value':'{:,.2f}'}))'''),
        md('''## 3. Monthly and quarterly performance
Compare two complete calendar years; month-over-month changes can be noisy. Year-over-year comparisons control for calendar month but still do not establish causality. The generator deliberately increases fourth-quarter order volumes and 2025 order counts.'''),
        code('''monthly=tables['month'].copy()
monthly['net_revenue_inr']=monthly.net_paise/100
monthly['mom_pct']=monthly.net_paise.pct_change()*100
monthly['yoy_pct']=monthly.net_paise.pct_change(12)*100
display(monthly[['orders','units','net_revenue_inr','margin_pct','mom_pct','yoy_pct']].round(2))
display(tables['quarter'])
display(Image(filename=str(ROOT/'output/charts/01_monthly_trends.png')))'''),
        md('''## 4. Seasonal patterns
Use explicitly defined calendar buckets: winter (December-February), pre-monsoon (March-May), monsoon (June-September), post-monsoon (October-November). These labels are an analytical convenience, not a regional climate claim. Buckets have different lengths, so compare average revenue per observed month as well as totals. December belongs to winter even though it is in Q4. Two years cannot establish robust seasonal effects.'''),
        code('''season=tables['season'].copy()
season['observed_months']=df.groupby('season').month.nunique()
season['net_inr_per_month']=season.net_paise/100/season.observed_months
display(season[['orders','units','net_paise','observed_months','net_inr_per_month']].round(2))
display(Image(filename=str(ROOT/'output/charts/02_quarterly_seasonal.png')))'''),
        md('''## 5. Category and product performance
Evaluate revenue, units and margin separately: a high-price category can lead revenue without leading volume. Category margins are weighted ratios of totals. Price/cost assumptions were designed into the synthetic catalog, so they are not discovered real-world economics.'''),
        code('''display(tables['category'].sort_values('net_paise',ascending=False).round(2))
catalog=pd.read_csv(ROOT/'data/product_catalog.csv').set_index('product_id')
display(tables['product_id'].join(catalog[['product_name','category']]).sort_values('net_paise',ascending=False).round(2))
display(Image(filename=str(ROOT/'output/charts/03_category_performance.png')))
display(Image(filename=str(ROOT/'output/charts/05_product_leaders.png')))'''),
        md('''## 6. Regional sales distribution
This fulfills the geographic-distribution requirement. No demographic inference is attempted. Shares include unknown regions, and a region's share is not adjusted for population, store count or customer exposure.'''),
        code('''regional=tables['region'].copy()
regional['net_share_pct']=100*regional.net_paise/regional.net_paise.sum()
display(regional.round(2))
display(Image(filename=str(ROOT/'output/charts/04_regional_distribution.png')))'''),
        md('''## 7. Reconcile every financial aggregation
All seven grouped dimensions must exactly reproduce five monetary totals, units and order counts. Every transaction has one category, product, region, month, quarter, year and season. These are additive partitions in this single-product-order dataset. Real multi-line orders would require special treatment of cross-category order counts.'''),
        code('''display(checks)
print(f'{len(checks)} exact reconciliation checks passed: {checks.passed.all()}')
assert metrics['gross_paise']-metrics['discount_paise']==metrics['net_paise']
assert metrics['net_paise']-metrics['cost_paise']==metrics['profit_paise']'''),
        md('''## 8. Sensitivity and limitations
Quantity outliers are retained because bulk orders can be legitimate. The exclusion scenario is a sensitivity test, not a recommendation to delete them. Also examine unique source IDs absent after cleaning: duplicate rows do not count as lost business. Blank IDs cannot be assigned to a unique order, and unparseable dates appear under `NaT`. Defects were injected into early 2024 rows, so year-over-year growth is partly affected by cleaning losses.'''),
        code('''display(sensitivity.round(2))
print(f"Flagged orders: {metrics['outlier_orders']}; share of net revenue: {metrics['outlier_net_share_pct']:.2f}%")
display(exclusion.round(2))'''),
        md('''## 9. Executive findings and recommended next steps
The following statements are computed from the retained dataset. Recommendations describe what to validate in a real business; they do not establish that an intervention would cause higher sales.'''),
        code('''cat=tables['category']; region=tables['region']; year=tables['year']
top=cat.net_paise.idxmax(); margin=cat.margin_pct.idxmax(); units=cat.units.idxmax()
share=100*cat.loc[top,'net_paise']/metrics['net_paise']
growth=100*(year.loc[2025,'net_paise']/year.loc[2024,'net_paise']-1)
display(Markdown(f"""
- **Revenue mix:** {top} contributes {share:.1f}% of net revenue. Review availability and stockouts for its leading products before increasing inventory.
- **Margin opportunity:** {margin} has the highest gross margin ({cat.loc[margin,'margin_pct']:.1f}%). Test a small cross-sell pilot; measure incremental profit after marketing and returns.
- **Volume:** {units} leads units sold ({int(cat.loc[units,'units']):,}). Compare replenishment needs using units, not just revenue.
- **Timing:** Net revenue changes {growth:.1f}% from 2024 to 2025. Plan capacity around observed peaks, while accounting for injected growth and early-period cleaning losses.
- **Geography:** {region.net_paise.idxmax()} leads net revenue. Obtain customer/store exposure before judging market penetration or allocating budget.
- **Concentration:** Quantity outliers contribute {metrics['outlier_net_share_pct']:.1f}% of net revenue. Validate bulk orders operationally before treating their demand as recurring.

**Limits:** Synthetic sampling, only two years, fixed catalog economics, no returns/tax/operating costs, deliberate defects, unknown regions, and no causal design. No external market conclusion is supported.
"""))'''),
        md('''## Reproduction and artifact index
Run `python analysis.py` to rebuild tables and five 240-DPI chart exports. Run `python build_notebook.py` to rebuild this fully executed notebook. Run `python -m unittest discover -s tests -v` for financial checks. See `README.md`, `DATA_DICTIONARY.md`, `output/metrics.json`, and `output/tables/reconciliation.csv`.

Source: local synthetic generator `generate_data.py` in the companion `codenova-data-cleaning` project; seed 20261010. No external dataset or paid service was used.''')]
    # Execute genuinely in-process: no background kernel/server or runtime files needed.
    # Every cell runs in the same IPython namespace; exceptions abort the build.
    os.chdir(ROOT)
    config=Config()
    config.HistoryManager.enabled=False
    config.HistoryManager.hist_file=':memory:'
    shell=InteractiveShell.instance(config=config)
    count=0
    for cell in nb.cells:
        if cell.cell_type != 'code':
            continue
        count+=1
        print(f'Executing code cell {count}',flush=True)
        with capture_output() as captured:
            result=shell.run_cell(cell.source,store_history=False)
        result.raise_error()
        cell.execution_count=count
        cell.outputs=[]
        if captured.stdout:
            cell.outputs.append(nbf.v4.new_output('stream',name='stdout',text=captured.stdout))
        if captured.stderr:
            cell.outputs.append(nbf.v4.new_output('stream',name='stderr',text=captured.stderr))
        for item in captured.outputs:
            cell.outputs.append(nbf.v4.new_output('display_data',data=item.data,metadata=item.metadata))
    nb.metadata['execution_method']='All code cells executed sequentially in a shared local IPython interpreter.'
    nbf.write(nb,ROOT/'sales_analysis.ipynb')
    print(f'Executed {sum(c.cell_type=="code" for c in nb.cells)} code cells; saved sales_analysis.ipynb')

if __name__=='__main__': main()

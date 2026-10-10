"""Exact-paise financial analysis and reproducible chart exports."""
import json
from decimal import Decimal
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT=Path(__file__).resolve().parent
SEASONS={12:'Winter',1:'Winter',2:'Winter',3:'Pre-monsoon',4:'Pre-monsoon',5:'Pre-monsoon',
         6:'Monsoon',7:'Monsoon',8:'Monsoon',9:'Monsoon',10:'Post-monsoon',11:'Post-monsoon'}
MONEY=['gross_paise','net_paise','cost_paise','profit_paise','discount_paise']

def load_data(path=ROOT/'data/sales_clean.csv'):
    df=pd.read_csv(path,dtype={'unit_price':str,'unit_cost':str})
    df['order_date']=pd.to_datetime(df.order_date,format='%Y-%m-%d')
    assert df.order_id.is_unique and df.order_id.notna().all()
    assert df.quantity.gt(0).all() and df.quantity.mod(1).eq(0).all()
    for c in ['unit_price','unit_cost']:
        df[c+'_paise']=df[c].map(lambda v: int(Decimal(v)*100))
    df['gross_paise']=df.quantity*df.unit_price_paise
    # Round discount to nearest paise, half up, per order using exact integer arithmetic.
    df['discount_paise']=(df.gross_paise*df.discount_pct+50)//100
    df['net_paise']=df.gross_paise-df.discount_paise
    df['cost_paise']=df.quantity*df.unit_cost_paise
    df['profit_paise']=df.net_paise-df.cost_paise
    df['month']=df.order_date.dt.to_period('M').astype(str)
    df['quarter']=df.order_date.dt.to_period('Q').astype(str)
    df['year']=df.order_date.dt.year
    df['season']=df.order_date.dt.month.map(SEASONS)
    return df

def aggregate(df,dimension):
    table=df.groupby(dimension,dropna=False).agg(**{c:(c,'sum') for c in MONEY},
        units=('quantity','sum'),orders=('order_id','nunique'))
    table['margin_pct']=100*table.profit_paise/table.net_paise.replace(0,np.nan)
    table['aov_inr']=table.net_paise/100/table.orders
    return table

def reconcile(df,tables):
    checks=[]
    for dimension,table in tables.items():
        for metric in MONEY+['units','orders']:
            expected=int(df[metric].sum()) if metric in MONEY else int(df.quantity.sum()) if metric=='units' else df.order_id.nunique()
            observed=int(table[metric].sum())
            checks.append(dict(dimension=dimension,metric=metric,expected=expected,observed=observed,passed=observed==expected))
    checks=pd.DataFrame(checks)
    assert checks.passed.all(),'Grouped totals failed reconciliation'
    assert (df.gross_paise-df.discount_paise==df.net_paise).all()
    assert (df.net_paise-df.cost_paise==df.profit_paise).all()
    return checks

def export_charts(df,tables,charts):
    charts.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,
        'axes.spines.right':False,'axes.titleweight':'bold','figure.facecolor':'white'})
    def save(fig,name):
        fig.savefig(charts/name,dpi=240,bbox_inches='tight'); plt.close(fig)
    def label_money(ax): ax.yaxis.set_major_formatter(FuncFormatter(lambda v,pos:f'{v/100000:.1f}'))
    monthly=tables['month']
    fig,ax=plt.subplots(figsize=(12,5),layout='constrained')
    x=np.arange(len(monthly)); y=monthly.net_paise/100
    ax.plot(x,y,marker='o',color='#0f766e',lw=2.5,label='Net revenue')
    ax.plot(x,monthly.profit_paise/100,marker='.',color='#2563eb',lw=2,label='Gross profit')
    peak=int(np.argmax(y.values)); ax.annotate(f'Peak: {monthly.index[peak]}',xy=(peak,y.iloc[peak]),
        xytext=(-90,20),textcoords='offset points',arrowprops={'arrowstyle':'->','color':'#475569'})
    ax.set_ylim(0,y.max()*1.25); ax.set_xticks(x[::2],monthly.index[::2],rotation=35,ha='right')
    ax.set_ylabel('INR lakh'); label_money(ax); ax.legend(loc='upper left',frameon=False)
    ax.set_title('Monthly sales and gross profit | Synthetic retail'); ax.grid(axis='y',alpha=.15)
    save(fig,'01_monthly_trends.png')
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    q=tables['quarter']; bars=axes[0].bar(q.index,q.net_paise/100,color='#0f766e')
    axes[0].tick_params(axis='x',rotation=40); axes[0].set_title('Quarterly net revenue'); axes[0].set_ylabel('INR lakh'); label_money(axes[0])
    seasons=tables['season'].reindex(['Winter','Pre-monsoon','Monsoon','Post-monsoon']).copy()
    # Unequal-length season groups: compare per calendar month, not just totals.
    seasons['observed_months']=df.groupby('season').month.nunique()
    v=seasons.net_paise/100/seasons.observed_months
    bars=axes[1].bar(v.index,v,color='#2563eb'); axes[1].tick_params(axis='x',rotation=25)
    axes[1].set_title('Seasonal average per observed month'); axes[1].set_ylabel('INR lakh / month'); label_money(axes[1])
    fig.suptitle('Time patterns | 24 complete calendar months; synthetic data',fontweight='bold')
    save(fig,'02_quarterly_seasonal.png')
    category=tables['category'].sort_values('net_paise')
    fig,axes=plt.subplots(1,3,figsize=(15,5),layout='constrained')
    for ax,col,title,div in zip(axes,['net_paise','units','margin_pct'],['Net revenue (INR lakh)','Units sold','Gross margin (%)'],[10000000,1,1]):
        v=category[col]/div; bars=ax.barh(category.index,v,color='#0f766e')
        ax.bar_label(bars,fmt='%.1f' if col!='units' else '%.0f',padding=4)
        ax.set_xlim(0,v.max()*1.25); ax.set_title(title); ax.grid(axis='x',alpha=.1)
    fig.suptitle('Category performance | Synthetic retail',fontweight='bold')
    save(fig,'03_category_performance.png')
    region=tables['region'].sort_values('net_paise')
    fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
    v=100*region.net_paise/region.net_paise.sum(); bars=ax.barh(region.index,v,color='#2563eb')
    ax.bar_label(bars,fmt='%.1f%%',padding=4); ax.set_xlim(0,v.max()*1.2)
    ax.set_xlabel('Share of net revenue (%)\nSynthetic allocations; not market estimates.',labelpad=10)
    ax.set_title('Regional distribution | Unknown geography retained')
    save(fig,'04_regional_distribution.png')
    products=tables['product_id'].sort_values('net_paise',ascending=False).head(8).iloc[::-1]
    catalog=pd.read_csv(ROOT/'data/product_catalog.csv').set_index('product_id')
    fig,ax=plt.subplots(figsize=(11,6),layout='constrained')
    v=products.net_paise/10000000; bars=ax.barh(catalog.loc[products.index,'product_name'],v,color='#0f766e')
    ax.bar_label(bars,fmt='%.2f',padding=4); ax.set_xlim(0,v.max()*1.2)
    ax.set_xlabel('Net revenue (INR lakh)'); ax.set_title('Top eight products by net revenue | Synthetic retail')
    save(fig,'05_product_leaders.png')

def run(output=ROOT/'output'):
    output=Path(output); (output/'tables').mkdir(parents=True,exist_ok=True)
    df=load_data()
    tables={d:aggregate(df,d) for d in ['month','quarter','season','category','region','product_id','year']}
    checks=reconcile(df,tables); checks.to_csv(output/'tables/reconciliation.csv',index=False)
    for d,t in tables.items(): t.to_csv(output/'tables'/f'{d}.csv')
    metrics={c:int(df[c].sum()) for c in MONEY}
    metrics.update(orders=int(df.order_id.nunique()),units=int(df.quantity.sum()),
        margin_pct=float(100*df.profit_paise.sum()/df.net_paise.sum()),
        aov_inr=float(df.net_paise.sum()/100/df.order_id.nunique()),
        outlier_orders=int(df.quantity_outlier.sum()),
        outlier_net_share_pct=float(100*df.loc[df.quantity_outlier,'net_paise'].sum()/df.net_paise.sum()))
    (output/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n',encoding='utf-8')
    flagged=df.quantity_outlier
    sensitivity=pd.DataFrame([dict(scope=label,orders=len(part),net_inr=part.net_paise.sum()/100,
        gross_profit_inr=part.profit_paise.sum()/100,aov_inr=part.net_paise.sum()/100/len(part))
        for label,part in [('All retained orders',df),('Excluding flagged orders (sensitivity only)',df.loc[~flagged])]])
    sensitivity.to_csv(output/'tables/outlier_sensitivity.csv',index=False)
    # Exclusion bias: distinct IDs absent from clean data, not duplicate rows.
    raw=pd.read_csv(ROOT/'data/sales_raw.csv',dtype=str,keep_default_na=False)
    raw=raw.loc[raw.order_id.ne('')].drop_duplicates('order_id')
    raw['date']=pd.to_datetime(raw.order_date,format='mixed',dayfirst=True,errors='coerce')
    raw['quarter']=raw.date.dt.to_period('Q').astype(str)
    raw['excluded']=~raw.order_id.isin(df.order_id)
    impact=raw.groupby('quarter').agg(identifiable_source_orders=('order_id','nunique'),excluded_orders=('excluded','sum'))
    impact['exclusion_pct']=100*impact.excluded_orders/impact.identifiable_source_orders
    impact.to_csv(output/'tables/exclusion_by_quarter.csv')
    export_charts(df,tables,output/'charts')
    return df,tables,metrics,checks,sensitivity,impact

if __name__=='__main__':
    _,_,metrics,checks,_,_=run()
    print(json.dumps(metrics,indent=2)); print(f'{len(checks)} reconciliation checks passed.')

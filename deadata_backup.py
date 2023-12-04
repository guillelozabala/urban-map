import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter
import matplotlib.colors as mcolors
import geopandas as gpd
from shapely.geometry import Polygon
import os
import wget

#wget.download("https://www2.census.gov/geo/tiger/GENZ2018/shp/cb_2018_us_county_500k.zip")

gdf = gpd.read_file('C:/Users/guill/Documents/Scripts/urban/cb_2018_us_county_500k')

df1 = pd.read_csv('C:/Users/guill/Documents/Scripts/urban/hydrocodone_agg.csv',index_col=0)
df1 = df1.rename(columns={'sum(DOSAGE_UNIT)':'hydrocodone'})

df2 = pd.read_csv('C:/Users/guill/Documents/Scripts/urban/oxycodone_agg.csv',index_col=0)
df2 = df2.rename(columns={'sum(DOSAGE_UNIT)':'oxycodone'})

df = df1.merge(df2, how='outer', on = ['BUYER_STATE','BUYER_COUNTY','year','month'])
df['hydrocodone'] = df['hydrocodone'].fillna(0)
df['oxycodone'] = df['oxycodone'].fillna(0)
df['total'] = df['hydrocodone'] + df['oxycodone']
df = df[['BUYER_STATE','BUYER_COUNTY','year','month','total']]

df_remaining = pd.read_csv('C:/Users/guill/Documents/Scripts/urban/county_monthly14.csv')
df_remaining = df_remaining[['BUYER_STATE','BUYER_COUNTY','year','month','DOSAGE_UNIT']]
df_remaining = df_remaining[df_remaining['year']>2012]
df_remaining = df_remaining.rename(columns={'DOSAGE_UNIT':'total'})

df = pd.concat([df,df_remaining])

df = df[df['BUYER_STATE']!='PR'] #no Puerto Rico
df = df[df['BUYER_STATE']!='VI'] #no Virgin Islands
df = df[df['BUYER_STATE']!='GU'] #no Guam
df = df[df['BUYER_STATE']!='MP'] #no Mariana Islands
df = df[df['BUYER_STATE']!='AE'] #no Armed Forces Europe
df = df[df['BUYER_STATE']!='PW'] #no Palau
df = df[~pd.isnull(df['BUYER_COUNTY'])]

countyids = pd.read_csv('C:/Users/guill/Documents/Scripts/urban/county_fips.csv')
countyids['countyfips'] = countyids['countyfips'].astype(str).str.zfill(5)

df = df.merge(countyids, how='outer', on = ['BUYER_STATE','BUYER_COUNTY'])
df[(df['BUYER_STATE'] == 'AR') & (df['BUYER_COUNTY'] == 'MONTGOMERY')] = df[(df['BUYER_STATE'] == 'AR') & (df['BUYER_COUNTY'] == 'MONTGOMERY')].assign(countyfips = '05097')
df = df.rename(columns={'countyfips':'GEOID'})

dfpop = pd.read_csv('C:/Users/guill/Documents/Scripts/urban/population0612.csv',index_col=0)
dfpop['state_fip'] = dfpop['state_fip'].astype(str).str.zfill(2)
dfpop['county_fip'] = dfpop['county_fip'].astype(str).str.zfill(3)
dfpop['GEOID'] = dfpop['state_fip'] + dfpop['county_fip'] 
dfpop = dfpop.rename(columns={'state':'BUYER_STATE'})
dfpop = dfpop[['year','BUYER_STATE','GEOID','population']]

df_pills = df.merge(dfpop, how='outer', on = ['BUYER_STATE','year','GEOID'])
df_pills[pd.isnull(df_pills['total'])] = df_pills[pd.isnull(df_pills['total'])].assign(total = 0.0)
df_pills['pills_pc'] = df_pills['total']/df_pills['population']
df_pills = df_pills[['year','month','BUYER_STATE','BUYER_COUNTY','GEOID','pills_pc']]

pdmp = pd.read_stata('C:/Users/guill/Documents/Scripts/urban/PDMP.dta')
pdmp = pdmp[['statefip','statecode','mopdmp_year','mopdmp_month']]
pdmp = pdmp.rename(columns={'statecode':'BUYER_STATE','mopdmp_year':'year','mopdmp_month':'month'})
pdmp['statefip'] = pdmp['statefip'].astype(str).str.zfill(2)

df_pills['treatment'] = 0

for i in np.unique(pdmp['BUYER_STATE']):
    p_year = np.array(pdmp[pdmp['BUYER_STATE']==i])[0,2]
    p_month = np.array(pdmp[pdmp['BUYER_STATE']==i])[0,3]
    if p_year < 2006:
        df_pills[df_pills['BUYER_STATE'] == i] = df_pills[df_pills['BUYER_STATE'] == i].assign(treatment = 1.0)
    elif 2005 < p_year < 2015:
        for j in range(2006,2015):
            if p_year < j:
                df_pills[(df_pills['BUYER_STATE'] == i)&(df_pills['year'] == j)] = df_pills[(df_pills['BUYER_STATE'] == i)&(df_pills['year'] == j)].assign(treatment = 1.0)
            elif p_year == j:
                for k in range(1,13):
                    if p_month <= k:
                        df_pills[(df_pills['BUYER_STATE'] == i)&(df_pills['year'] == j)&(df_pills['month'] == k)] = df_pills[(df_pills['BUYER_STATE'] == i)&(df_pills['year'] == j)&(df_pills['month'] == k)].assign(treatment = 1.0)


df_final = df_pills.merge(gdf,how='outer',on='GEOID')
df_final = gpd.GeoDataFrame(df_final)


for i in range(2006,2015):
    for j in range(1,13):

        variable = 'pills_pc'

        year,month = i, j
        vmin, vmax = 0, 25 

        colormap_reg, colormap_pdmp = 'OrRd', 'BuPu'

        df_plot = df_final[(df_final['year'] == year) & (df_final['month'] == month)]

        remaining = df_final[df_final['GEOID'].isin(set(df_final.GEOID) - set(df_plot.GEOID))]
        remaining = remaining[~remaining.duplicated('GEOID')]

        for k in pd.unique(remaining['STATEFP']):
            if df_plot[(df_plot['STATEFP'] == k)&(df_plot['year'] == year)&(df_plot['month'] == month)].empty == False:
                comparison = df_plot[(df_plot['STATEFP'] == k)&(df_plot['year'] == year)&(df_plot['month'] == month)].iloc[0]
            if comparison.treatment == 1:
                remaining[remaining['STATEFP'] == k] = remaining[remaining['STATEFP'] == k].assign(treatment = 1)


        df_plot = pd.concat([df_plot,remaining])

        fig, ax = plt.subplots(1, figsize=(18, 14))
        ax.set(xlim=(-2.5e6, 3e6), ylim=(-2.5e6, 1.25e6))  
        ax.axis('off')

        hfont = {'fontname':'serif'}


        ax.set_title(f'The Opioid Crisis:\n Hydrocodone and Oxycodone pills per capita and\n Prescription Drug Monitoring Programs in {str(month).zfill(2)}/{year}', **hfont, fontdict={'fontsize': '40', 'fontweight' : '1'})

        cbax1 = fig.add_axes([0.87, 0.21, 0.03, 0.31]) 
        sm1 = plt.cm.ScalarMappable(cmap=colormap_reg,norm=plt.Normalize(vmin=vmin, vmax=vmax))
        sm1._A = []
        fig.colorbar(sm1, cax=cbax1)

        cbax2 = fig.add_axes([0.92, 0.21, 0.03, 0.31]) 
        sm2 = plt.cm.ScalarMappable(cmap=colormap_pdmp,norm=plt.Normalize(vmin=vmin, vmax=vmax))
        sm2._A = []
        fig.colorbar(sm2, cax=cbax2)


        df_ante = df_plot[(~df_plot['BUYER_STATE'].isin(['AK','HI'])) & (df_plot['treatment'] == 0)]
        visframe_ante = df_ante.to_crs({'init':'epsg:2163'})
        visframe_ante.plot(variable,linewidth=0.8,ax=ax,vmin=vmin,vmax=vmax,edgecolor='0.8',aspect=1,missing_kwds= dict(color = "lightgrey"),cmap = colormap_reg)

        df_post = df_plot[(~df_plot['BUYER_STATE'].isin(['AK','HI'])) & (df_plot['treatment'] == 1)]
        visframe_post = df_post.to_crs({'init':'epsg:2163'})
        visframe_post.plot(variable,linewidth=0.8,ax=ax,vmin=vmin,vmax=vmax,edgecolor='0.8',aspect=1,missing_kwds= dict(color = "lightgrey"),cmap = colormap_pdmp)

        left_al, bottom_al, width_al, height_al = [0.15, 0.0, 0.15, 0.4] 
        ax2 = fig.add_axes([left_al, bottom_al, width_al, height_al])
        ax2.axis('off')

        alaska_ante = df_plot[(df_plot['BUYER_STATE'] == 'AK') & (df_plot['treatment'] == 0)]
        polygon = Polygon([(-170,50),(-170,72),(-140, 72),(-140,50)])
        alaska_ante.clip(polygon).plot(variable,linewidth=0.8,ax=ax2,vmin=vmin,vmax=vmax, edgecolor='0.8',aspect=1,missing_kwds= dict(color = "lightgrey"),cmap = colormap_reg)

        alaska_post = df_plot[(df_plot['BUYER_STATE'] == 'AK') & (df_plot['treatment'] == 1)]
        polygon = Polygon([(-170,50),(-170,72),(-140, 72),(-140,50)])
        alaska_post.clip(polygon).plot(variable,linewidth=0.8,ax=ax2,vmin=vmin,vmax=vmax, edgecolor='0.8',aspect=1,missing_kwds= dict(color = "lightgrey"),cmap = colormap_pdmp)


        left_ha, bottom_ha, width_ha, height_ha = [0.32, 0.1, 0.1, 0.3]
        ax3 = fig.add_axes([left_ha, bottom_ha, width_ha, height_ha])  
        ax3.axis('off')

        hawaii_ante = df_plot[(df_plot['BUYER_STATE'] == 'HI') & (df_plot['treatment'] == 0)]
        hipolygon = Polygon([(-160,0),(-160,90),(-120,90),(-120,0)])
        hawaii_ante.clip(hipolygon).plot(variable,linewidth=0.8,ax=ax3,vmin=vmin,vmax=vmax, edgecolor='0.8',aspect=1,missing_kwds= dict(color = "lightgrey"),cmap = colormap_reg)

        hawaii_post = df_plot[(df_plot['BUYER_STATE'] == 'HI') & (df_plot['treatment'] == 1)]
        hipolygon = Polygon([(-160,0),(-160,90),(-120,90),(-120,0)])
        hawaii_post.clip(hipolygon).plot(variable,linewidth=0.8,ax=ax3,vmin=vmin,vmax=vmax, edgecolor='0.8',aspect=1,missing_kwds= dict(color = "lightgrey"),cmap = colormap_pdmp)


        text = fig.text(0.50, 0.02,f'A Prescription Drug Monitoring Program is an electronic database that tracks controlled substance prescriptions in a state. They can be used to\n send "proactive" reports to authorized users to protect patients at the higher risk and identify inappropiate prescribing trends.\n States that passed a modern PDMP by {str(month).zfill(2)}/{year} are colored in a blue shade.', horizontalalignment='center',wrap=True,**hfont, fontdict={'fontsize': '15', 'fontweight' : '1'}) 

        fig.savefig(f'C:/Users/guill/Documents/Scripts/urban/plots_pdmp_opi/{year}{str(month).zfill(2)}.png',dpi=400, bbox_inches="tight")
        plt.close()
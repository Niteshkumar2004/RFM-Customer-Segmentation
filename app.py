import streamlit as st
import pandas as pd, numpy as np
import plotly.express as px
from pathlib import Path
st.set_page_config(page_title="RFM Customer Segmentation",page_icon="👥",layout="wide")
ROOT=Path(__file__).parent
st.markdown("""<style>.stApp{background:#F5F8FC}[data-testid="stMetric"]{background:white;padding:16px;border:1px solid #E5EAF1;border-radius:14px}.hero{padding:24px;background:linear-gradient(110deg,#102A43,#2563EB);border-radius:16px;color:white}.hero h1{color:white}.hero p{color:#DBEAFE}</style><div class="hero"><h1>RFM Customer Segmentation & Target Marketing</h1><p>Customer value • K-Means clustering • export-ready audiences</p></div>""",unsafe_allow_html=True)
@st.cache_data
def load(f): return pd.read_csv(f,parse_dates=["order_date"])
up=st.sidebar.file_uploader("Upload transactions CSV",type="csv")
try: raw=load(up if up else ROOT/"data/transactions.csv")
except Exception as e: st.error(str(e)); st.stop()
required={"customer_id","email","order_id","order_date","amount"}
if not required.issubset(raw.columns): st.error("Required columns: "+", ".join(sorted(required))); st.stop()
raw["amount"]=pd.to_numeric(raw.amount,errors="coerce"); raw["order_date"]=pd.to_datetime(raw.order_date,errors="coerce")
raw=raw.dropna(subset=["customer_id","email","order_id","order_date","amount"]); raw=raw[(raw.amount>=0)].drop_duplicates("order_id")
if raw.empty: st.warning("No valid transactions."); st.stop()
asof=st.sidebar.date_input("Analysis date",(raw.order_date.max()+pd.Timedelta(days=1)).date())
k=st.sidebar.slider("K-Means clusters",3,6,4)
rfm=raw.groupby("customer_id").agg(Recency=("order_date",lambda x:(pd.Timestamp(asof)-x.max()).days),Frequency=("order_id","nunique"),Monetary=("amount","sum"),email=("email","first"),customer_name=("customer_name","first") if "customer_name" in raw else ("email","first")).reset_index()
rfm["Recency"]=rfm.Recency.clip(lower=0)
def score(s,reverse=False):
    z=np.ceil(s.rank(method="first",pct=True)*5).clip(1,5).astype(int)
    return 6-z if reverse else z
rfm["R_Score"]=score(rfm.Recency,True); rfm["F_Score"]=score(rfm.Frequency); rfm["M_Score"]=score(rfm.Monetary)
rfm["RFM_Score"]=rfm[["R_Score","F_Score","M_Score"]].astype(str).agg("".join,axis=1)
X=np.log1p(rfm[["Recency","Frequency","Monetary"]].astype(float).values); X=(X-X.mean(0))/np.where(X.std(0)==0,1,X.std(0))
def kmeans(X,k):
    rng=np.random.default_rng(42); centers=X[rng.choice(len(X),k,replace=False)]
    labels=np.zeros(len(X),int)
    for _ in range(100):
        new=((X[:,None,:]-centers[None,:,:])**2).sum(2).argmin(1)
        nc=np.array([X[new==j].mean(0) if (new==j).any() else X[rng.integers(len(X))] for j in range(k)])
        if np.array_equal(new,labels) and np.allclose(nc,centers): break
        labels,centers=new,nc
    return labels
rfm["Cluster"]=kmeans(X,k)
q=rfm.groupby("Cluster").agg(r=("Recency","mean"),f=("Frequency","mean"),m=("Monetary","mean"))
q["quality"]=-q.r.rank(pct=True)+q.f.rank(pct=True)+q.m.rank(pct=True)
labels=["VIP Champions","Loyal Customers","At-Risk Customers","Lost Customers","Potential Loyalists","New Customers"]
rfm["Segment"]=rfm.Cluster.map({c:labels[i] for i,c in enumerate(q.sort_values("quality",ascending=False).index)})
st.subheader("Customer intelligence overview")
a,b,c,d=st.columns(4); a.metric("Customers",f"{len(rfm):,}"); b.metric("Customer revenue",f"${rfm.Monetary.sum():,.0f}"); c.metric("VIP Champions",f"{(rfm.Segment=='VIP Champions').sum():,}"); d.metric("Average order value",f"${raw.amount.mean():,.2f}")
l,r=st.columns(2)
with l: st.subheader("Segment distribution"); st.plotly_chart(px.pie(rfm,names="Segment",hole=.5),use_container_width=True)
with r: st.subheader("Revenue by segment"); st.plotly_chart(px.bar(rfm.groupby("Segment",as_index=False).Monetary.sum(),x="Segment",y="Monetary",color="Segment"),use_container_width=True)
st.divider(); st.subheader("RFM customer explorer")
segments=sorted(rfm.Segment.unique()); selected=st.multiselect("Filter segments",segments,default=segments)
view=rfm[rfm.Segment.isin(selected)]
st.dataframe(view[["customer_id","customer_name","email","Recency","Frequency","Monetary","RFM_Score","Segment"]].sort_values("Monetary",ascending=False),use_container_width=True,hide_index=True)
st.subheader("Export target audience")
seg=st.selectbox("Select audience",segments); audience=rfm[rfm.Segment==seg][["customer_id","customer_name","email","Recency","Frequency","Monetary","RFM_Score","Segment"]]
st.download_button(f"Download {seg} email list ({len(audience)} customers)",audience.to_csv(index=False).encode(),file_name=seg.lower().replace(" ","_")+"_audience.csv",mime="text/csv")
st.download_button("Download full RFM table",rfm.to_csv(index=False).encode(),file_name="rfm_customer_segments.csv",mime="text/csv")
st.caption("RFM scores use quintile ranks. K-Means uses standardized log-transformed RFM values. Cluster labels are assigned by relative average RFM quality. Demo data is synthetic; validate segments and consent before campaign activation.")

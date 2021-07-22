import streamlit as st
# To make things easier later, we're also importing numpy and pandas for
# working with sample data.
import numpy as np
import pandas as pd

gtts = pd.read_excel('./plot_df/gtts.xlsx')
st.dataframe(gtts)

holding = pd.read_excel('./plot_df/holding.xlsx')
st.dataframe(holding)

positions = pd.read_excel('./plot_df/positions.xlsx')
st.dataframe(positions)
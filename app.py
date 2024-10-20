

import streamlit as st
import folium
from streamlit_folium import st_folium

import pandas as pd
import requests

st.set_page_config(
    page_title="使用ヘルメット別の医療機関等の地図",
    page_icon="👶",
    layout="wide"
)

@st.cache_data
def fetch_data(url):
    response = requests.get(url)
    return response.json()
    
url = st.secrets["API_URL"]

response = requests.get(url)
data = fetch_data(url)  # キャッシュされたデータを使用

helmets = ['ベビーバンド', 'スターバンド', 'スターバンド調整', 'クルムフィット', 'リモベビー', 'プロモメット', 'HANI Helmet', 'GIO Helmet']

df = pd.DataFrame()

count = {}

for helmet in helmets:
  df_temp = pd.DataFrame(data[helmet])
  print(df_temp.columns)
  if '削除日' in df_temp.columns:
    df_temp = df_temp[df_temp['削除日']== '']
  df_temp = df_temp[df_temp['医療機関名'] != '']
  df_temp = df_temp[['医療機関名', '住所', '緯度', '経度', 'URL']]
  df_temp = df_temp.dropna()
  count[helmet] = str(len(df_temp))
  df_temp['ヘルメット'] = helmet
  df = pd.concat([df, df_temp])

# 地図の初期設定（初期表示位置を東京に設定）
m = folium.Map(location=[35.6895, 139.6917], zoom_start=6)

# 色を指定する関数
def get_marker_color(name):
    if name == 'クルムフィット':
        return 'lightgray'
        #return '#D3D3D3'
    elif name == 'ベビーバンド':
        return 'pink'
        #return 'FFC0CB'
    elif name == 'スターバンド':
        return 'orange'
        #return 'FFA500'
    elif name == 'スターバンド調整':
        return 'red'
        #return 'FFA500'
    elif name == 'リモベビー':
        return 'beige'
        #return 'F5F5DC'
    elif name == 'プロモメット':
        return 'lightblue'
        #return 'ADD8E6'
    elif name == 'HANI Helmet':
        return 'blue'
    else:  #GIO Helmet
        return 'navy'

# レイヤーコントロールを使用して各都市のマーカーを別々のレイヤーに追加
fg_q = folium.FeatureGroup(name='クルムフィット').add_to(m)
fg_bb = folium.FeatureGroup(name='ベビーバンド').add_to(m)
fg_sb = folium.FeatureGroup(name='スターバンド').add_to(m)
fg_sba = folium.FeatureGroup(name='スターバンド調整').add_to(m)
fg_rb = folium.FeatureGroup(name='リモベビー').add_to(m)
fg_pm = folium.FeatureGroup(name='プロモメット').add_to(m)
fg_hh = folium.FeatureGroup(name='HANI Helmet').add_to(m)
fg_gh = folium.FeatureGroup(name='GIO Helmet').add_to(m)

# データフレームの各行を地図にプロット
for index, row in df.iterrows():
    #<a href="https://www.ncchd.go.jp/" target="_blank" rel="noreferrer noopener">国立研究開発法人 国立成育医療研究ｾﾝﾀｰ</a>
    if row['URL'] != '':
        if row['ヘルメット'] in ['スターバンド調整', 'HANI Helmet', 'GIO Helmet']:
          popup_content = f"""
            <b>施設名:</b> <a href={row['URL']} target="_blank">{row['医療機関名']}</a><br>
            {row['ヘルメット']}<br>
            {row['住所']}<br>
            """
        else:
          popup_content = f"""
            <b>医療機関名:</b> <a href={row['URL']} target="_blank">{row['医療機関名']}</a><br>
            <b>ヘルメット:</b> {row['ヘルメット']}<br>
            {row['住所']}<br>
            """
    else:
        if row['ヘルメット'] in ['スターバンド調整', 'HANI Helmet', 'GIO Helmet']:
          popup_content = f"""
            <b>施設名:</b> {row['医療機関名']}<br>
            {row['ヘルメット']}<br>
            {row['住所']}<br>
            """
        else:
          popup_content = f"""
            <b>医療機関名:</b> {row['医療機関名']}<br>
            <b>ヘルメット:</b> {row['ヘルメット']}<br>
            {row['住所']}<br>
            """        
            
    #if row['URL'] != '':
        #popup_content += f"{row['URL']}<br>"

    #iframe = folium.IFrame(popup_content, width=200, height=100)
    #popup = folium.Popup(iframe, max_width=2000)
    popup = folium.Popup(popup_content, max_width=2000)  # max_width=200

    marker = folium.Marker(
        location=[row['緯度'], row['経度']],
        popup=popup,
        icon=folium.Icon(color=get_marker_color(row['ヘルメット']))
    )

    if row['ヘルメット'] == 'クルムフィット':
      marker.add_to(fg_q)
    if row['ヘルメット'] == 'ベビーバンド':
      marker.add_to(fg_bb)
    if row['ヘルメット'] == 'スターバンド':
      marker.add_to(fg_sb)
    if row['ヘルメット'] == 'スターバンド調整':
      marker.add_to(fg_sba)
    if row['ヘルメット'] == 'リモベビー':
      marker.add_to(fg_rb)
    if row['ヘルメット'] == 'プロモメット':
      marker.add_to(fg_pm)
    if row['ヘルメット'] == 'HANI Helmet':
      marker.add_to(fg_hh)
    if row['ヘルメット'] == 'GIO Helmet':
      marker.add_to(fg_gh)

# レイヤーコントロールを地図に追加
folium.LayerControl().add_to(m)

#st.write('ヘルメットの種類ごとに色分けされた医療機関の地図')
# タイトルの中央揃え
st.markdown('<div style="text-align: center; color:black; font-size:24px; font-weight: bold;">ヘルメットの種類ごとに色分けされた医療機関の地図</div>', unsafe_allow_html=True)

# 同じ行に表示して中央揃え
st.markdown(
    f"""
    <div style="display: flex; justify-content: center; align-items: center;">
        <span style="color:#9C9E9E; font-size:18px;">クルムフィット {count['クルムフィット']} 施設　</span>
        <span style="color:#FF8CE8; font-size:18px; margin-left: 10px;">ベビーバンド {count['ベビーバンド']} 施設　</span>
        <span style="color:#F49630; font-size:18px; margin-left: 10px;">スターバンド {count['スターバンド']} 施設</span>
        <span style="color:red; font-size:18px; margin-left: 10px;">（調整 {count['スターバンド調整']} 施設）　</span>
        <span style="color:#FFC88D; font-size:18px; margin-left: 10px;">リモベビー {count['リモベビー']} 施設　</span>
        <span style="color:lightblue; font-size:18px; margin-left: 10px;">プロモメット {count['プロモメット']} 施設</span>
        <span style="color:blue; font-size:18px; margin-left: 10px;">HANI Helmet {count['HANI Helmet']} 施設</span>
        <span style="color:navy; font-size:18px; margin-left: 10px;">GIO Helmet {count['GIO Helmet']} 施設</span>
    </div>
    """,
    unsafe_allow_html=True
)

# 地図を表示
st_folium(m, use_container_width=True, height=1000, returned_objects=[])

st.markdown('<div style="text-align: right; color:black; font-size:18px;">地図右上のレイヤーを選択すると、ヘルメットの種類を絞ることができます</div>', unsafe_allow_html=True)

st.markdown('<div style="color:black; font-size:18px;">情報ソース</div>', unsafe_allow_html=True)
st.markdown('<a href="https://babyhelmet.jp/clinics/">クルムフィット</a>', unsafe_allow_html=True)
st.markdown('<a href="https://www.babyband.jp/clinics">ベビーバンド</a>', unsafe_allow_html=True)
st.markdown('<a href="https://www.ahsjapan.com/facility/medical-institution/">スターバンド</a>', unsafe_allow_html=True)
st.markdown('<a href="https://remobaby.com/institution">リモベビー</a>', unsafe_allow_html=True)
st.markdown('<a href="https://yamaguchi-hosougu.co.jp/promomet/">プロモメット</a>', unsafe_allow_html=True)
st.markdown('<a href="https://hanihelmet.com/en/?page_id=2031">HANI Helmet</a>', unsafe_allow_html=True)
st.markdown('<a href="http://giohelmet.com/">GIO Helmet</a>', unsafe_allow_html=True)


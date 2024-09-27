import streamlit as st
import folium
from streamlit_folium import st_folium

import pandas as pd
import requests

url = st.secrets["API_URL"]

response = requests.get(url)
data = response.json()

helmets = ['ベビーバンド', 'スターバンド', 'クルム', 'リモベビー', 'プロモメット']

df = pd.DataFrame()

for helmet in helmets:
  df_temp = pd.DataFrame(data[helmet])
  #print(df_temp.columns)
  if '削除日' in df_temp.columns:
    df_temp = df_temp[df_temp['削除日']== '']
  df_temp = df_temp[df_temp['医療機関名'] != '']
  df_temp = df_temp[['医療機関名', '住所', '緯度', '経度']]
  df_temp = df_temp.dropna()
  df_temp['ヘルメット'] = helmet
  df = pd.concat([df, df_temp])

# 地図の初期設定（初期表示位置を東京に設定）
if "map" not in st.session_state:
    # 初回のみ地図を作成し、セッションに保存
    m = folium.Map(location=[35.6895, 139.6917], zoom_start=6)

    # 色を指定する関数
    def get_marker_color(name):
        if name == 'クルム':
            return 'lightgray'
        elif name == 'ベビーバンド':
            return 'pink'
        elif name == 'スターバンド':
            return 'orange'
        elif name == 'リモベビー':
            return 'beige'
        else:  # プロモメット
            return 'lightblue'

    # レイヤーコントロールを使用して各都市のマーカーを別々のレイヤーに追加
    fg_q = folium.FeatureGroup(name='クルム').add_to(m)
    fg_bb = folium.FeatureGroup(name='ベビーバンド').add_to(m)
    fg_sb = folium.FeatureGroup(name='スターバンド').add_to(m)
    fg_rb = folium.FeatureGroup(name='リモベビー').add_to(m)
    fg_pm = folium.FeatureGroup(name='プロモメット').add_to(m)

    # データフレームの各行を地図にプロット
    for index, row in df.iterrows():
        popup_content = f"""
        <b>医療機関名:</b> {row['医療機関名']}<br>
        <b>ヘルメット:</b> {row['ヘルメット']}<br>
        """
        popup = folium.Popup(popup_content, max_width=2000)

        marker = folium.Marker(
            location=[row['緯度'], row['経度']],
            popup=popup,
            icon=folium.Icon(color=get_marker_color(row['ヘルメット']))
        )

        if row['ヘルメット'] == 'クルム':
            marker.add_to(fg_q)
        elif row['ヘルメット'] == 'ベビーバンド':
            marker.add_to(fg_bb)
        elif row['ヘルメット'] == 'スターバンド':
            marker.add_to(fg_sb)
        elif row['ヘルメット'] == 'リモベビー':
            marker.add_to(fg_rb)
        elif row['ヘルメット'] == 'プロモメット':
            marker.add_to(fg_pm)

    # カスタムHTMLを使用して凡例を追加
    legend_html = '''
    <div style="position: fixed;
                bottom: 50px; left: 375px; width: 200px; height: 180px;
                border:2px solid grey; z-index:9999; font-size:14px;
                background-color:white; opacity: 0.8;
                padding: 10px;">
    &emsp;<b>ヘルメットの種類</b><br>
    &emsp;<i class="fa fa-map-marker fa-2x" style="color:#9C9E9E"></i>&emsp;クルム<br>
    &emsp;<i class="fa fa-map-marker fa-2x" style="color:#FF8CE8"></i>&emsp;ベビーバンド<br>
    &emsp;<i class="fa fa-map-marker fa-2x" style="color:#F49630"></i>&emsp;スターバンド<br>
    &emsp;<i class="fa fa-map-marker fa-2x" style="color:#FFC88D"></i>&emsp;リモベビー<br>
    &emsp;<i class="fa fa-map-marker fa-2x" style="color:lightblue"></i>&emsp;プロモメット<br>
    </div>
    '''

    m.get_root().html.add_child(folium.Element(legend_html))

    # レイヤーコントロールを地図に追加
    folium.LayerControl().add_to(m)

    # セッションステートにマップを保存
    st.session_state.map = m

st.write('ヘルメットの種類ごとに色分けした医療機関の地図')
st_folium(st.session_state.map, width=725)



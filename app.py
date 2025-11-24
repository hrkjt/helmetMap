import streamlit as st
import folium
from streamlit_folium import st_folium

import time
import io
import imageio.v2 as imageio  # requirements.txt に imageio を追加しておいてください

import pandas as pd
import requests

import altair as alt
import numpy as np

import datetime


st.set_page_config(
    page_title="使用ヘルメット別の医療機関等の地図",
    page_icon="👶",
    layout="wide"
)

@st.cache_data
def fetch_data(url):
    response = requests.get(url)
    print("Response status code:", response.status_code)
    print("Response text:", response.text)
    return response.json()
    
url = st.secrets["API_URL"]

response = requests.get(url)
data = fetch_data(url)  # キャッシュされたデータを使用

helmets = ['ベビーバンド', 'スターバンド', 'スターバンド調整', 'クルムフィット', 'リモベビー', 'プロモメット', 'HANI Helmet', 'GIO Helmet', 'INNOBAND']

df = pd.DataFrame()

count = {}

for helmet in helmets:
  print(helmet)
  df_temp = pd.DataFrame(data[helmet])
  print(df_temp.columns)
  if '削除日' in df_temp.columns:
    df_temp = df_temp[df_temp['削除日']== '']
  df_temp = df_temp[df_temp['医療機関名'] != '']
  # df_temp = df_temp[['医療機関名', '住所', '緯度', '経度', 'URL']]
  cols = ['医療機関名', '住所', '緯度', '経度', 'URL']
  if '年-月' in df_temp.columns:
    cols.append('年-月')

  df_temp = df_temp[cols]
    
  df_temp = df_temp.dropna()
  count[helmet] = str(len(df_temp))
  df_temp['ヘルメット'] = helmet
  df = pd.concat([df, df_temp])

#st.write('ヘルメットの種類ごとに色分けされた医療機関の地図')
# タイトルの中央揃え
st.markdown('<div style="text-align: center; color:black; font-size:24px; font-weight: bold;">ヘルメットの種類ごとに色分けされた医療機関等の地図</div>', unsafe_allow_html=True)

# 同じ行に表示して中央揃え
st.markdown(
    f"""
    <div style="display: flex; justify-content: center; align-items: center;">
        <span style="color:black; font-size:18px;">日本：</span>
        <span style="color:#9C9E9E; font-size:18px;">クルムフィット {count['クルムフィット']} 施設　</span>
        <span style="color:#FF8CE8; font-size:18px; margin-left: 10px;">ベビーバンド {count['ベビーバンド']} 施設　</span>
        <span style="color:#F49630; font-size:18px; margin-left: 10px;">スターバンド {count['スターバンド']} 施設</span>
        <span style="color:red; font-size:18px; margin-left: 10px;">（調整 {count['スターバンド調整']} 施設）　</span>
        <span style="color:#FFC88D; font-size:18px; margin-left: 10px;">リモベビー {count['リモベビー']} 施設　</span>
        <span style="color:lightblue; font-size:18px; margin-left: 10px;">プロモメット {count['プロモメット']} 施設</span>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    f"""
    <div style="display: flex; justify-content: center; align-items: center;">
        <span style="color:black; font-size:18px;">韓国：</span>
        <span style="color:blue; font-size:18px; margin-left: 10px;">HANI Helmet {count['HANI Helmet']} 施設</span>
        <span style="color:darkblue; font-size:18px; margin-left: 10px;">GIO Helmet {count['GIO Helmet']} 施設</span>
        <span style="color:darkpurple; font-size:18px; margin-left: 10px;">INNOBAND {count['INNOBAND']} 施設</span>
    </div>
    """,
    unsafe_allow_html=True
)

# 「年-月」列がある場合は datetime に変換してスライダーで絞り込み
if '年-月' in df.columns:
    # 文字列 "YYYY-MM" → Timestamp（その月の1日）
    df['年月'] = pd.to_datetime(df['年-月'], format='%Y-%m', errors='coerce')

    # 下限は 2024-06-01、上限は「現在の月初」かデータ最大のどちらか小さい方
    default_start = pd.Timestamp('2024-06-01')

    import datetime
    today = datetime.date.today()
    current_month = pd.Timestamp(today.replace(day=1))

    data_min = df['年月'].min()
    data_max = df['年月'].max()

    # スライダーの範囲（pandas.Timestamp のまま一旦計算）
    slider_min_ts = max(default_start, data_min) if pd.notna(data_min) else default_start
    slider_max_ts = min(current_month, data_max) if pd.notna(data_max) else current_month

    # ★ Streamlit に渡すときは Python の datetime に変換する
    slider_min = slider_min_ts.to_pydatetime()
    slider_max = slider_max_ts.to_pydatetime()

    # 📌 ここがエラーになっていたので、min/max/value を全部 datetime に統一
    start_dt, end_dt = st.slider(
        "表示する年月（年-月）",
        min_value=slider_min,
        max_value=slider_max,
        value=(slider_min, slider_max),
        format="YYYY-MM"
    )

    # フィルタ用に pandas 側の Timestamp に戻してもいいし、そのまま比較でもOK
    start_month = pd.Timestamp(start_dt)
    end_month = pd.Timestamp(end_dt)

    # ★ 地図用の df を年月範囲でフィルタ
    if slider_min_ts == default_start:
        df_map = df[df['年月'] <= end_month].copy()
    else:
        df_map = df[(df['年月'] >= start_month) & (df['年月'] <= end_month)].copy()

else:
    # 「年-月」が無い場合は全件表示
    df_map = df.copy()

# 統計表示用の件数も、フィルタ後の df_map で数え直す
count = {}
for helmet in helmets:
    count[helmet] = str(len(df_map[df_map['ヘルメット'] == helmet]))

# ==========================================================
# # 色を指定する関数
# #[‘red’, ‘blue’, ‘green’, ‘purple’, ‘orange’, ‘darkred’, ’lightred’, ‘beige’, ‘darkblue’, ‘darkgreen’, ‘cadetblue’, ‘darkpurple’, ‘white’, ‘pink’, ‘lightblue’, ‘lightgreen’, ‘gray’, ‘black’, ‘lightgray’]
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
    elif name == 'GIO Helmet':
        return 'darkblue'
    else:  #INNOBAND
        return 'darkpurple'

# # 地図の初期設定（初期表示位置を東京に設定）
# m = folium.Map(location=[35.6895, 139.6917], zoom_start=6)

# # レイヤーコントロールを使用して各都市のマーカーを別々のレイヤーに追加
# fg_q = folium.FeatureGroup(name='クルムフィット').add_to(m)
# fg_bb = folium.FeatureGroup(name='ベビーバンド').add_to(m)
# fg_sb = folium.FeatureGroup(name='スターバンド').add_to(m)
# fg_sba = folium.FeatureGroup(name='スターバンド調整').add_to(m)
# fg_rb = folium.FeatureGroup(name='リモベビー').add_to(m)
# fg_pm = folium.FeatureGroup(name='プロモメット').add_to(m)
# fg_hh = folium.FeatureGroup(name='HANI Helmet').add_to(m)
# fg_gh = folium.FeatureGroup(name='GIO Helmet').add_to(m)
# fg_ib = folium.FeatureGroup(name='INNOBAND').add_to(m)

# if df_map.empty:
#     st.warning("選択された年月の範囲に該当する施設がありません。")

# # データフレームの各行を地図にプロット
# # for index, row in df.iterrows():
# for index, row in df_map.iterrows():    
#     #<a href="https://www.ncchd.go.jp/" target="_blank" rel="noreferrer noopener">国立研究開発法人 国立成育医療研究ｾﾝﾀｰ</a>
#     if row['URL'] != '':
#         if row['ヘルメット'] in ['スターバンド調整', 'HANI Helmet', 'GIO Helmet', 'INNOBAND']:
#           popup_content = f"""
#             <b>施設名:</b> <a href={row['URL']} target="_blank">{row['医療機関名']}</a><br>
#             {row['ヘルメット']}<br>
#             {row['住所']}<br>
#             """
#         else:
#           popup_content = f"""
#             <b>医療機関名:</b> <a href={row['URL']} target="_blank">{row['医療機関名']}</a><br>
#             <b>ヘルメット:</b> {row['ヘルメット']}<br>
#             {row['住所']}<br>
#             """
#     else:
#         if row['ヘルメット'] in ['スターバンド調整', 'HANI Helmet', 'GIO Helmet', 'INNOBAND']:
#           popup_content = f"""
#             <b>施設名:</b> {row['医療機関名']}<br>
#             {row['ヘルメット']}<br>
#             {row['住所']}<br>
#             """
#         else:
#           popup_content = f"""
#             <b>医療機関名:</b> {row['医療機関名']}<br>
#             <b>ヘルメット:</b> {row['ヘルメット']}<br>
#             {row['住所']}<br>
#             """        
            
#     #if row['URL'] != '':
#         #popup_content += f"{row['URL']}<br>"

#     #iframe = folium.IFrame(popup_content, width=200, height=100)
#     #popup = folium.Popup(iframe, max_width=2000)
#     popup = folium.Popup(popup_content, max_width=2000)  # max_width=200

#     marker = folium.Marker(
#         location=[row['緯度'], row['経度']],
#         popup=popup,
#         icon=folium.Icon(color=get_marker_color(row['ヘルメット']))
#     )

#     if row['ヘルメット'] == 'クルムフィット':
#       marker.add_to(fg_q)
#     if row['ヘルメット'] == 'ベビーバンド':
#       marker.add_to(fg_bb)
#     if row['ヘルメット'] == 'スターバンド':
#       marker.add_to(fg_sb)
#     if row['ヘルメット'] == 'スターバンド調整':
#       marker.add_to(fg_sba)
#     if row['ヘルメット'] == 'リモベビー':
#       marker.add_to(fg_rb)
#     if row['ヘルメット'] == 'プロモメット':
#       marker.add_to(fg_pm)
#     if row['ヘルメット'] == 'HANI Helmet':
#       marker.add_to(fg_hh)
#     if row['ヘルメット'] == 'GIO Helmet':
#       marker.add_to(fg_gh)
#     if row['ヘルメット'] == 'INNOBAND':
#       marker.add_to(fg_ib)

# # レイヤーコントロールを地図に追加
# folium.LayerControl().add_to(m)

# # 地図を表示
# st_folium(m, use_container_width=True, height=1000, returned_objects=[])

# st.markdown('<div style="text-align: right; color:black; font-size:18px;">地図右上のレイヤーを選択すると、ヘルメットの種類を絞ることができます</div>', unsafe_allow_html=True)

# ================== 地図描画関数 ==================
def build_map(df_map: pd.DataFrame) -> folium.Map:
    # 地図の初期設定（初期表示位置を東京に設定）
    m = folium.Map(location=[35.6895, 139.6917], zoom_start=6)

    # レイヤーコントロールを使用して各都市のマーカーを別々のレイヤーに追加
    fg_q = folium.FeatureGroup(name='クルムフィット').add_to(m)
    fg_bb = folium.FeatureGroup(name='ベビーバンド').add_to(m)
    fg_sb = folium.FeatureGroup(name='スターバンド').add_to(m)
    fg_sba = folium.FeatureGroup(name='スターバンド調整').add_to(m)
    fg_rb = folium.FeatureGroup(name='リモベビー').add_to(m)
    fg_pm = folium.FeatureGroup(name='プロモメット').add_to(m)
    fg_hh = folium.FeatureGroup(name='HANI Helmet').add_to(m)
    fg_gh = folium.FeatureGroup(name='GIO Helmet').add_to(m)
    fg_ib = folium.FeatureGroup(name='INNOBAND').add_to(m)

    # データフレームの各行を地図にプロット
    for _, row in df_map.iterrows():
        if row['URL'] != '':
            if row['ヘルメット'] in ['スターバンド調整', 'HANI Helmet', 'GIO Helmet', 'INNOBAND']:
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
            if row['ヘルメット'] in ['スターバンド調整', 'HANI Helmet', 'GIO Helmet', 'INNOBAND']:
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

        popup = folium.Popup(popup_content, max_width=2000)

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
        if row['ヘルメット'] == 'INNOBAND':
            marker.add_to(fg_ib)

    # レイヤーコントロールを地図に追加
    folium.LayerControl().add_to(m)

    return m


# ============== 通常表示用の地図 ==============
if df_map.empty:
    st.warning("選択された年月の範囲に該当する施設がありません。")
else:
    # ここで placeholder を用意しておく
    map_placeholder = st.empty()

    # 現在のスライダー設定での静止画マップ
    m_initial = build_map(df_map)
    with map_placeholder:
        st_folium(
            m_initial,
            use_container_width=True,
            height=1000,
            returned_objects=[],
            key="helmet_map_initial"  # ★ 固定の key
        )

st.markdown(
    '<div style="text-align: right; color:black; font-size:18px;">'
    '地図右上のレイヤーを選択すると、ヘルメットの種類を絞ることができます'
    '</div>',
    unsafe_allow_html=True
)


# ================== アニメーション・GIF作成 ==================
# スライダーから得た start_month, end_month, slider_max_ts, slider_min_ts を前のブロックで定義済みと仮定

if '年-月' in df.columns and not df_map.empty:

    st.markdown("### 📽️ end_dt を1ヶ月ずつ増やしたアニメーション")

    col1, col2 = st.columns(2)
    with col1:
        play_anim = st.button("▶︎ 画面で再生")
    with col2:
        make_gif = st.button("💾 GIF を作成")

    # ユーザーが現在選んでいる start_dt に合わせて、end_dt を月ごとに右へ動かすイメージ
    start_ts = pd.Timestamp(start_dt)
    # アニメーションは現在の end_dt 〜 データの最大月 まででも、default_start〜最大まででもOK
    # ここでは「start_dt〜slider_max_ts」までをコマにします
    anim_months = pd.date_range(start=start_ts, end=slider_max_ts, freq='MS')

    # 「default_start からの累積表示かどうか」のフラグ
    use_cumulative_from_default = (slider_min_ts == pd.Timestamp('2024-06-01'))

    def filter_df_for_range(end_ts: pd.Timestamp) -> pd.DataFrame:
        if use_cumulative_from_default:
            # 2024-06 からの累積
            return df[df['年月'] <= end_ts].copy()
        else:
            # スライダー左端 start_ts からの累積
            return df[(df['年月'] >= start_ts) & (df['年月'] <= end_ts)].copy()

    # --- 画面でのアニメーション再生 ---
    if play_anim:
        for i, end_ts in enumerate(anim_months):
            df_frame = filter_df_for_range(end_ts)

            if df_frame.empty:
                continue

            # 画面右上に「何年何月まで表示中か」を出す
            st.markdown(
                f"<div style='text-align:right; font-size:16px;'>"
                f"{end_ts.strftime('%Y-%m')} までの施設を表示中（{i+1}/{len(anim_months)}）"
                f"</div>",
                unsafe_allow_html=True
            )

            m_frame = build_map(df_frame)
            with map_placeholder:
                st_folium(
                    m_frame,
                    use_container_width=True,
                    height=1000,
                    returned_objects=[],
                    key=f"helmet_map_anim_{i}"  # ← i を付けてユニークに
                )

            time.sleep(0.7)  # コマ送りの間隔（秒）

    # --- GIF 作成＆ダウンロード ---
    if make_gif:
        frames = []

        for end_ts in anim_months:
            df_frame = filter_df_for_range(end_ts)
            if df_frame.empty:
                continue

            m_frame = build_map(df_frame)

            # folium Map → PNG バイト列
            png_bytes = m_frame._to_png(5)  # delay=5秒ぐらい（環境により調整）
            img = imageio.imread(io.BytesIO(png_bytes))
            frames.append(img)

        if frames:
            gif_bytes = io.BytesIO()
            imageio.mimsave(gif_bytes, frames, format="GIF", duration=0.7)
            gif_bytes.seek(0)

            st.download_button(
                "GIF をダウンロード",
                data=gif_bytes,
                file_name="helmet_map_animation.gif",
                mime="image/gif"
            )
        else:
            st.warning("GIF 用のフレームを作成できませんでした。")


# ===== ここから折れ線グラフ用の処理 =====

target_helmets = ['ベビーバンド', 'スターバンド', 'クルムフィット', 'リモベビー']

# 「年-月」列があるかチェック
if '年-月' in df.columns:
    df_chart = df[df['ヘルメット'].isin(target_helmets)].copy()
    
    # 念のためダブりを削る（同じ医療機関+ヘルメットが複数行あっても1施設と数える想定）
    df_chart = df_chart.drop_duplicates(subset=['医療機関名', 'ヘルメット'])
    
    # 年月を Timestamp に変換
    df_chart['年月'] = pd.to_datetime(df_chart['年-月'], format='%Y-%m', errors='coerce')
    df_chart = df_chart.dropna(subset=['年月'])
    
    # 2024-06以降に限定
    # start_month = pd.Timestamp('2024-06-01')
    # df_chart = df_chart[df_chart['年月'] >= start_month]
    
    if not df_chart.empty:
        # 月初日ベースの連続した月のリストを作る
        # end_month = df_chart['年月'].max()
        # month_range = pd.date_range(start=start_month, end=end_month, freq='MS')  # MS = month start
        
        # 各ヘルメット×年月ごとの「新規施設数」（その月に新しく出てきた施設数）
        monthly_new = (
            df_chart
            .groupby(['ヘルメット', '年月'])
            .size()
            .rename('新規施設数')
            .reset_index()
        )

        # 月の全範囲（最初〜最後）
        overall_start = monthly_new['年月'].min()
        overall_end   = monthly_new['年月'].max()
        month_range = pd.date_range(start=overall_start, end=overall_end, freq='MS')
        
        # 全てのヘルメット×全ての月を埋めたテーブルにし、欠損は0
        idx = pd.MultiIndex.from_product(
            [target_helmets, month_range],
            names=['ヘルメット', '年月']
        )
        monthly_new_full = (
            monthly_new
            .set_index(['ヘルメット', '年月'])
            .reindex(idx, fill_value=0)
            .reset_index()
        )
        
        # 各ヘルメットごとの累積施設数を計算
        monthly_new_full['累積施設数'] = (
            monthly_new_full
            .groupby('ヘルメット')['新規施設数']
            .cumsum()
        )
        
        # 合計ライン（4ヘルメット合計の累積施設数）を作成
        total_by_month = (
            monthly_new_full
            .groupby('年月')['累積施設数']
            .sum()
            .rename('累積施設数')
            .reset_index()
        )
        total_by_month['ヘルメット'] = '合計'
        
        # プロット用に結合
        df_plot = pd.concat(
            [
                monthly_new_full[['ヘルメット', '年月', '累積施設数']],
                total_by_month[['ヘルメット', '年月', '累積施設数']]
            ],
            ignore_index=True
        )
        
        # 年月表示用に文字列（YYYY-MM）を作っておくとツールチップが見やすい
        df_plot['年月_str'] = df_plot['年月'].dt.strftime('%Y-%m')
        
        # Altair で折れ線グラフを作成
        chart = (
            alt.Chart(df_plot)
            .mark_line(point=True)
            .encode(
                x=alt.X('年月:T', title='年月'),
                y=alt.Y('累積施設数:Q', title='累積の医療機関数'),
                # color=alt.Color('ヘルメット:N', title='ヘルメット'),
                color=alt.Color(
                    'ヘルメット:N',
                    title='ヘルメット',
                    # レジェンドと色の順番を固定
                    scale=alt.Scale(
                        domain=['スターバンド', 'リモベビー', 'クルムフィット', 'ベビーバンド'],
                        range=['#FFA500', '#F5F5DC', '#D3D3D3', '#FFC0CB']  # お好みで
                    )
                ),
                tooltip=[
                    alt.Tooltip('ヘルメット:N', title='ヘルメット'),
                    alt.Tooltip('年月_str:N', title='年月'),
                    alt.Tooltip('累積施設数:Q', title='累積施設数')
                ]
            )
            .properties(
                width=800,
                height=400,
                title='ヘルメット別 医療機関数の推移（2024-06以降, 累積）'
            )
        )
        
        # st.markdown(
        #     '<div style="text-align: center; color:black; font-size:22px; font-weight: bold; margin-top: 30px;">'
        #     'ベビーバンド / スターバンド / クルムフィット / リモベビー の医療機関数の推移'
        #     '</div>',
        #     unsafe_allow_html=True
        # )
        # st.altair_chart(chart, use_container_width=True)
    else:
        st.warning('2024-06以降の「年-月」データがありませんでした。')
else:
    st.warning('APIレスポンスに「年-月」カラムが含まれていません。')
# ===== 折れ線グラフ用の処理ここまで =====

# ===== スタックエリアチャート（合計の内訳を色分け） =====
# ★ ここで初めて「表示用」に 2024-06 以降を切り出す
start_month = pd.Timestamp('2024-06-01')
# df_area = monthly_new_full.copy()
df_area = monthly_new_full[monthly_new_full['年月'] >= start_month].copy()
df_area['年月_str'] = df_area['年月'].dt.strftime('%Y-%m')


# スタック順を数値で持たせる
order_map = {
    'スターバンド': 0,   # 一番下
    'リモベビー': 2,
    'クルムフィット': 1,
    'ベビーバンド': 3  # 一番上
}
df_area['helmet_order'] = df_area['ヘルメット'].map(order_map)

# ★ 境界線用の「下からの累積」を計算
df_border = (
    df_area
    .sort_values(['年月', 'helmet_order'])
    .groupby('年月', as_index=False)
    .apply(lambda g: g.assign(累積境界=g['累積施設数'].cumsum()))
    .reset_index(drop=True)
)

# area_chart = (
#     alt.Chart(df_area)
#     .mark_area()
#     .encode(
#         x=alt.X('年月:T', title='年月'),
#         y=alt.Y(
#             '累積施設数:Q',
#             title='累積の医療機関数',
#             stack='zero'
#         ),
#         color=alt.Color(
#             'ヘルメット:N',
#             title='ヘルメット',
#             # レジェンドと色の順番を固定
#             scale=alt.Scale(
#                 domain=['スターバンド', 'リモベビー', 'クルムフィット', 'ベビーバンド'],
#                 range=['#FFA500', '#F5F5DC', '#D3D3D3', '#FFC0CB']  # お好みで
#             )
#         ),
#         # ★ スタック順はこの数値で制御
#         order=alt.Order('helmet_order:Q', sort='ascending'),
#         tooltip=[
#             alt.Tooltip('ヘルメット:N', title='ヘルメット'),
#             alt.Tooltip('年月_str:N', title='年月'),
#             alt.Tooltip('累積施設数:Q', title='累積施設数')
#         ]
#     )
#     .properties(
#         width=800,
#         height=400,
#         title='ヘルメット別 累積医療機関数'  #（内訳を色分け・指定順でスタック）
#     )
# )

# 塗りつぶし
area_layer = (
    alt.Chart(df_area)
    .mark_area()
    .encode(
        x=alt.X('年月:T', title='年月'),
        y=alt.Y('累積施設数:Q', title='累積の医療機関数', stack='zero'),
        color=alt.Color(
            'ヘルメット:N',
            title='ヘルメット',
            scale=alt.Scale(
                domain=['スターバンド', 'リモベビー', 'クルムフィット', 'ベビーバンド'],
                range=['#F49630', '#FFF5C7', '#D3D3D3', '#FFC0CB']  # お好みで
            )
        ),
        order=alt.Order('helmet_order:Q', sort='ascending'),
        tooltip=[
            alt.Tooltip('ヘルメット:N', title='ヘルメット'),
            alt.Tooltip('年月_str:N', title='年月'),
            alt.Tooltip('累積施設数:Q', title='累積施設数')
        ]
    )
)

# ★ 境界線（下からの累積を線でなぞる）
border_layer = (
    alt.Chart(df_border)
    .mark_line(color='black', strokeWidth=1.2)
    .encode(
        x='年月:T',
        y='累積境界:Q',
        detail='ヘルメット:N',             # ヘルメットごとに別ライン
        order=alt.Order('helmet_order:Q', sort='ascending')
    )
)

final_chart = (
    (area_layer + border_layer)
    .properties(
        width=800,
        height=400,
        title='ヘルメット別 累積医療機関数'  #（内訳 + 境界黒線）
    )
)

st.markdown(
    '<div style="text-align: center; color:black; font-size:22px; font-weight: bold; margin-top: 30px;">'
    'ベビーバンド / スターバンド / クルムフィット / リモベビー の累積医療機関数'  #（内訳付き）
    '</div>',
    unsafe_allow_html=True
)
# st.altair_chart(area_chart, use_container_width=True)
st.altair_chart(final_chart, use_container_width=True)




st.markdown('<div style="color:black; font-size:18px;">情報ソース</div>', unsafe_allow_html=True)
st.markdown('<a href="https://babyhelmet.jp/clinics/">クルムフィット</a>', unsafe_allow_html=True)
st.markdown('<a href="https://www.babyband.jp/clinics">ベビーバンド</a>', unsafe_allow_html=True)
st.markdown('<a href="https://www.ahsjapan.com/facility/medical-institution/">スターバンド</a>', unsafe_allow_html=True)
st.markdown('<a href="https://remobaby.com/institution">リモベビー</a>', unsafe_allow_html=True)
st.markdown('<a href="https://yamaguchi-hosougu.co.jp/promomet/">プロモメット</a>', unsafe_allow_html=True)
st.markdown('<a href="https://hanihelmet.com/en/?page_id=2031">HANI Helmet</a>', unsafe_allow_html=True)
st.markdown('<a href="http://giohelmet.com/">GIO Helmet</a>', unsafe_allow_html=True)
st.markdown('<a href="https://www.innoband.co.kr/">INNOBAND</a>', unsafe_allow_html=True)


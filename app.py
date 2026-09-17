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


helmets = [
    'ベビーバンド',
    'スターバンド',
    'スターバンド調整',
    'クルムフィット',
    'リモベビー',
    'プロモメット',
    'ココバンド',
    'HANI Helmet',
    'GIO Helmet',
    'INNOBAND'
]

df = pd.DataFrame()

count = {}

for helmet in helmets:
    print(helmet)

    # API側にまだ該当ヘルメットのキーがなくてもエラーにならないようにする
    df_temp = pd.DataFrame(data.get(helmet, []))

    print(df_temp.columns)

    # データが空の場合
    if df_temp.empty:
        count[helmet] = '0'
        continue

    if '削除日' in df_temp.columns:
        df_temp = df_temp[df_temp['削除日'] == '']

    df_temp = df_temp[df_temp['医療機関名'] != '']

    cols = ['医療機関名', '住所', '緯度', '経度', 'URL']

    if '年-月' in df_temp.columns:
        cols.append('年-月')

    df_temp = df_temp[cols]

    df_temp = df_temp.dropna()

    count[helmet] = str(len(df_temp))

    df_temp['ヘルメット'] = helmet

    df = pd.concat([df, df_temp], ignore_index=True)


# タイトルの中央揃え
st.markdown(
    '<div style="text-align: center; color:black; font-size:24px; font-weight: bold;">'
    'ヘルメットの種類ごとに色分けされた医療機関等の地図'
    '</div>',
    unsafe_allow_html=True
)


# 日本
st.markdown(
    f"""<div style="display:flex; justify-content:center; align-items:center; flex-wrap:wrap;">
<span style="color:black; font-size:18px;">日本：</span>
<span style="color:#9C9E9E; font-size:18px;">クルムフィット {count['クルムフィット']} 施設　</span>
<span style="color:#FF8CE8; font-size:18px; margin-left:10px;">ベビーバンド {count['ベビーバンド']} 施設　</span>
<span style="color:#F49630; font-size:18px; margin-left:10px;">スターバンド {count['スターバンド']} 施設</span>
<span style="color:red; font-size:18px; margin-left:10px;">（調整 {count['スターバンド調整']} 施設）　</span>
<span style="color:#FFC88D; font-size:18px; margin-left:10px;">リモベビー {count['リモベビー']} 施設　</span>
<span style="color:lightblue; font-size:18px; margin-left:10px;">プロモメット {count['プロモメット']} 施設　</span>
<span style="color:#2E8B57; font-size:18px; margin-left:10px;">ココバンド {count['ココバンド']} 施設</span>
</div>""",
    unsafe_allow_html=True
)


# 韓国
st.markdown(
    f"""<div style="display:flex; justify-content:center; align-items:center; flex-wrap:wrap;">
<span style="color:black; font-size:18px;">韓国：</span>
<span style="color:blue; font-size:18px; margin-left:10px;">HANI Helmet {count['HANI Helmet']} 施設</span>
<span style="color:darkblue; font-size:18px; margin-left:10px;">GIO Helmet {count['GIO Helmet']} 施設</span>
<span style="color:darkpurple; font-size:18px; margin-left:10px;">INNOBAND {count['INNOBAND']} 施設</span>
</div>""",
    unsafe_allow_html=True
)


# ==========================================================
# 「年-月」列がある場合は datetime に変換してスライダーで絞り込み
# ==========================================================

if '年-月' in df.columns:

    # 文字列 "YYYY-MM" → Timestamp（その月の1日）
    df['年月'] = pd.to_datetime(
        df['年-月'],
        format='%Y-%m',
        errors='coerce'
    )

    # 下限は 2024-06-01
    default_start = pd.Timestamp('2024-06-01')

    today = datetime.date.today()
    current_month = pd.Timestamp(today.replace(day=1))

    data_min = df['年月'].min()
    data_max = df['年月'].max()

    # スライダー範囲
    slider_min_ts = (
        max(default_start, data_min)
        if pd.notna(data_min)
        else default_start
    )

    slider_max_ts = (
        min(current_month, data_max)
        if pd.notna(data_max)
        else current_month
    )

    # Streamlit に渡すときは Python datetime に変換
    slider_min = slider_min_ts.to_pydatetime()
    slider_max = slider_max_ts.to_pydatetime()

    start_dt, end_dt = st.slider(
        "表示する年月（年-月）",
        min_value=slider_min,
        max_value=slider_max,
        value=(slider_min, slider_max),
        format="YYYY-MM"
    )

    start_month = pd.Timestamp(start_dt)
    end_month = pd.Timestamp(end_dt)

    # 地図用データを年月範囲でフィルタ
    if slider_min_ts == default_start:
        df_map = df[
            df['年月'] <= end_month
        ].copy()
    else:
        df_map = df[
            (df['年月'] >= start_month)
            & (df['年月'] <= end_month)
        ].copy()

else:
    df_map = df.copy()


# ==========================================================
# 統計表示用の件数をフィルタ後の df_map で再計算
# ==========================================================

count = {}

for helmet in helmets:
    count[helmet] = str(
        len(
            df_map[
                df_map['ヘルメット'] == helmet
            ]
        )
    )


# ==========================================================
# 色を指定する関数
#
# Foliumで利用できる主な色:
# red, blue, green, purple, orange, darkred,
# lightred, beige, darkblue, darkgreen,
# cadetblue, darkpurple, white, pink,
# lightblue, lightgreen, gray, black, lightgray
# ==========================================================

def get_marker_color(name):

    if name == 'クルムフィット':
        return 'lightgray'

    elif name == 'ベビーバンド':
        return 'pink'

    elif name == 'スターバンド':
        return 'orange'

    elif name == 'スターバンド調整':
        return 'red'

    elif name == 'リモベビー':
        return 'beige'

    elif name == 'プロモメット':
        return 'lightblue'

    elif name == 'ココバンド':
        return 'green'

    elif name == 'HANI Helmet':
        return 'blue'

    elif name == 'GIO Helmet':
        return 'darkblue'

    elif name == 'INNOBAND':
        return 'darkpurple'

    return 'gray'


# ==========================================================
# 地図描画関数
# ==========================================================

def build_map(df_map: pd.DataFrame) -> folium.Map:

    # 地図の初期設定（東京）
    m = folium.Map(
        location=[35.6895, 139.6917],
        zoom_start=5.3
    )

    # ------------------------------------------------------
    # 各ヘルメットのレイヤー
    # ------------------------------------------------------

    fg_q = folium.FeatureGroup(
        name='クルムフィット',
        show=True
    ).add_to(m)

    fg_bb = folium.FeatureGroup(
        name='ベビーバンド',
        show=True
    ).add_to(m)

    fg_sb = folium.FeatureGroup(
        name='スターバンド',
        show=True
    ).add_to(m)

    fg_sba = folium.FeatureGroup(
        name='スターバンド調整',
        show=True
    ).add_to(m)

    fg_rb = folium.FeatureGroup(
        name='リモベビー',
        show=True
    ).add_to(m)

    fg_pm = folium.FeatureGroup(
        name='プロモメット',
        show=True
    ).add_to(m)

    # ココバンド
    fg_cb = folium.FeatureGroup(
        name='ココバンド',
        show=True
    ).add_to(m)

    # 韓国製品は初期非表示
    fg_hh = folium.FeatureGroup(
        name='HANI Helmet',
        show=False
    ).add_to(m)

    fg_gh = folium.FeatureGroup(
        name='GIO Helmet',
        show=False
    ).add_to(m)

    fg_ib = folium.FeatureGroup(
        name='INNOBAND',
        show=False
    ).add_to(m)

    # ------------------------------------------------------
    # データフレームの各行を地図にプロット
    # ------------------------------------------------------

    for _, row in df_map.iterrows():

        special_facility_labels = [
            'スターバンド調整',
            'HANI Helmet',
            'GIO Helmet',
            'INNOBAND'
        ]

        if row['URL'] != '':

            if row['ヘルメット'] in special_facility_labels:

                popup_content = f"""
                    <b>施設名:</b>
                    <a href="{row['URL']}" target="_blank">
                        {row['医療機関名']}
                    </a>
                    <br>

                    {row['ヘルメット']}
                    <br>

                    {row['住所']}
                    <br>
                """

            else:

                popup_content = f"""
                    <b>医療機関名:</b>
                    <a href="{row['URL']}" target="_blank">
                        {row['医療機関名']}
                    </a>
                    <br>

                    <b>ヘルメット:</b>
                    {row['ヘルメット']}
                    <br>

                    {row['住所']}
                    <br>
                """

        else:

            if row['ヘルメット'] in special_facility_labels:

                popup_content = f"""
                    <b>施設名:</b>
                    {row['医療機関名']}
                    <br>

                    {row['ヘルメット']}
                    <br>

                    {row['住所']}
                    <br>
                """

            else:

                popup_content = f"""
                    <b>医療機関名:</b>
                    {row['医療機関名']}
                    <br>

                    <b>ヘルメット:</b>
                    {row['ヘルメット']}
                    <br>

                    {row['住所']}
                    <br>
                """

        popup = folium.Popup(
            popup_content,
            max_width=2000
        )

        marker = folium.Marker(
            location=[
                row['緯度'],
                row['経度']
            ],
            popup=popup,
            icon=folium.Icon(
                color=get_marker_color(
                    row['ヘルメット']
                )
            )
        )

        # --------------------------------------------------
        # 対応するレイヤーへ追加
        # --------------------------------------------------

        if row['ヘルメット'] == 'クルムフィット':
            marker.add_to(fg_q)

        elif row['ヘルメット'] == 'ベビーバンド':
            marker.add_to(fg_bb)

        elif row['ヘルメット'] == 'スターバンド':
            marker.add_to(fg_sb)

        elif row['ヘルメット'] == 'スターバンド調整':
            marker.add_to(fg_sba)

        elif row['ヘルメット'] == 'リモベビー':
            marker.add_to(fg_rb)

        elif row['ヘルメット'] == 'プロモメット':
            marker.add_to(fg_pm)

        elif row['ヘルメット'] == 'ココバンド':
            marker.add_to(fg_cb)

        elif row['ヘルメット'] == 'HANI Helmet':
            marker.add_to(fg_hh)

        elif row['ヘルメット'] == 'GIO Helmet':
            marker.add_to(fg_gh)

        elif row['ヘルメット'] == 'INNOBAND':
            marker.add_to(fg_ib)

    # レイヤーコントロール
    folium.LayerControl().add_to(m)

    return m


# ==========================================================
# 通常表示用の地図
# ==========================================================

if df_map.empty:

    st.warning(
        "選択された年月の範囲に該当する施設がありません。"
    )

else:

    map_placeholder = st.empty()

    m_initial = build_map(df_map)

    with map_placeholder:

        st_folium(
            m_initial,
            use_container_width=True,
            height=1000,
            returned_objects=[],
            key="helmet_map_initial"
        )


st.markdown(
    '<div style="text-align: right; color:black; font-size:18px;">'
    '地図右上のレイヤーを選択すると、'
    'ヘルメットの種類を絞ることができます'
    '</div>',
    unsafe_allow_html=True
)


# ==========================================================
# アニメーション
# ==========================================================

if '年-月' in df.columns and not df_map.empty:

    st.markdown(
        "### 📽️ end_dt を1ヶ月ずつ増やしたアニメーション"
    )

    play_anim = st.button(
        "▶︎ 画面で再生"
    )

    start_ts = pd.Timestamp(start_dt)

    anim_months = pd.date_range(
        start=start_ts,
        end=slider_max_ts,
        freq='MS'
    )

    use_cumulative_from_default = (
        slider_min_ts
        == pd.Timestamp('2024-06-01')
    )

    def filter_df_for_range(
        end_ts: pd.Timestamp
    ) -> pd.DataFrame:

        if use_cumulative_from_default:

            # 2024-06以前も含めて、
            # 指定月までの累積施設を表示
            return df[
                df['年月'] <= end_ts
            ].copy()

        else:

            # スライダー左端から指定月まで
            return df[
                (df['年月'] >= start_ts)
                & (df['年月'] <= end_ts)
            ].copy()

    # ------------------------------------------------------
    # 画面でアニメーション再生
    # ------------------------------------------------------

    if play_anim:

        for i, end_ts in enumerate(anim_months):

            df_frame = filter_df_for_range(
                end_ts
            )

            if df_frame.empty:
                continue

            st.markdown(
                f"""
                <div style="
                    text-align:right;
                    font-size:16px;
                ">
                    {end_ts.strftime('%Y-%m')}
                    までの施設を表示中
                    （{i + 1}/{len(anim_months)}）
                </div>
                """,
                unsafe_allow_html=True
            )

            m_frame = build_map(
                df_frame
            )

            with map_placeholder:

                st_folium(
                    m_frame,
                    use_container_width=True,
                    height=1000,
                    returned_objects=[],
                    key=f"helmet_map_anim_{i}"
                )

            time.sleep(0.7)


# ==========================================================
# 折れ線グラフ
# ==========================================================

target_helmets = [
    'ベビーバンド',
    'スターバンド',
    'クルムフィット',
    'リモベビー',
    'ココバンド'
]


if '年-月' in df.columns:

    df_chart = df[
        df['ヘルメット'].isin(
            target_helmets
        )
    ].copy()

    # 同じ医療機関＋ヘルメットは1施設としてカウント
    df_chart = df_chart.drop_duplicates(
        subset=[
            '医療機関名',
            'ヘルメット'
        ]
    )

    df_chart['年月'] = pd.to_datetime(
        df_chart['年-月'],
        format='%Y-%m',
        errors='coerce'
    )

    df_chart = df_chart.dropna(
        subset=['年月']
    )

    if not df_chart.empty:

        # --------------------------------------------------
        # 各ヘルメット×年月の新規施設数
        # --------------------------------------------------

        monthly_new = (
            df_chart
            .groupby(
                ['ヘルメット', '年月']
            )
            .size()
            .rename('新規施設数')
            .reset_index()
        )

        overall_start = (
            monthly_new['年月'].min()
        )

        overall_end = (
            monthly_new['年月'].max()
        )

        month_range = pd.date_range(
            start=overall_start,
            end=overall_end,
            freq='MS'
        )

        # --------------------------------------------------
        # 全ヘルメット × 全年月を生成
        # --------------------------------------------------

        idx = pd.MultiIndex.from_product(
            [
                target_helmets,
                month_range
            ],
            names=[
                'ヘルメット',
                '年月'
            ]
        )

        monthly_new_full = (
            monthly_new
            .set_index([
                'ヘルメット',
                '年月'
            ])
            .reindex(
                idx,
                fill_value=0
            )
            .reset_index()
        )

        # --------------------------------------------------
        # 累積施設数
        # --------------------------------------------------

        monthly_new_full[
            '累積施設数'
        ] = (
            monthly_new_full
            .groupby(
                'ヘルメット'
            )['新規施設数']
            .cumsum()
        )

        # --------------------------------------------------
        # 合計ライン
        # --------------------------------------------------

        total_by_month = (
            monthly_new_full
            .groupby(
                '年月'
            )['累積施設数']
            .sum()
            .rename(
                '累積施設数'
            )
            .reset_index()
        )

        total_by_month[
            'ヘルメット'
        ] = '合計'

        df_plot = pd.concat(
            [
                monthly_new_full[
                    [
                        'ヘルメット',
                        '年月',
                        '累積施設数'
                    ]
                ],
                total_by_month[
                    [
                        'ヘルメット',
                        '年月',
                        '累積施設数'
                    ]
                ]
            ],
            ignore_index=True
        )

        df_plot[
            '年月_str'
        ] = (
            df_plot[
                '年月'
            ]
            .dt
            .strftime('%Y-%m')
        )

        # --------------------------------------------------
        # 折れ線グラフ
        # --------------------------------------------------

        chart = (
            alt.Chart(
                df_plot
            )
            .mark_line(
                point=True
            )
            .encode(

                x=alt.X(
                    '年月:T',
                    title='年月'
                ),

                y=alt.Y(
                    '累積施設数:Q',
                    title='累積の医療機関数'
                ),

                color=alt.Color(
                    'ヘルメット:N',
                    title='ヘルメット',

                    scale=alt.Scale(
                        domain=[
                            'スターバンド',
                            'クルムフィット',
                            'リモベビー',
                            'ベビーバンド',
                            'ココバンド'
                        ],

                        range=[
                            '#F49630',
                            '#D3D3D3',
                            '#FFF5C7',
                            '#FFC0CB',
                            '#2E8B57'
                        ]
                    )
                ),

                tooltip=[
                    alt.Tooltip(
                        'ヘルメット:N',
                        title='ヘルメット'
                    ),

                    alt.Tooltip(
                        '年月_str:N',
                        title='年月'
                    ),

                    alt.Tooltip(
                        '累積施設数:Q',
                        title='累積施設数'
                    )
                ]
            )
            .properties(
                width=800,
                height=400,
                title=(
                    'ヘルメット別 '
                    '医療機関数の推移'
                )
            )
        )

    else:

        st.warning(
            '「年-月」データがありませんでした。'
        )

else:

    st.warning(
        'APIレスポンスに「年-月」カラムが含まれていません。'
    )


# ==========================================================
# スタックエリアチャート
# ==========================================================

if (
    '年-月' in df.columns
    and not df_chart.empty
):

    start_month = pd.Timestamp(
        '2024-06-01'
    )

    df_area = monthly_new_full[
        monthly_new_full['年月']
        >= start_month
    ].copy()

    df_area[
        '年月_str'
    ] = (
        df_area[
            '年月'
        ]
        .dt
        .strftime('%Y-%m')
    )

    # ------------------------------------------------------
    # スタック順
    # ------------------------------------------------------

    order_map = {
        'スターバンド': 0,
        'クルムフィット': 1,
        'リモベビー': 2,
        'ベビーバンド': 3,
        'ココバンド': 4
    }

    df_area[
        'helmet_order'
    ] = (
        df_area[
            'ヘルメット'
        ]
        .map(
            order_map
        )
    )

    # ------------------------------------------------------
    # 境界線用
    # ------------------------------------------------------

    df_border = (
        df_area
        .sort_values(
            [
                '年月',
                'helmet_order'
            ]
        )
        .groupby(
            '年月',
            as_index=False
        )
        .apply(
            lambda g: g.assign(
                累積境界=(
                    g[
                        '累積施設数'
                    ]
                    .cumsum()
                )
            )
        )
        .reset_index(
            drop=True
        )
    )

    # ------------------------------------------------------
    # 面グラフ
    # ------------------------------------------------------

    area_layer = (
        alt.Chart(
            df_area
        )
        .mark_area()
        .encode(

            x=alt.X(
                '年月:T',
                title='年月'
            ),

            y=alt.Y(
                '累積施設数:Q',
                title='累積の医療機関数',
                stack='zero'
            ),

            color=alt.Color(
                'ヘルメット:N',
                title='ヘルメット',

                scale=alt.Scale(

                    domain=[
                        'スターバンド',
                        'クルムフィット',
                        'リモベビー',
                        'ベビーバンド',
                        'ココバンド'
                    ],

                    range=[
                        '#F49630',
                        '#D3D3D3',
                        '#FFF5C7',
                        '#FFC0CB',
                        '#2E8B57'
                    ]
                )
            ),

            order=alt.Order(
                'helmet_order:Q',
                sort='ascending'
            ),

            tooltip=[
                alt.Tooltip(
                    'ヘルメット:N',
                    title='ヘルメット'
                ),

                alt.Tooltip(
                    '年月_str:N',
                    title='年月'
                ),

                alt.Tooltip(
                    '累積施設数:Q',
                    title='累積施設数'
                )
            ]
        )
    )

    # ------------------------------------------------------
    # 境界線
    # ------------------------------------------------------

    border_layer = (
        alt.Chart(
            df_border
        )
        .mark_line(
            color='black',
            strokeWidth=1.2
        )
        .encode(

            x='年月:T',

            y='累積境界:Q',

            detail='ヘルメット:N',

            order=alt.Order(
                'helmet_order:Q',
                sort='ascending'
            )
        )
    )

    # ------------------------------------------------------
    # 合成
    # ------------------------------------------------------

    final_chart = (
        (
            area_layer
            + border_layer
        )
        .properties(
            width=800,
            height=400,
            title=(
                'ヘルメット別 '
                '累積医療機関数'
            )
        )
    )

    st.markdown(
        """
        <div style="
            text-align: center;
            color:black;
            font-size:22px;
            font-weight: bold;
            margin-top: 30px;
        ">
        ベビーバンド /
        スターバンド /
        クルムフィット /
        リモベビー /
        ココバンド
        の累積医療機関数
        </div>
        """,
        unsafe_allow_html=True
    )

    st.altair_chart(
        final_chart,
        use_container_width=True
    )


# ==========================================================
# 情報ソース
# ==========================================================

st.markdown(
    '<div style="color:black; font-size:18px;">情報ソース</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<a href="https://babyhelmet.jp/clinics/" target="_blank">'
    'クルムフィット'
    '</a>',
    unsafe_allow_html=True
)

st.markdown(
    '<a href="https://www.babyband.jp/clinics" target="_blank">'
    'ベビーバンド'
    '</a>',
    unsafe_allow_html=True
)

st.markdown(
    '<a href="https://www.ahsjapan.com/facility/medical-institution/" target="_blank">'
    'スターバンド'
    '</a>',
    unsafe_allow_html=True
)

st.markdown(
    '<a href="https://remobaby.com/institution" target="_blank">'
    'リモベビー'
    '</a>',
    unsafe_allow_html=True
)

st.markdown(
    '<a href="https://yamaguchi-hosougu.co.jp/promomet/" target="_blank">'
    'プロモメット'
    '</a>',
    unsafe_allow_html=True
)

st.markdown(
    '<a href="https://coco-band.com/campaign-sale/" target="_blank">'
    'ココバンド'
    '</a>',
    unsafe_allow_html=True
)

st.markdown(
    '<a href="https://hanihelmet.com/en/?page_id=2031" target="_blank">'
    'HANI Helmet'
    '</a>',
    unsafe_allow_html=True
)

st.markdown(
    '<a href="http://giohelmet.com/" target="_blank">'
    'GIO Helmet'
    '</a>',
    unsafe_allow_html=True
)

st.markdown(
    '<a href="https://www.innoband.co.kr/" target="_blank">'
    'INNOBAND'
    '</a>',
    unsafe_allow_html=True
)

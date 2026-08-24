import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px

# --- 頁面與基礎設定 ---
st.set_page_config(page_title="產線管理 APP 原型", layout="wide")
st.title("雲乳食品科技股份有限公司 - 產線效能與排程 APP (測試版 v2)")

# 初始化暫存資料庫
if 'production_data' not in st.session_state:
    st.session_state.production_data = pd.DataFrame(columns=[
        '日期', '產線', '作業類型', '產品名稱', 
        '開始時間', '結束時間', '實際花費時間(H)', '生產數量(瓶)', '生產噸數(T)'
    ])

# 產線與產品連動字典
product_mapping = {
    "TR/G7": ["元初-高蛋白濃豆乳", "有飲-開心果四季春奶茶", "全家-抹茶牛乳", "全家-紅茶牛乳", "雲乳-純濃牛乳", "台牧-茶の魔手專用", "台牧-六甲田莊鮮乳", "台牧-六甲田莊極選A2β鮮乳", "台牧-六甲雙韻茶牛乳", "台牧-六甲純培咖啡牛乳", "翔本-特濃厚牛乳", "茗登-提茉西特濃牛乳", "900鮮採梅番茄", "400梅子番茄", "匯紘-奶茶", "匯紘-蘋果奶茶", "匯紘-烏龍奶茶"],
    "TR/7":  ["元初-高蛋白濃豆乳", "有飲-開心果四季春奶茶", "全家-抹茶牛乳", "全家-紅茶牛乳", "翔本-特濃厚牛乳", "900鮮採梅番茄", "400梅子番茄", "匯紘-奶茶", "匯紘-蘋果奶茶", "匯紘-烏龍奶茶"],
    "PE": ["全脂牛乳 1837", "全脂牛乳 946", "牛奶本味", "抹茶本位", "奶茶本位", "果汁牛乳", "台牧-六甲田莊巧克力牛乳乳飲品", "台牧-六甲田莊咖啡牛乳乳飲品", ]
}

# --- 側邊欄：現場紀錄輸入區 ---
st.sidebar.header("現場生產紀錄輸入")
today = st.sidebar.date_input("紀錄日期", date.today())
selected_line = st.sidebar.selectbox("生產線選擇", list(product_mapping.keys()))

# 新增作業類型選項
task_type = st.sidebar.radio("作業類型", ["產品生產", "設備蒸汽殺菌", "設備CIP清洗"])

# 根據作業類型，決定是否需要選擇產品名稱
if task_type == "產品生產":
    selected_product = st.sidebar.selectbox("產品名稱", product_mapping[selected_line])
else:
    selected_product = "-- (非生產作業) --"

st.sidebar.markdown("---")
st.sidebar.subheader("時間與產量設定")

# 統一使用開始與結束時間
start_time = st.sidebar.time_input("開始時間 (首件/作業開始)")
end_time = st.sidebar.time_input("結束時間 (末件/作業結束)")

# 僅有生產作業需要輸入數量與重量
if task_type == "產品生產":
    bottle_count = st.sidebar.number_input("實際生產數量 (瓶)", min_value=0, value=5000, step=100)
    bottle_weight = st.sidebar.number_input("單瓶重量/容量參數 (g/ml)", min_value=0, value=946, step=1)
else:
    bottle_count = 0
    bottle_weight = 0

# --- 資料寫入與運算邏輯 ---
if st.sidebar.button("確認送出紀錄"):
    if end_time <= start_time:
        st.sidebar.error("錯誤：結束時間不得早於或等於開始時間！")
    else:
        t1 = datetime.combine(today, start_time)
        t2 = datetime.combine(today, end_time)
        actual_hours = (t2 - t1).total_seconds() / 3600
        
        # 生產噸數計算 (僅在產品生產時計算)
        if task_type == "產品生產":
            production_tons = (bottle_count * bottle_weight) / 1000000
        else:
            production_tons = 0
        
        new_record = pd.DataFrame([{
            '日期': today.strftime("%Y-%m-%d"), 
            '產線': selected_line, 
            '作業類型': task_type,
            '產品名稱': selected_product,
            '開始時間': start_time.strftime("%H:%M"), 
            '結束時間': end_time.strftime("%H:%M"),
            '實際花費時間(H)': round(actual_hours, 2), 
            '生產數量(瓶)': bottle_count, 
            '生產噸數(T)': round(production_tons, 2)
        }])
        
        st.session_state.production_data = pd.concat([st.session_state.production_data, new_record], ignore_index=True)
        st.sidebar.success(f"{task_type} 紀錄已成功加入！")

# --- 主畫面：數據看板與報表 ---
st.subheader("一、 產線即時排程可視化 (甘特圖模擬)")
if not st.session_state.production_data.empty:
    df_chart = st.session_state.production_data.copy()
    df_chart['Start'] = pd.to_datetime(df_chart['日期'] + ' ' + df_chart['開始時間'])
    df_chart['Finish'] = pd.to_datetime(df_chart['日期'] + ' ' + df_chart['結束時間'])
    
    # 建立甘特圖顯示用標籤 (結合產品與作業類型)
    df_chart['顯示標籤'] = df_chart.apply(
        lambda x: x['產品名稱'] if x['作業類型'] == '產品生產' else x['作業類型'], axis=1
    )
    
    fig = px.timeline(df_chart, x_start="Start", x_end="Finish", y="產線", color="顯示標籤",
                      title="當日生產與設備保養排程狀態", height=300)
    fig.update_yaxes(autorange="reversed") 
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("目前尚無生產紀錄，請從左方側邊欄輸入測試數據。")

st.markdown("---")
st.subheader("二、 產線生產與保養紀錄表")
if not st.session_state.production_data.empty:
    st.dataframe(st.session_state.production_data, use_container_width=True)
    
    csv = st.session_state.production_data.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 匯出 Excel (CSV) 報表",
        data=csv,
        file_name=f"Production_Record_{date.today().strftime('%Y%m%d')}.csv",
        mime='text/csv',
    )
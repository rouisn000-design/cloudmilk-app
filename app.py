import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 頁面與基礎設定 ---
st.set_page_config(page_title="產線管理 APP 原型", layout="wide")
st.title("雲乳食品科技股份有限公司 - 產線效能與排程 APP (連線版)")

# --- Google 試算表串接設定 ---
@st.cache_resource
def init_connection():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open("產線生產紀錄_DB").sheet1
        return sheet
    except Exception as e:
        return None

# 初始化連線
sheet = init_connection()
db_connected = True if sheet else False

if not db_connected:
    st.error("資料庫連線失敗，請檢查金鑰或試算表名稱設定。")

# 讀取雲端資料的函數
def fetch_data():
    if db_connected:
        try:
            records = sheet.get_all_records()
            if records:
                return pd.DataFrame(records)
            else:
                # 若試算表為空，回傳包含新擴充欄位的空表頭 (🌟 新增備註欄位)
                return pd.DataFrame(columns=[
                    '日期', '產線', '作業類型', '產品名稱', 
                    '開始時間', '結束時間', '實際花費時間(H)', '實際生產數量(瓶)', 
                    '單瓶容量(ml/g)', '調配生產噸數(T)',
                    '設備標準產能(瓶/H)', '設備稼動效率(%)', '產品產出率(%)', '備註'
                ])
        except Exception as e:
             st.warning(f"讀取資料異常: {e}")
    return pd.DataFrame()

# 產線與產品連動字典
product_mapping = {
    "TR/G7": ["元初-高蛋白濃豆乳", "有飲-開心果四季春奶茶", "全家-抹茶牛乳", "全家-紅茶牛乳", "雲乳-純濃牛乳", "台牧-茶の魔手專用", "台牧-六甲田莊鮮乳", "台牧-六甲田莊極選A2β鮮乳", "台牧-六甲雙韻茶牛乳", "台牧-六甲純培咖啡牛乳", "翔本-特濃厚牛乳", "茗登-提茉西特濃牛乳", "AGV-鮮採梅番茄900", "AGV-梅子番茄400", "匯紘-阿薩姆奶茶", "匯紘-阿薩姆青森蘋果奶茶", "匯紘-阿薩姆雙茶會烏龍奶茶" ],
    "TR/7":  ["元初-高蛋白濃豆乳", "有飲-開心果四季春奶茶", "全家-抹茶牛乳", "全家-紅茶牛乳", "翔本-特濃厚牛乳", "AGV-鮮採梅番茄900", "AGV-梅子番茄400", "匯紘-阿薩姆奶茶", "匯紘-阿薩姆青森蘋果奶茶", "匯紘-阿薩姆雙茶會烏龍奶茶" ],
    "PE": ["全脂牛乳 1837", "全脂牛乳 946", "牛奶本味", "抹茶本位", "奶茶本位", "果汁牛乳", "台牧-六甲田莊巧克力牛乳乳飲品", "台牧-六甲田莊咖啡牛乳乳飲品" ], 
    "PP": ["AGV-寒天檸檬", "AGV-寒天百香", "AGV-寒天仙草", "AGV-番茄蜂蜜綜合蔬菜汁","英泉-巧克力", "英泉-麥芽", "英泉-蘋果", "英泉-草莓", "英泉-優酪乳乳酸飲料", "英泉-蔓越莓乳酸飲料","台牧-六甲田莊鮮乳", "台牧-六甲田莊牛乳", "台牧-極選牛乳", "台牧-珍稀牛乳" ], 
}

# --- 側邊欄：現場紀錄輸入區 ---
st.sidebar.header("現場生產紀錄輸入")
today = st.sidebar.date_input("紀錄日期", date.today())
selected_line = st.sidebar.selectbox("生產線選擇", list(product_mapping.keys()))

# 🌟 擴充作業類型選項
task_type = st.sidebar.radio(
    "作業類型", 
    ["產品生產", "設備蒸汽殺菌", "設備CIP清洗", "機台維修", "待料停機", "中午用餐"]
)

if task_type == "產品生產":
    selected_product = st.sidebar.selectbox("產品名稱", product_mapping[selected_line])
else:
    selected_product = "-- (非生產作業) --"

st.sidebar.markdown("---")
st.sidebar.subheader("時間與產量設定")
start_time = st.sidebar.time_input("開始時間 (首件/作業開始)")
end_time = st.sidebar.time_input("結束時間 (末件/作業結束)")

# 依據作業類型，決定是否顯示效能參數輸入框
if task_type == "產品生產":
    bottle_count = st.sidebar.number_input("實際生產數量 (瓶)", min_value=0, value=5000, step=100)
    bottle_weight = st.sidebar.number_input("單瓶容量/重量 (ml/g)", min_value=0, value=946, step=1)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 效能分析參數")
    standard_rate = st.sidebar.number_input("設備標準產能 (瓶/H)", min_value=1, value=6000, step=100)
    batch_tons = st.sidebar.number_input("調配(生產)噸數 (T)", min_value=0.0, value=5.0, step=0.1)
else:
    bottle_count = 0
    bottle_weight = 0
    standard_rate = 0
    batch_tons = 0

st.sidebar.markdown("---")
# 🌟 新增備註輸入區
remarks = st.sidebar.text_area("備註 (異常原因說明)", placeholder="若有異常、維修或特殊狀況，請簡述說明...")

# --- 資料寫入與系統自動計算邏輯 ---
if st.sidebar.button("確認送出紀錄"):
    if end_time <= start_time:
        st.sidebar.error("錯誤：結束時間不得早於或等於開始時間！")
    elif not db_connected:
        st.sidebar.error("資料庫未連線，無法寫入。")
    else:
        # 計算實際花費時間
        t1 = datetime.combine(today, start_time)
        t2 = datetime.combine(today, end_time)
        actual_hours = (t2 - t1).total_seconds() / 3600
        
        performance_rate = 0.0
        yield_rate = 0.0
        
        # 只有在「產品生產」時才計算效能與產出率
        if task_type == "產品生產":
            if actual_hours > 0 and standard_rate > 0:
                theoretical_output = standard_rate * actual_hours
                performance_rate = (bottle_count / theoretical_output) * 100
                
            if batch_tons > 0:
                actual_tons_filled = (bottle_count * bottle_weight) / 1000000
                yield_rate = (actual_tons_filled / batch_tons) * 100
        
        # 準備寫入 Google 試算表的一列資料 (🌟 寫入備註內容)
        new_row = [
            today.strftime("%Y-%m-%d"), 
            selected_line, 
            task_type,
            selected_product,
            start_time.strftime("%H:%M"), 
            end_time.strftime("%H:%M"),
            round(actual_hours, 2), 
            bottle_count, 
            bottle_weight if task_type == "產品生產" else "-",
            round(batch_tons, 2) if task_type == "產品生產" else "-",
            standard_rate if task_type == "產品生產" else "-",
            f"{round(performance_rate, 1)}%" if task_type == "產品生產" else "-",
            f"{round(yield_rate, 1)}%" if task_type == "產品生產" else "-",
            remarks  
        ]
        
        # 執行寫入
        try:
            sheet.append_row(new_row)
            st.sidebar.success(f"成功寫入雲端資料庫！")
            st.rerun() 
        except Exception as e:
            st.sidebar.error(f"寫入失敗: {e}")

# --- 主畫面：讀取雲端資料並渲染 ---
df = fetch_data()

selected_date_str = today.strftime("%Y-%m-%d")

if not df.empty:
    df_display = df[df['日期'] == selected_date_str]
else:
    df_display = pd.DataFrame()

st.subheader(f"一、 產線即時排程可視化 ({selected_date_str})")

if not df_display.empty and len(df_display) > 0:
    try:
        df_chart = df_display.copy()
        df_chart['Start'] = pd.to_datetime(df_chart['日期'].astype(str) + ' ' + df_chart['開始時間'].astype(str))
        df_chart['Finish'] = pd.to_datetime(df_chart['日期'].astype(str) + ' ' + df_chart['結束時間'].astype(str))
        
        df_chart['顯示標籤'] = df_chart.apply(
            lambda x: x['產品名稱'] if x['作業類型'] == '產品生產' else x['作業類型'], axis=1
        )
        
        # 🌟 新增：時間格式自動轉換公式 (將 4.6 轉為 4 小時 36 分鐘)
        def format_duration(h):
            try:
                h_float = float(h)
                hours = int(h_float)
                minutes = int(round((h_float - hours) * 60))
                
                if hours > 0 and minutes > 0:
                    return f"{hours} 小時 {minutes} 分鐘"
                elif hours > 0:
                    return f"{hours} 小時"
                else:
                    return f"{minutes} 分鐘"
            except:
                return str(h)

        # 套用轉換公式
        df_chart['花費時間'] = df_chart['實際花費時間(H)'].apply(format_duration)
        
        df_chart['產量'] = df_chart.apply(
            lambda x: f"{x['實際生產數量(瓶)']} 瓶" if x['作業類型'] == '產品生產' else "無", axis=1
        )
        
        df_chart['備註說明'] = df_chart['備註'].apply(lambda x: x if pd.notnull(x) and str(x).strip() != '' else '無')
        
        df_chart['設備稼動率'] = df_chart['設備稼動效率(%)'].astype(str)
        df_chart['產品產出率'] = df_chart['產品產出率(%)'].astype(str)
        
        fig = px.timeline(
            df_chart, 
            x_start="Start", 
            x_end="Finish", 
            y="產線", 
            color="顯示標籤",
            text="顯示標籤", 
            hover_name="顯示標籤",
            hover_data={
                "顯示標籤": False, 
                "Start": True,
                "Finish": True,
                "花費時間": True,
                "產量": True,
                "設備稼動率": True,  
                "產品產出率": True,  
                "備註說明": True, 
                "產線": False
            },
            title=f"{selected_date_str} 當日生產與設備保養排程", 
            height=400 
        )
        
        fig.update_yaxes(autorange="reversed", title_text="") 
        
        fig.update_xaxes(
            title_text="",
            tickformat="%H:%M",  
            dtick=3600000,       
            tickangle=45
        )
        
        fig.update_traces(textposition='inside', insidetextanchor='middle')
        
        fig.update_layout(
            legend_title_text="作業項目",
            legend=dict(
                orientation="h", 
                yanchor="top",
                y=-0.2,          
                xanchor="center",
                x=0.5
            ),
            margin=dict(t=50, b=80, l=50, r=50)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"圖表繪製異常，請稍候再試。({e})")
else:
    st.info(f"雲端資料庫中目前尚無 {selected_date_str} 的紀錄。")

st.markdown("---")
st.subheader(f"二、 {selected_date_str} 產線效能與保養紀錄表")
if not df_display.empty and len(df_display) > 0:
    st.dataframe(df_display, use_container_width=True)

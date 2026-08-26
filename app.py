import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 頁面與基礎設定 ---
st.set_page_config(page_title="產線與殺菌設備管理 APP", layout="wide")
st.title("雲乳食品科技股份有限公司 - 產線與殺菌排程效能系統 (連線版)")

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
    st.error("資料庫連線失敗，請檢查 GCP 金鑰或試算表名稱設定。")

# 讀取雲端資料函數
def fetch_data():
    if db_connected:
        try:
            records = sheet.get_all_records()
            if records:
                return pd.DataFrame(records)
            else:
                # 🌟 更新：新增「殺菌後成品量(L)」欄位
                return pd.DataFrame(columns=[
                    '日期', '設備類別', '設備名稱', '作業類型', '產品名稱', 
                    '開始時間', '結束時間', '實際花費時間(H)', '實際生產數量(瓶)', 
                    '單瓶容量(ml/g)', '調配生產噸數(T)',
                    '設備標準產能(瓶/H)', '設備稼動效率(%)', '產品產出率(%)', '殺菌後成品量(L)', '備註'
                ])
        except Exception as e:
            st.warning(f"讀取資料異常: {e}")
    return pd.DataFrame()

# --- 清單常數定義 ---
STERILIZERS = [
    "GEA 12噸板式殺菌機",
    "APV 12噸板式殺菌機",
    "鉅鵬 4噸管式殺菌機"
]

STERILIZER_CAPACITY = {
    "GEA 12噸板式殺菌機": 12000,
    "APV 12噸板式殺菌機": 12000,
    "鉅鵬 4噸管式殺菌機": 4000
}

LINES = ["TR/G7", "TR/7", "PE", "PP"]

EQUIPMENT_ORDER = STERILIZERS + LINES

PRODUCTS = [
    "台牧-生乳", "台牧-A2β生乳", "元初-高蛋白濃豆乳", "有飲-開心果四季春奶茶", "全家-抹茶牛乳", "全家-紅茶牛乳",
    "台牧-六甲田莊鮮乳", "台牧-六甲田莊極選A2β鮮乳", "台牧-六甲雙韻茶牛乳", "台牧-六甲純培咖啡牛乳",
    "翔本-特濃厚牛乳", "茗登-提茉西特濃牛乳", "AGV-鮮採梅番茄900", "AGV-梅子番茄400",
    "匯紘-阿薩姆奶茶", "匯紘-阿薩姆青森蘋果奶茶", "匯紘-阿薩姆雙茶會烏龍奶茶",
    "英泉-全脂牛乳 1837", "英泉-全脂牛乳 946", "牛奶本味", "抹茶本位", "奶茶本位", "芝麻本位", "果汁牛乳",
    "台牧-六甲田莊巧克力牛乳乳飲品", "台牧-六甲田莊咖啡牛乳乳飲品",
    "AGV-寒天檸檬", "AGV-寒天百香", "AGV-寒天仙草", "AGV-番茄蜂蜜綜合蔬菜汁",
    "英泉-巧克力", "英泉-麥芽", "英泉-蘋果", "英泉-草莓", "英泉-優酪乳乳酸飲料", "英泉-蔓越莓乳酸飲料",
    "台牧-六甲田莊牛乳", "台牧-極選牛乳", "台牧-珍稀牛乳"
]

# --- 側邊欄：現場生產紀錄輸入區 ---
st.sidebar.header("現場生產紀錄輸入")
today = st.sidebar.date_input("紀錄日期", date.today())

equip_type = st.sidebar.radio("選擇作業對象類別", ["殺菌機", "生產線"])

selected_equip = ""
task_type = "-"
selected_product = "-"
bottle_count = 0
bottle_weight = 0
standard_rate = 0
batch_tons = 0
performance_rate = 0.0
yield_rate = 0.0

if equip_type == "殺菌機":
    selected_equip = st.sidebar.selectbox("殺菌機選擇", STERILIZERS)
    task_type = st.sidebar.radio(
        "作業類型", 
        ["產品殺菌作業", "設備蒸汽殺菌", "設備CIP清洗", "機台維修", "待料停機", "中午用餐"]
    )
    
    if task_type == "產品殺菌作業":
        selected_product = st.sidebar.selectbox("產品名稱", PRODUCTS)
    else:
        selected_product = "-- (非產品殺菌作業) --"
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("時間與參數設定")
    start_time = st.sidebar.time_input("開始時間 (作業開始)", step=1)
    end_time = st.sidebar.time_input("結束時間 (作業結束)", step=1)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 設備能力參數")
    capacity = STERILIZER_CAPACITY.get(selected_equip, 0)
    st.sidebar.text_input("設備能力 (L/H)", value=f"{capacity} L", disabled=True)
    standard_rate = capacity

elif equip_type == "生產線":
    selected_equip = st.sidebar.selectbox("生產線選擇", LINES)
    task_type = st.sidebar.radio(
        "作業類型", 
        ["產品生產", "設備蒸汽殺菌", "設備CIP清洗", "機台維修", "待料停機", "中午用餐"]
    )
    is_production = (task_type == "產品生產")

    if is_production:
        selected_product = st.sidebar.selectbox("產品名稱", PRODUCTS)
    else:
        selected_product = "-- (非生產作業) --"

    st.sidebar.markdown("---")
    st.sidebar.subheader("時間與參數設定")
    start_time = st.sidebar.time_input("開始時間 (首件/作業開始)")
    end_time = st.sidebar.time_input("結束時間 (末件/作業結束)")

    if is_production:
        bottle_count = st.sidebar.number_input("實際生產數量 (瓶)", min_value=0, value=5000, step=100)
        bottle_weight = st.sidebar.number_input("單瓶容量/重量 (ml/g)", min_value=0, value=946, step=1)
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("🎯 效能分析參數")
        standard_rate = st.sidebar.number_input("設備標準產能 (瓶/H)", min_value=1, value=6000, step=100)
        batch_tons = st.sidebar.number_input("調配(生產)噸數 (T)", min_value=0.0, value=5.0, step=0.1)

st.sidebar.markdown("---")
remarks = st.sidebar.text_area("備註 (異常原因說明)", placeholder="若有異常、維修或特殊狀況，請簡述說明...")

# --- 資料寫入與系統自動計算邏輯 ---
if st.sidebar.button("確認送出紀錄"):
    if end_time <= start_time:
        st.sidebar.error("錯誤：結束時間不得早於或等於開始時間！")
    elif not db_connected:
        st.sidebar.error("資料庫未連線，無法寫入。")
    else:
        t1 = datetime.combine(today, start_time)
        t2 = datetime.combine(today, end_time)
        
        # 精確計算總秒數與小時
        total_seconds = (t2 - t1).total_seconds()
        actual_hours = total_seconds / 3600.0
        
        sterilized_volume = 0.0
        
        # 1. 殺菌機產量計算邏輯：總秒數 * 每秒能力
        if equip_type == "殺菌機" and task_type == "產品殺菌作業":
            if total_seconds > 0 and standard_rate > 0:
                capacity_per_second = standard_rate / 3600.0
                sterilized_volume = total_seconds * capacity_per_second

        # 2. 生產線效能計算邏輯
        if equip_type == "生產線" and task_type == "產品生產":
            if actual_hours > 0 and standard_rate > 0:
                theoretical_output = standard_rate * actual_hours
                performance_rate = (bottle_count / theoretical_output) * 100
                
            if batch_tons > 0:
                actual_tons_filled = (bottle_count * bottle_weight) / 1000000
                yield_rate = (actual_tons_filled / batch_tons) * 100
        
        time_format = "%H:%M:%S" if equip_type == "殺菌機" else "%H:%M"

        # 🌟 寫入新列資料，並對應 Google Sheet 新增的第 15 欄
        new_row = [
            today.strftime("%Y-%m-%d"), 
            equip_type,
            selected_equip, 
            task_type,
            selected_product,
            start_time.strftime(time_format), 
            end_time.strftime(time_format),
            round(actual_hours, 4), 
            bottle_count if equip_type == "生產線" else "-", 
            bottle_weight if equip_type == "生產線" and task_type == "產品生產" else "-",
            round(batch_tons, 2) if equip_type == "生產線" and task_type == "產品生產" else "-",
            standard_rate, 
            f"{round(performance_rate, 1)}%" if equip_type == "生產線" and task_type == "產品生產" else "-",
            f"{round(yield_rate, 1)}%" if equip_type == "生產線" and task_type == "產品生產" else "-",
            round(sterilized_volume, 2) if equip_type == "殺菌機" and task_type == "產品殺菌作業" else "-", # 新增欄位寫入
            remarks  
        ]
        
        try:
            sheet.append_row(new_row)
            st.sidebar.success(f"成功寫入雲端資料庫！")
            st.rerun() 
        except Exception as e:
            st.sidebar.error(f"寫入失敗: {e}")

# --- 主畫面：讀取雲端資料並渲染 ---
df = fetch_data()

selected_date_str = today.strftime("%Y-%m-%d")

if not df.empty and '日期' in df.columns:
    df_display = df[df['日期'] == selected_date_str]
else:
    df_display = pd.DataFrame()

st.subheader(f"一、 產線與殺菌即時排程可視化 ({selected_date_str})")

if not df_display.empty and len(df_display) > 0:
    try:
        df_chart = df_display.copy()
        
        if '設備名稱' not in df_chart.columns and '產線' in df_chart.columns:
            df_chart['設備名稱'] = df_chart['產線']
            
        df_chart['Start'] = pd.to_datetime(df_chart['日期'].astype(str) + ' ' + df_chart['開始時間'].astype(str))
        df_chart['Finish'] = pd.to_datetime(df_chart['日期'].astype(str) + ' ' + df_chart['結束時間'].astype(str))
        
        df_chart['顯示標籤'] = df_chart.apply(
            lambda x: x['產品名稱'] if x['作業類型'] in ['產品生產', '產品殺菌作業'] else x['作業類型'], axis=1
        )
        
        def format_duration(h):
            try:
                h_float = float(h)
                hours = int(h_float)
                minutes = int((h_float - hours) * 60)
                seconds = int(round((((h_float - hours) * 60) - minutes) * 60))
                
                parts = []
                if hours > 0: parts.append(f"{hours} 小時")
                if minutes > 0: parts.append(f"{minutes} 分")
                if seconds > 0: parts.append(f"{seconds} 秒")
                
                return " ".join(parts) if parts else "0 秒"
            except:
                return str(h)

        df_chart['花費時間'] = df_chart['實際花費時間(H)'].apply(format_duration)
        
        # 整合生產線產量與殺菌機產量，以供懸浮視窗顯示
        def get_production_info(row):
            if row['作業類型'] == '產品生產':
                return f"{row['實際生產數量(瓶)']} 瓶"
            elif row['作業類型'] == '產品殺菌作業':
                volume = row.get('殺菌後成品量(L)', "-")
                return f"{volume} L" if volume != "-" else "無紀錄"
            return "無"
            
        df_chart['產出量'] = df_chart.apply(get_production_info, axis=1)
        
        df_chart['備註說明'] = df_chart['備註'].apply(lambda x: x if pd.notnull(x) and str(x).strip() != '' else '無')
        df_chart['設備稼動率'] = df_chart['設備稼動效率(%)'].astype(str)
        df_chart['產品產出率'] = df_chart['產品產出率(%)'].astype(str)
        
        fig = px.timeline(
            df_chart, 
            x_start="Start", 
            x_end="Finish", 
            y="設備名稱", 
            color="顯示標籤",
            text="顯示標籤", 
            hover_name="顯示標籤",
            hover_data={
                "顯示標籤": False, 
                "Start": True,
                "Finish": True,
                "花費時間": True,
                "產出量": True,      # 🌟 生產線顯示「瓶」，殺菌機顯示「L」
                "設備稼動率": True,  
                "產品產出率": True,  
                "備註說明": True, 
                "設備名稱": False
            },
            title=f"{selected_date_str} 當日殺菌設備與生產線作業排程", 
            height=480 
        )
        
        fig.update_yaxes(
            categoryorder="array",
            categoryarray=list(reversed(EQUIPMENT_ORDER)),
            title_text=""
        ) 
        
        fig.update_xaxes(
            title_text="",
            tickformat="%H:%M:%S",  
            dtick=3600000,       
            tickangle=45
        )
        
        fig.update_traces(textposition='inside', insidetextanchor='middle')
        fig.update_layout(
            showlegend=False,
            margin=dict(t=50, b=20, l=50, r=50)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # --- 系統自動化分析報告與各線稼動率看板 ---
        st.markdown(f"### 📊 {selected_date_str} 各產線整體效能與分析報告")
        
        df_display['實際生產數量(瓶)'] = pd.to_numeric(df_display['實際生產數量(瓶)'], errors='coerce').fillna(0)
        df_display['實際花費時間(H)'] = pd.to_numeric(df_display['實際花費時間(H)'], errors='coerce').fillna(0)
        df_display['設備標準產能(瓶/H)'] = pd.to_numeric(df_display['設備標準產能(瓶/H)'], errors='coerce').fillna(0)
        
        df_display['Start'] = pd.to_datetime(df_display['日期'].astype(str) + ' ' + df_display['開始時間'].astype(str))
        df_display['Finish'] = pd.to_datetime(df_display['日期'].astype(str) + ' ' + df_display['結束時間'].astype(str))
        
        cols = st.columns(len(LINES))
        perf_dict = {}
        
        for idx, line in enumerate(LINES):
            with cols[idx]:
                line_data = df_display[df_display['設備名稱'] == line]
                prod_data = line_data[line_data['作業類型'] == '產品生產']
                
                if not prod_data.empty and prod_data['實際花費時間(H)'].sum() > 0:
                    first_start = prod_data['Start'].min()
                    last_finish = prod_data['Finish'].max()
                    total_span_hours = (last_finish - first_start).total_seconds() / 3600.0
                    
                    total_prod_hours = prod_data['實際花費時間(H)'].sum()
                    theoretical_total = (prod_data['設備標準產能(瓶/H)'] * prod_data['實際花費時間(H)']).sum()
                    weighted_avg_capacity = theoretical_total / total_prod_hours
                    total_actual_bottles = prod_data['實際生產數量(瓶)'].sum()
                    
                    if total_span_hours > 0 and weighted_avg_capacity > 0:
                        line_perf = (total_actual_bottles / (total_span_hours * weighted_avg_capacity)) * 100
                        perf_dict[line] = line_perf
                        st.metric(label=f"🟢 {line} 產線總稼動率", value=f"{line_perf:.1f}%")
                    else:
                        st.metric(label=f"⚪ {line} 產線總稼動率", value="無法計算")
                else:
                    st.metric(label=f"⚪ {line} 產線總稼動率", value="無生產紀錄")
        
        st.markdown("**💡 系統自動分析摘要：**")
        if perf_dict:
            best_line = max(perf_dict, key=perf_dict.get)
            st.write(f"- 🏆 **本日表現最佳產線**：**{best_line}**，綜合稼動率達 **{perf_dict[best_line]:.1f}%**。")
            
            low_perf_lines = [line for line, perf in perf_dict.items() if perf < 80]
            if low_perf_lines:
                st.warning(f"- ⚠️ **效能偏低提醒**：產線 **{', '.join(low_perf_lines)}** 今日總稼動率低於 80%，建議檢視表格內的【異常備註】。")
            else:
                st.success("- ✨ **整體產能狀況良好**：今日有生產的產線，總稼動率均維持在 80% 以上。")
                
        abnormal_df = df_display[df_display['作業類型'].isin(['機台維修', '待料停機'])]
        if not abnormal_df.empty:
            abnormal_df['實際花費時間(H)'] = pd.to_numeric(abnormal_df['實際花費時間(H)'], errors='coerce').fillna(0)
            total_abnormal_hours = abnormal_df['實際花費時間(H)'].sum()
            st.error(f"- 🛠️ **異常停機統計**：今日記錄到機台維修/待料停機，共計影響約 **{total_abnormal_hours:.1f} 小時**。")
        else:
            st.write("- ✅ **異常停機統計**：今日無記錄機台維修或待料停機狀況。")

    except Exception as e:
        st.warning(f"圖表繪製異常，請稍候再試。({e})")
else:
    st.info(f"雲端資料庫中目前尚無 {selected_date_str} 的紀錄。")

st.markdown("---")
st.subheader(f"二、 {selected_date_str} 產線與殺菌設備運作紀錄表")
if not df_display.empty and len(df_display) > 0:
    st.dataframe(df_display, use_container_width=True)

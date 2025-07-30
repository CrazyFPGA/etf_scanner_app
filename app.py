import streamlit as st
import pandas as pd
import tushare as ts
from datetime import datetime, timedelta

# --- Streamlit 页面配置 ---
st.set_page_config(
    page_title="ETF 200日均线扫描器",
    page_icon="📈",
    layout="wide"
)


# --- 核心扫描逻辑函数 ---
# 我们将之前的逻辑封装成一个函数，但用 yield 来实时返回状态
def run_scanner(tushare_token, percentage_threshold):
    """
    执行扫描的核心函数。
    使用 yield 实时更新状态，最后 yield 出结果DataFrame。
    """
    try:
        pro = ts.pro_api(tushare_token)
        # 检查token是否有效
        pro.trade_cal(exchange='', start_date='20200101', end_date='20200101')
    except Exception:
        yield "错误：Tushare Token 无效或网络连接失败。"
        yield pd.DataFrame()  # 返回一个空的DataFrame
        return

    # --- ETF 列表 (与之前相同) ---
    etfs_broad_base = ["510050.SH", "510300.SH", "159919.SZ", "510500.SH", "159915.SZ", "588000.SH", "159901.SZ",
                       "512100.SH"]
    etfs_industry = ["512760.SH", "515790.SH", "515030.SH", "512170.SH", "512880.SH", "512660.SH", "512690.SH"]
    etfs_cross_border = ["513100.SH", "513500.SH", "159920.SZ", "513050.SH"]
    all_etfs_to_scan = sorted(list(set(etfs_broad_base + etfs_industry + etfs_cross_border)))

    etfs_near_ma = []
    today = datetime.now()
    start_date = (today - timedelta(days=365)).strftime('%Y%m%d')
    end_date = today.strftime('%Y%m%d')

    total_count = len(all_etfs_to_scan)
    for i, symbol in enumerate(all_etfs_to_scan):
        # 使用 yield 返回实时状态更新
        yield f"处理中 ({i + 1}/{total_count}): {symbol}"
        try:
            hist = pro.fund_daily(ts_code=symbol, start_date=start_date, end_date=end_date)
            hist = hist.iloc[::-1].reset_index(drop=True)

            if len(hist) < 200:
                continue

            hist['MA200'] = hist['close'].rolling(window=200).mean()
            latest_data = hist.iloc[-1]
            last_price = latest_data['close']
            ma200 = latest_data['MA200']

            if pd.isna(ma200) or ma200 == 0:
                continue

            difference = abs(last_price - ma200)
            percentage_diff = (difference / ma200) * 100

            if percentage_diff <= percentage_threshold:
                try:
                    name = pro.fund_basic(ts_code=symbol)['name'].values[0]
                except:
                    name = "N/A"
                etfs_near_ma.append({
                    '代码': symbol,
                    '名称': name,
                    '最新价': f"{last_price:.3f}",
                    '200日均线': f"{ma200:.3f}",
                    '偏离度': f"{percentage_diff:.2f}%"
                })
        except Exception as e:
            print(f"处理 {symbol} 时出错: {e}")  # 这个打印在服务器端，用于调试
            continue

    yield "扫描完成！"
    yield pd.DataFrame(etfs_near_ma)


# --- Streamlit 界面布局 ---
st.title("📈 ETF 200日均线扫描器")
st.markdown("输入您的Tushare Token，一键扫描当前价格处于200日移动平均线附近的ETF。")

# 使用侧边栏来放置输入控件
st.sidebar.header("⚙️ 参数设置")
token = st.sidebar.text_input("输入您的Tushare Token", type="password", help="请从 Tushare.pro 官网个人主页获取")
threshold = st.sidebar.slider("设置偏离度阈值 (%)", min_value=0.5, max_value=10.0, value=2.0, step=0.5)

# 创建一个占位符，用于之后显示结果
results_placeholder = st.empty()
status_placeholder = st.empty()

if st.sidebar.button("🚀 开始扫描"):
    if not token:
        st.warning("请输入您的 Tushare Token！")
    else:
        # 清空旧结果
        results_placeholder.empty()
        status_placeholder.info("正在初始化...")

        final_df = None
        # 循环接收来自扫描函数的状态和结果
        for result in run_scanner(token, threshold):
            if isinstance(result, str):
                # 如果是字符串，更新状态
                status_placeholder.info(result)
            elif isinstance(result, pd.DataFrame):
                # 如果是DataFrame，说明是最终结果
                final_df = result

        if final_df is not None and not final_df.empty:
            results_placeholder.success("筛选结果如下：")
            results_placeholder.dataframe(final_df, use_container_width=True)
        else:
            results_placeholder.info("在指定的ETF列表中，没有找到符合条件的ETF。")

else:
    st.info("请在左侧侧边栏设置参数并点击“开始扫描”。")


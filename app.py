import streamlit as st
import google.generativeai as genai

# --- Gemini AI 配置 ---
# API Key 不寫在程式碼裡，改從 Streamlit 的 Secrets 讀取
# （在 Streamlit 後台 Manage app → Settings → Secrets 填入：GEMINI_API_KEY = "你的新金鑰"）
DEFAULT_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# --- Streamlit 網頁介面設計 ---
st.set_page_config(layout="wide", page_title="精神科專屬 SOIE 紀錄優化器 Pro (AI融合版)")
st.title("🧠 精神科專屬 SOIE 護理紀錄生成器 (AI 語意無縫融合版)")
st.caption("已優化手寫內容邏輯！AI 現在會自動將您的手寫補充嵌入敘事中最流暢、最適合的脈絡位置。")

# 側邊欄：保留金鑰彈性與說明
with st.sidebar:
    st.markdown("### 🔑 AI 大腦設定")
    # 金鑰只留在伺服器端，不再預填進輸入框（預填的值會被送到每位使用者的瀏覽器）
    user_key = st.text_input("Gemini API Key（可留空，使用預設金鑰）：", type="password")
    api_key = user_key or DEFAULT_API_KEY
    st.caption("⚠️ 請勿輸入病人姓名、病歷號、床號等可識別個資")
    st.markdown("---")
    st.markdown("""
    **💡 臨床流暢提示：**
    手寫補充欄位您可以隨心所欲地打，AI 會根據上下文語意（例如看到『繞圈』就結合『大廳活動』），自動把它們安插在最自然的位置，不會再死板地丟在最末端！
    """)

# 初始化 Gemini 模型的函式
def generate_soie_with_ai(raw_data_summary, api_key):
    if not api_key:
        return "❌ 錯誤：請在左側輸入您的 Gemini API Key 才能啟動 AI 功能！"
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=(
                "你是一位資深的精神科護理師。你的任務是將使用者勾選的精神症狀與護理處置關鍵字，"
                "融合成一段結構嚴謹、語氣自然、排版流暢的精神科 SOIE 護理紀錄。\n\n"
                "【💡 核心融合規則：針對手寫補充】\n"
                "使用者在各區填寫的「手寫補充內容」是該段落的核心情境。你必須根據語意，將手寫補充的細節"
                "自然地交織、嵌入在勾選症狀之間。絕對不要把手寫補充硬塞在段落的最後面！"
                "例如：如果勾選了『大多於大廳活動』，手寫補充了『在大廳繞圈情形』，應融合成『大多於大廳活動，可見在大廳繞圈情形』，而非放在句尾端。\n\n"
                "【重要：你必須嚴格模仿以下使用者的個人書寫風格範本】\n"
                "範本內容：\n"
                "S:今天幻聽很多，所以我一直在走路轉移，手摀著耳朵會好一點\n"
                "O:精神可，情緒平穩，表情淡漠，言談可切題，抱怨聽幻覺干擾，可見手摀住耳朵、在大廳繞圈情形，大多於大廳活動，乏人際互動，活動步態平穩。\n"
                "I:自我介紹，建立良好治療性人際關係，引導會談，了解目前症狀干擾情形，傾聽其聽幻覺所帶來的困擾，與其討論轉移聽幻覺之方法，對於目前之轉移方式給予肯定，定時探視，觀察並記錄其行為表現，當症狀干擾嚴重時給予必要協助，予預防跌倒衛教：採漸進式下床、睡前少喝水、发生意外时需呼叫旁人。\n"
                "E：可說出聽幻覺干擾情形，聽幻覺尚可轉移，班內未額外尋求協助，可了解預防跌倒衛教，班內無跌倒情形。\n\n"
                "【基本書寫規則】\n"
                "1. 必須嚴格切分 S:、O:、I:、E: 四個段落，字詞間使用「，」或「、」做流暢連接，絕不要出現死板的條列式。\n"
                "2. 語氣要保持醫學紀錄的客觀性與專業性，並符合上述範本的用詞習慣。"
            )
        )
        
        response = model.generate_content(
            f"請將以下臨床資料，融合手寫細節，轉化為完美流暢的精神科 SOIE 紀錄：\n\n{raw_data_summary}",
            generation_config={"temperature": 0.3}
        )
        return response.text
    except Exception as e:
        print(f"Gemini error: {e}")  # 詳細錯誤只寫進後台 log
        return "❌ AI 聯絡失敗，請稍後再試，或檢查 API Key 是否有效。"

col1, col2 = st.columns([6, 4])

with col1:
    # === S 區 ===
    st.markdown("### 📝 【S】個案主訴 (Subjective)")
    s_text = st.text_input("主訴內容（手寫輸入）：", placeholder="例如：個案表示「今天心情比較好」或「聽幻覺一直叫我走動」...")
    
    st.write("---")
    
    # === O 區 ===
    st.markdown("### 🔍 【O】客觀精神症狀與評估 (Objective)")
    o_col1, o_col2, o_col3 = st.columns(3)
    
    with o_col1:
        st.caption("精神、情緒與風險")
        o_active = st.checkbox("精神可")
        o_fatigue = st.checkbox("精神倦怠")
        o_stable = st.checkbox("情緒平穩")
        o_depressed = st.checkbox("情緒顯低落")
        o_agitated = st.checkbox("情緒激躁易怒")
        o_anxious = st.checkbox("焦慮不安")
        o_labile = st.checkbox("情緒起伏大/情動不穩")
        o_smile = st.checkbox("表情有笑容")
        o_flat = st.checkbox("表情淡漠")
        
    with o_col2:
        st.caption("言談、思考與知覺干擾")
        o_coherent = st.checkbox("言談可切題")
        o_delusion = st.checkbox("言談夾雜妄想內容")
        o_grandiose = st.checkbox("言談誇大")
        o_poor_reality = st.checkbox("言談乏現實感")
        o_pressure = st.checkbox("言談速度快且量多")
        o_flight = st.checkbox("思考跳躍")
        o_gesturing = st.checkbox("對空比劃與手勢行為")
        o_muttering = st.checkbox("喃喃自語")
        o_avh = st.checkbox("抱怨聽/視幻覺干擾")
        o_aggressive = st.checkbox("具言語/身體攻擊傾向")
        o_suicidal = st.checkbox("具自殺/自傷意念或衝動")
        o_runaway = st.checkbox("企圖衝出病房")
        
    with o_col3:
        st.caption("活動、社交與步態輔具")
        o_activity = st.checkbox("大多於大廳活動/可參與病室活動")
        o_ot = st.checkbox("可參與職能治療")
        o_lying = st.checkbox("整天躺床/活動量少")
        o_passive = st.checkbox("被動配合常規")
        o_no_interaction = st.checkbox("乏人際互動")
        st.checkbox("人際互動良好", key="o_good_int")
        st.checkbox("可與部分病友互動", key="o_peer_int")
        o_gait_stable = st.checkbox("活動步態平穩")
        o_gait_unstable = st.checkbox("下床活動時步態欠穩")
        o_wheelchair = st.checkbox("輪椅代步")
        
    o_extra = st.text_input("✍️ O 區症狀/情境手寫補充：", placeholder="例如：可見手摀住耳朵、在大廳繞圈情形...")

    st.write("---")

    # === I 區 ===
    st.markdown("### 🛠️ 【I】護理措施 (Intervention)")
    i_col1, i_col2 = st.columns(2)
    
    with i_col1:
        st.caption("治療性關係與症狀處理")
        i_intro = st.checkbox("自我介紹")
        i_relation = st.checkbox("建立與維持良好治療性人際關係")
        i_interview = st.checkbox("引導會談並了解目前症狀干擾情形")
        i_empathy = st.checkbox("傾聽其幻覺困擾並同理感受")
        i_distract = st.checkbox("與其討論轉移聽幻覺之方法並對目前方式給予肯定")
        i_visit = st.checkbox("定時探視並觀察記錄行為表現")
        i_assist = st.checkbox("症狀干擾嚴重時給予必要協助")
        i_reality = st.checkbox("引導現實導向，不爭辯妄想內容")
        i_med = st.checkbox("督促按時服藥並確實檢查有無藏藥")
        i_security = st.checkbox("加強查房與環境安全檢查")
        
    with i_col2:
        st.caption("特殊護理與預防跌倒")
        i_restraint = st.checkbox("依醫囑執行保護性約束護理")
        i_fall_edu = st.checkbox("予預防跌倒衛教：採漸進式下床、睡前少喝水、發生意外時需呼叫旁人")
        
    i_extra = st.text_input("✍️ I 區措施/情境手寫補充：", placeholder="例如：引導會談時了解目前聽幻覺干擾細節...")

    st.write("---")

    # === E 區 ===
    st.markdown("### 📊 【E】護理評值 (Evaluation)")
    e_col1, e_col2 = st.columns(2)
    
    with e_col1:
        st.caption("行為與精神症狀反應")
        e_express = st.checkbox("可說出聽幻覺/精神症狀干擾情形")
        e_distracted = st.checkbox("聽幻覺尚可轉移")
        e_no_help = st.checkbox("班內未額外尋求協助")
        e_cooperate = st.checkbox("行為可配合治療與病房常規")
        e_med_ok = st.checkbox("能確實服藥，無藏藥行為")
        e_accept_edu = st.checkbox("可了解預防跌倒衛教內容")
        e_no_fall = st.checkbox("班內無跌倒情形")
        
    e_extra = st.text_input("✍️ E 區反應/情境手寫補充：", placeholder="例如：聽幻覺仍存在但尚可配合轉移...")

    st.write("---")
    submit = st.button("🚀 啟動 Gemini AI 生成專屬護理紀錄", type="primary")

with col2:
    st.markdown("### 📋 AI 靈魂優化複製區（直接貼上 HIS）")
    if submit:
        with st.spinner("🧠 Gemini 大腦正在無縫揉合您的手寫細節中..."):
            # 彙整勾選重點
            o_summary = []
            if o_active: o_summary.append("精神可")
            if o_fatigue: o_summary.append("精神倦怠")
            if o_stable: o_summary.append("情緒平穩")
            if o_depressed: o_summary.append("情緒顯低落")
            if o_agitated: o_summary.append("情緒激躁易怒")
            if o_flat: o_summary.append("表情淡漠")
            if o_coherent: o_summary.append("言談可切題")
            if o_delusion: o_summary.append("言談夾雜妄想")
            if o_muttering: o_summary.append("喃喃自語")
            if o_avh: o_summary.append("抱怨聽幻覺干擾、手摀住耳朵")
            if o_activity: o_summary.append("大多於大廳活動")
            if o_no_interaction: o_summary.append("乏人際互動")
            if o_gait_stable: o_summary.append("活動步態平穩")

            i_summary = []
            if i_intro: i_summary.append("自我介紹")
            if i_relation: i_summary.append("建立良好治療性人際關係")
            if i_interview: i_summary.append("引導會談，了解目前症狀干擾情形")
            if i_empathy: i_summary.append("傾聽其聽幻覺所帶來的困擾")
            if i_distract: i_summary.append("與其討論轉移聽幻覺之方法，對於目前之轉移方式給予肯定")
            if i_visit: i_summary.append("定時探視，觀察並記錄其行為表現")
            if i_assist: i_summary.append("當症狀干擾嚴重時給予必要協助")
            if i_med: i_summary.append("督促按時服藥並檢查有無藏藥")
            if i_fall_edu: i_summary.append("予預防跌倒衛教：採漸進式下床、睡前少喝水、發生意外時需呼叫旁人")

            e_summary = []
            if e_express: e_summary.append("可說出聽幻覺干擾情形")
            if e_distracted: e_summary.append("聽幻覺尚可轉移")
            if e_no_help: e_summary.append("班內未額外尋求協助")
            if e_accept_edu: e_summary.append("可了解預防跌倒衛教")
            if e_no_fall: e_summary.append("班內無跌倒情形")

            # 重新組織 Payload，明確指示手寫是「融入用的細節情境」
            raw_input_payload = f"""
            【S 區主訴】: {s_text if s_text else "個案未主動表達特殊主訴"}
            
            【O 區常規勾選】: {"、".join(o_summary)}
            【O 區核心手寫補充（請自然嵌入上述勾選脈絡中）】: {o_extra if o_extra else "無"}
            
            【I 區常規勾選】: {"、".join(i_summary)}
            【I 區核心手寫補充（請自然嵌入上述勾選脈絡中）】: {i_extra if i_extra else "無"}
            
            【E 區常規勾選】: {"、".join(e_summary)}
            【E 區核心手寫補充（請自然嵌入上述勾選脈絡中）】: {e_extra if e_extra else "無"}
            """
            
            ai_output = generate_soie_with_ai(raw_input_payload, api_key)
            
            st.text_area("直接全選複製：", value=ai_output, height=500)
            st.success("🎉 完美融合！手寫內容已流暢嵌入脈絡中！")

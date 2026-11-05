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
                "I:自我介紹，建立良好治療性人際關係，引導會談，了解目前症狀干擾情形，傾聽其聽幻覺所帶來的困擾，與其討論轉移聽幻覺之方法，對於目前之轉移方式給予肯定，定時探視，觀察並記錄其行為表現，當症狀干擾嚴重時給予必要協助，給予預防跌倒衛教：採漸進式下床、晚餐後減少飲水、睡前如廁、若有需要可請求他人協助。\n"
                "E：可說出聽幻覺干擾情形，聽幻覺尚可轉移，班內未額外尋求協助，對衛教內容可點頭表了解及接受，無跌倒情形。\n\n"
                "【基本書寫規則】\n"
                "1. 必須嚴格切分 S:、O:、I:、E: 四個段落，字詞間使用「，」或「、」做流暢連接，絕不要出現死板的條列式。\n"
                "2. 語氣要保持醫學紀錄的客觀性與專業性，並符合上述範本的用詞習慣。\n"
                "3. 只能根據使用者提供的勾選與手寫內容撰寫，範本僅供模仿語氣，絕對不可自行添加未提供的症狀、行為或措施。\n"
                "4. 例外：若某區標示「請 AI 依 S、O 區建議」，才可依 S、O 區內容，撰寫合理且常規的精神科護理措施（I）或評值（E）；S、O 區仍只能寫使用者提供的內容。"
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

# 小工具：畫出一組勾選框，回傳「有被勾選的項目」清單
# 以後要新增選項，只要在下面的清單加一行文字就好，不用再另外寫 if 判斷
def checkbox_group(labels, prefix):
    return [label for label in labels if st.checkbox(label, key=f"{prefix}_{label}")]

# ==================================================================
# 白班 SOIE 選項（依單位實際紀錄的高頻用詞整理）
# ==================================================================
O_LOOK = ["精神可", "精神顯倦怠", "外觀衣著合宜", "外觀衣著未修飾", "頭髮凌亂", "鬍鬚長"]
O_MOOD = ["情緒無明顯起伏", "情緒顯低落", "焦慮不安", "情緒激躁易怒", "情緒起伏大/情動不穩",
          "表情自然", "表情平淡", "表情淡漠", "偶有笑容", "表情愁苦"]
O_RISK = ["具言語/身體攻擊傾向", "具自殺/自傷意念或衝動", "企圖衝出病房"]
O_TALK = ["言談可切題", "言談部分切題", "言談被動", "言談簡短", "言談夾雜妄想內容", "言談誇大",
          "言談乏現實感", "言談速度快且量多", "思考跳躍", "對空比劃與手勢行為", "喃喃自語",
          "抱怨聽/視幻覺干擾", "乏病識感"]
O_ACT = ["多於大廳活動", "多於房內活動", "可於大廳觀賞電視", "多獨自在大廳來回走動",
         "整天躺床/活動量少", "可主動參與職能治療", "被動配合常規",
         "人際互動可", "人際互動合宜", "人際互動少", "人際互動疏離", "可與部分病友互動"]
O_GAIT = ["活動步態平穩", "活動步態緩慢尚穩", "下床活動時步態欠穩", "輪椅代步"]

I_RELATION = ["自我介紹", "採尊重、友善及信任態度主動接觸", "建立治療性人際關係", "維持治療性人際關係",
              "主動關心及定時探視", "引導會談", "集中會談主題"]
I_EMOTION = ["予以傾聽及同理", "提供情緒宣洩管道", "引導表達內心想法及感受", "適時安撫情緒",
             "評估精神症狀對日常生活之影響", "評估情緒變化及行為表現",
             "與其討論轉移聽幻覺之方法並對目前方式給予肯定", "引導現實導向，不爭辯妄想內容",
             "對正向行為給予肯定", "鼓勵參與病房活動", "視情況提供協助"]
I_SAFETY = ["確實給藥、監督服藥", "服藥時予藥物衛教", "觀察藥物效果", "提醒注意活動安全",
            "加強查房與環境安全檢查", "依醫囑執行保護性約束護理",
            "給予預防跌倒衛教：採漸進式下床、晚餐後減少飲水、睡前如廁、若有需要可請求他人協助"]
I_RISK_TYPES = ["暴力", "自殺", "自傷", "逃跑", "性不適切"]
RISK_LEVELS = ["不註明級數", "第一級", "第二級", "第三級", "第四級"]

E_BEHAVIOR = ["無跌倒情形", "暫無不適切行為", "班內行為可配合", "情緒可自控",
              "可配合服藥及張口檢查", "可主動排隊服藥、張口檢查", "引導下可參與活動"]
E_RESPONSE = ["對衛教內容可點頭表了解及接受", "被動接受衛教內容", "可說出其感受", "可說出內心想法及感受",
              "可說出聽幻覺/精神症狀干擾情形", "聽幻覺尚可轉移", "可說出目前症狀改善", "班內未額外尋求協助"]


def risk_sentence():
    """防範危急：選種類＋級數，組成「依醫囑持續防範暴力(第三級)及逃跑危急」"""
    types = st.multiselect("🚨 依醫囑防範危急（可複選）", I_RISK_TYPES)
    parts = []
    for t in types:
        lv = st.selectbox(f"{t} 級數", RISK_LEVELS, key=f"risk_{t}")
        parts.append(t if lv == "不註明級數" else f"{t}({lv})")
    return f"依醫囑持續防範{'及'.join(parts)}危急" if parts else None


def day_shift():
    col1, col2 = st.columns([6, 4])

    with col1:
        # === S 區 ===
        st.markdown("### 📝 【S】個案主訴 (Subjective)")
        s_text = st.text_input("主訴內容（手寫輸入）：", placeholder="例如：個案表示「今天心情比較好」或「聽幻覺一直叫我走動」...")
        st.write("---")

        # === O 區 ===
        st.markdown("### 🔍 【O】客觀精神症狀與評估 (Objective)")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.caption("外觀與精神")
            o_summary = checkbox_group(O_LOOK, "o")
            st.caption("情緒與表情")
            o_summary += checkbox_group(O_MOOD, "o")
            st.caption("風險行為")
            o_summary += checkbox_group(O_RISK, "o")
        with c2:
            st.caption("言談、思考與知覺")
            o_summary += checkbox_group(O_TALK, "o")
        with c3:
            st.caption("活動與人際互動")
            o_summary += checkbox_group(O_ACT, "o")
            st.caption("步態")
            o_summary += checkbox_group(O_GAIT, "o")
            fall_score = st.number_input("跌倒高危險評估（分，0 = 不寫）", min_value=0, max_value=20, step=1)
            if fall_score:
                o_summary.append(f"跌倒高危險評估{fall_score}分")
        o_extra = st.text_input("✍️ O 區症狀/情境手寫補充：", placeholder="例如：可見手摀住耳朵、在大廳繞圈情形...")
        st.write("---")

        # === I 區 ===
        st.markdown("### 🛠️ 【I】護理措施 (Intervention)")
        c1, c2 = st.columns(2)
        with c1:
            st.caption("治療性關係")
            i_summary = checkbox_group(I_RELATION, "i")
            st.caption("情緒與症狀處理")
            i_summary += checkbox_group(I_EMOTION, "i")
        with c2:
            st.caption("給藥與安全")
            i_summary += checkbox_group(I_SAFETY, "i")
            risk = risk_sentence()
            if risk:
                i_summary.append(risk)
        i_extra = st.text_input("✍️ I 區措施/情境手寫補充：", placeholder="例如：引導會談時了解目前聽幻覺干擾細節...")
        st.write("---")

        # === E 區 ===
        st.markdown("### 📊 【E】護理評值 (Evaluation)")
        c1, c2 = st.columns(2)
        with c1:
            st.caption("行為與服藥")
            e_summary = checkbox_group(E_BEHAVIOR, "e")
        with c2:
            st.caption("表達與衛教反應")
            e_summary += checkbox_group(E_RESPONSE, "e")
        e_extra = st.text_input("✍️ E 區反應/情境手寫補充：", placeholder="例如：聽幻覺仍存在但尚可配合轉移...")
        st.write("---")

        # I、E 自動建議開關（預設關閉）
        auto_mode = st.toggle("✨ I、E 沒勾也沒寫時，由 AI 依 S、O 區自動建議", value=False)
        submit = st.button("🚀 啟動 Gemini AI 生成專屬護理紀錄", type="primary")

    with col2:
        st.markdown("### 📋 AI 靈魂優化複製區（直接貼上 HIS）")
        if submit:
            with st.spinner("🧠 Gemini 大腦正在無縫揉合您的手寫細節中..."):
                # 判斷 I、E 是否需要 AI 自動建議（開關打開，且該區沒勾也沒寫）
                auto_i = auto_mode and not i_summary and not i_extra
                auto_e = auto_mode and not e_summary and not e_extra
                i_block = ("【I 區】: 使用者未填寫，請 AI 依 S、O 區建議" if auto_i else
                           f"【I 區常規勾選】: {'、'.join(i_summary) if i_summary else '無'}\n"
                           f"【I 區核心手寫補充（請自然嵌入上述勾選脈絡中）】: {i_extra if i_extra else '無'}")
                e_block = ("【E 區】: 使用者未填寫，請 AI 依 S、O 區建議" if auto_e else
                           f"【E 區常規勾選】: {'、'.join(e_summary) if e_summary else '無'}\n"
                           f"【E 區核心手寫補充（請自然嵌入上述勾選脈絡中）】: {e_extra if e_extra else '無'}")

                raw_input_payload = (
                    f"【S 區主訴】: {s_text if s_text else '個案未主動表達特殊主訴'}\n\n"
                    f"【O 區常規勾選】: {'、'.join(o_summary) if o_summary else '無'}\n"
                    f"【O 區核心手寫補充（請自然嵌入上述勾選脈絡中）】: {o_extra if o_extra else '無'}\n\n"
                    f"{i_block}\n\n{e_block}\n"
                )

                ai_output = generate_soie_with_ai(raw_input_payload, api_key)

                st.text_area("直接全選複製：", value=ai_output, height=500)
                if auto_i or auto_e:
                    parts = "、".join(x for x, on in (("I", auto_i), ("E", auto_e)) if on)
                    st.warning(f"⚠️ {parts} 段是 AI 建議的內容，請確認都是你實際執行、觀察到的，必要時修改後再貼進 HIS。")
                else:
                    st.success("🎉 完美融合！手寫內容已流暢嵌入脈絡中！")


# ==================================================================
# 大夜：夜眠紀錄（不經過 AI，程式直接組句子）
# ==================================================================
WAKE_REASONS = ["如廁", "翻身", "自行醒來"]
MORNING = ["晨起無不適切情緒及行為表現", "晨起步態平穩", "晨起下床坐輪椅代步", "可自行完成梳洗",
           "晨起可配合抽血", "叫人鈴備用"]


def night_shift():
    col1, col2 = st.columns([6, 4])

    with col1:
        st.markdown("### 🌙 夜眠情形")
        c1, c2 = st.columns(2)
        with c1:
            start = st.selectbox("接班時", ["已入睡", "尚未入睡", "於大廳活動", "靜躺未入睡"])
            breath = st.checkbox("呼吸平順", value=True)
            times = st.number_input("夜眠中斷次數", min_value=0, max_value=20, step=1)
            reasons = st.multiselect("中斷原因（可複選）", WAKE_REASONS) if times else []
            after = (st.selectbox("中斷後", ["可再入睡", "可再短暫入睡", "未再入睡",
                                            "主動至護理站要求助眠藥物，服藥後可入睡"])
                     if times else None)
        with c2:
            hours = st.number_input("夜眠共計（小時）", min_value=0.0, max_value=12.0, step=0.5, value=6.0)
            early = st.text_input("早醒時間（沒有就留空）", placeholder="例如：0430")
            sugar = st.text_input("晨起飯前血糖 mg/dL（沒有就留空）", placeholder="例如：126")

        st.markdown("### 🌅 晨間情形")
        morning = checkbox_group(MORNING, "n")
        extra = st.text_input("✍️ 其他補充（例如中斷時的狀況）：",
                              placeholder="例如：0300 醒來至護理站表示睡不著，予傾聽後返室躺床")

    # --- 組句子 ---
    parts = [f"接班時{start}"]
    if breath:
        parts.append("呼吸平順")
    if times == 0:
        parts.append("夜眠無中斷")
    else:
        why = f"（{'、'.join(reasons)}）" if reasons else ""
        parts.append(f"夜眠中斷{times}次{why}")
        parts.append(after)
    if extra:
        parts.append(extra.strip("，。 "))
    parts.append(f"夜眠共計{hours:g}小時")
    if early:
        parts.append(f"{early}早醒")
    parts += morning
    if sugar:
        parts.append(f"晨起飯前血糖：{sugar}mg╱dL")
    note = "，".join(parts) + "。"

    with col2:
        st.markdown("### 📋 複製區（直接貼上 HIS）")
        st.text_area("直接全選複製：", value=note, height=200)
        st.caption("💡 大夜紀錄由程式直接組成，不經過 AI，不消耗額度，數字也不會寫錯。")


# ==================================================================
# 班別選擇
# ==================================================================
shift = st.radio("請選擇班別：", ["🌞 白班（SOIE）", "🌙 大夜（夜眠紀錄）"], horizontal=True)
st.write("---")
if shift.startswith("🌞"):
    day_shift()
else:
    night_shift()

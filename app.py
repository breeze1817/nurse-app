import streamlit as st
import google.generativeai as genai
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# --- Gemini AI 配置 ---
# API Key 不寫在程式碼裡，改從 Streamlit 的 Secrets 讀取
# （在 Streamlit 後台 Manage app → Settings → Secrets 填入：GEMINI_API_KEY = "你的新金鑰"）
DEFAULT_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# --- Streamlit 網頁介面設計 ---
st.set_page_config(layout="wide", page_title="精神科專屬 SOIE 紀錄優化器 Pro (AI融合版)")
st.title("🧠 精神科專屬 SOIE 護理紀錄生成器 (AI 語意無縫融合版)")
st.caption("已優化手寫內容邏輯！AI 現在會自動將您的手寫補充嵌入敘事中最流暢、最適合的脈絡位置。")

# API Key 一律使用 Secrets 裡的金鑰，不需要使用者輸入，因此移除左側欄
api_key = DEFAULT_API_KEY
st.warning("⚠️ 請勿輸入病人姓名、病歷號、床號等可識別個資")
quota_box = st.empty()  # 今日剩餘次數，等整頁跑完再填入最新數字

# --- 今日 AI 使用次數（估算）---
# Gemini 免費版每天 20 次，在美國太平洋時間午夜重置（台灣時間下午 3～4 點）
# 計數存在伺服器記憶體裡，所有使用者共用；App 重新啟動（休眠、Reboot、更新程式）時會歸零
DAILY_LIMIT = 20
PACIFIC = ZoneInfo("America/Los_Angeles")
TAIPEI = ZoneInfo("Asia/Taipei")


@st.cache_resource
def usage_store():
    return {"date": None, "count": 0, "exhausted": False}


def get_usage():
    u = usage_store()
    today = datetime.now(PACIFIC).date()
    if u["date"] != today:  # 過了重置時間就歸零
        u.update(date=today, count=0, exhausted=False)
    return u


def next_reset_taipei():
    now = datetime.now(PACIFIC)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight.astimezone(TAIPEI).strftime("%H:%M")


def show_quota():
    u = get_usage()
    left = 0 if u["exhausted"] else max(DAILY_LIMIT - u["count"], 0)
    msg = (f"🔋 今日 AI 剩餘次數：約 **{left} / {DAILY_LIMIT}** 次"
           f"（台灣時間 {next_reset_taipei()} 重置；小夜、大夜紀錄不用 AI，不受限制）")
    if left == 0:
        quota_box.error(msg + "\n\n今日額度已用完，請等重置後再使用 AI 生成。")
    elif left <= 5:
        quota_box.warning(msg)
    else:
        quota_box.info(msg)

# 初始化 Gemini 模型的函式
def generate_soie_with_ai(raw_data_summary, api_key):
    if not api_key:
        return "❌ 錯誤：系統尚未設定 Gemini API Key（請到 Streamlit 的 Secrets 設定 GEMINI_API_KEY）"
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=(
                "你是一位資深的精神科護理師。你的任務是將使用者勾選的精神症狀與護理處置關鍵字，"
                "融合成一段符合單位書寫習慣的精神科 SOIE 護理紀錄。\n\n"
                "【💡 核心融合規則：針對手寫補充】\n"
                "使用者在各區填寫的「手寫補充內容」是該段落的核心情境。你必須根據語意，將手寫補充的細節"
                "自然地交織、嵌入在勾選症狀之間。絕對不要把手寫補充硬塞在段落的最後面！"
                "例如：如果勾選了『大多於大廳活動』，手寫補充了『在大廳繞圈情形』，應融合成『大多於大廳活動，可見在大廳繞圈情形』，而非放在句尾端。\n\n"
                "【重要：你必須嚴格模仿以下單位實際紀錄的書寫風格與排列順序】\n"
                "範例一：\n"
                "S：現在晚上睡覺還是會有嗡嗡嗡的聲音，機器的聲音，已經有一兩個月了，但是不會因為這樣睡不著。"
                "O：外觀衣著合宜，精神可，表情自然，情緒無明顯起伏，言談可切題回應，多於大廳活動，人際互動少，下床活動步態平穩。"
                "I：採尊重、親切態度與其接觸，主動關心及定時探視，維持治療性人際關係，引導表達內心之想法及感受，予以傾聽及同理，"
                "評估聽幻覺內容及對日常生活之干擾程度，醫囑持續防範暴力(二級)及性不適切之危急；"
                "給予預防跌倒衛教：採漸進式下床、晚餐後減少飲水、睡前如廁、若有需要可請求他人協助。"
                "E：點頭表示理解衛教內容，無跌倒情形。\n"
                "範例二：\n"
                "S：我有感覺比較累，可能是最近走太多路了。"
                "O：外觀衣著合宜，精神顯倦怠，表情平淡，情緒未見明顯起伏，言談可切題，多於房內獨處，人際互動少，活動步態平穩。"
                "I：採誠懇、尊重、溫和之態度與其接觸，維持治療性人際關係，主動關心及定時探視，引導表達內心想法及感受，予傾聽並同理其感受，"
                "確實給藥，監督服藥，給予預防跌倒衛教：採漸進式下床、晚餐後減少飲水、睡前如廁、若有需要可請求他人協助，提醒注意活動安全。"
                "E：對衛教內容可點頭表了解及接受，暫無不適切行為、跌倒情形發生。\n\n"
                "【基本書寫規則】\n"
                "1. 必須嚴格切分 S：、O：、I：、E： 四個段落，字詞間使用「，」或「、」做流暢連接，絕不要出現死板的條列式。\n"
                "2. 語氣要保持醫學紀錄的客觀性與專業性，並符合上述範例的用詞習慣。\n"
                "2-1. 勾選項目已依單位習慣排好順序（O 區：外觀衣著→精神→表情→情緒→言談→活動→人際互動→步態；I 區最後為防範危急、跌倒衛教、提醒注意活動安全；E 區最後為無跌倒情形），請照提供的順序撰寫，盡量保留勾選詞彙原文，不要改寫或重新排列，手寫補充依語意插入最合適的位置。\n"
                "3. 只能根據使用者提供的勾選與手寫內容撰寫，範本僅供模仿語氣，絕對不可自行添加未提供的症狀、行為或措施。\n"
                "4. 例外：若某區標示「請 AI 依 S、O 區建議」，才可依 S、O 區內容，撰寫合理且常規的精神科護理措施（I）或評值（E）；S、O 區仍只能寫使用者提供的內容。"
            )
        )
        
        get_usage()["count"] += 1  # 每送出一次請求就算一次（失敗也會被 Google 計入）
        response = model.generate_content(
            f"請將以下臨床資料，融合手寫細節，轉化為完美流暢的精神科 SOIE 紀錄：\n\n{raw_data_summary}",
            generation_config={"temperature": 0.3}
        )
        return response.text
    except Exception as e:
        print(f"Gemini error: {e}")  # 詳細錯誤只寫進後台 log
        err = str(e)
        if "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
            if "PerDay" in err or "per day" in err.lower():
                get_usage()["exhausted"] = True
                return "❌ 今日 AI 免費額度已用完，請等重置後再使用。"
            return "❌ 使用太頻繁（每分鐘上限 5 次），請等 1 分鐘後再試。"
        if "503" in err:
            return "❌ Google 伺服器忙碌中，請過幾秒再按一次生成。"
        return "❌ AI 聯絡失敗，請稍後再試，或檢查 API Key 是否有效。"

# 小工具：畫出一組勾選框，回傳「有被勾選的項目」清單（大夜晨間情形使用）
def checkbox_group(labels, prefix):
    return [label for label in labels if st.checkbox(label, key=f"{prefix}_{label}")]


def pick_row(label, options, key):
    """一列一個項目：左邊是項目名稱，右邊是可複選的按鈕。
    按鈕上會省略和項目名稱重複的開頭字（例如「表情」列的「表情自然」顯示成「自然」），
    但送給 AI 的仍是完整詞彙。回傳順序固定依選項排列順序。"""
    def short(x):
        return x[len(label):] if x.startswith(label) and len(x) > len(label) else x
    c1, c2 = st.columns([1.3, 8])
    c1.markdown(f"**{label}**")
    with c2:
        if hasattr(st, "pills"):
            picked = st.pills(label, options, selection_mode="multi", format_func=short,
                              key=key, label_visibility="collapsed") or []
        else:  # 舊版 Streamlit 沒有 pills，改用下拉複選
            picked = st.multiselect(label, options, format_func=short, key=key,
                                    label_visibility="collapsed")
    return [o for o in options if o in picked]


# ==================================================================
# 共用的「列」：（項目名稱, 選項清單）——由上到下就是紀錄的書寫順序
# 以後要新增選項，只要在對應的清單加一個詞就好
# ==================================================================
R_LOOK = ("外觀衣著", ["外觀衣著合宜", "外觀衣著未修飾", "頭髮凌亂", "鬍鬚長"])
R_SPIRIT = ("精神", ["精神可", "精神顯倦怠"])
R_FACE = ("表情", ["表情自然", "表情平淡", "表情淡漠", "偶有笑容", "表情愁苦"])
R_MOOD = ("情緒", ["情緒無明顯起伏", "情緒顯低落", "焦慮不安", "情緒激躁易怒", "情緒起伏大/情動不穩"])
R_TALK = ("言談", ["言談可切題", "言談部分切題", "言談被動", "言談簡短", "言談夾雜妄想內容",
                  "言談誇大", "言談乏現實感", "言談速度快且量多"])
R_THINK = ("思考知覺", ["思考跳躍", "對空比劃與手勢行為", "喃喃自語", "抱怨聽/視幻覺干擾", "乏病識感"])
R_RISK = ("風險行為", ["具言語/身體攻擊傾向", "具自殺/自傷意念或衝動", "企圖衝出病房"])
R_ACT = ("活動", ["多於大廳活動", "多於房內活動", "可於大廳觀賞電視", "多獨自在大廳來回走動",
                 "整天躺床/活動量少", "可主動參與職能治療", "被動配合常規"])
R_SOCIAL = ("人際互動", ["人際互動可", "人際互動合宜", "人際互動少", "人際互動疏離", "可與部分病友互動"])
R_GAIT = ("步態", ["活動步態平穩", "活動步態緩慢尚穩", "下床活動時步態欠穩", "輪椅代步"])

R_FALL_EDU = ("預防跌倒", ["給予預防跌倒衛教：採漸進式下床、晚餐後減少飲水、睡前如廁、若有需要可請求他人協助",
                       "提醒注意活動安全"])
R_NO_FALL = ("跌倒", ["無跌倒情形"])

I_RISK_TYPES = ["暴力", "自殺", "自傷", "逃跑", "性不適切"]
RISK_LEVELS = ["不註明級數", "第一級", "第二級", "第三級", "第四級"]
RESTRAINT_TYPES = ["腹部固定帶", "軀幹約束衣", "雙手泡棉式", "四肢布條式", "雙下肢布條式", "手腕式約束帶"]

def risk_sentence(prefix):
    """防範危急：選種類＋級數，組成「依醫囑持續防範暴力(第三級)及逃跑危急」"""
    types = st.multiselect("🚨 依醫囑防範危急（可複選）", I_RISK_TYPES, key=f"{prefix}_risk")
    parts = []
    for t in types:
        lv = st.selectbox(f"{t} 級數", RISK_LEVELS, key=f"{prefix}_risk_{t}")
        parts.append(t if lv == "不註明級數" else f"{t}({lv})")
    return [f"依醫囑持續防範{'及'.join(parts)}危急"] if parts else []


def fall_score(prefix):
    score = st.number_input("跌倒高危險評估（分，0 = 不寫）", min_value=0, max_value=20, step=1, key=f"{prefix}_fall")
    return [f"跌倒高危險評估{score}分"] if score else []


def admit_way(prefix):
    """入院方式：組成「於1500由門診步行，家屬陪伴入病房」"""
    t = st.text_input("入病房時間", placeholder="例如：1500", key=f"{prefix}_time")
    src = st.selectbox("來源", ["門診", "急診", "他院轉入"], key=f"{prefix}_src")
    how = st.selectbox("方式", ["步行", "推床", "輪椅"], key=f"{prefix}_how")
    who = st.selectbox("陪同", ["家屬陪伴", "獨自", "工作人員陪同"], key=f"{prefix}_who")
    return [f"{'於' + t if t else ''}由{src}{how}，{who}入病房"]


def leave_way(prefix):
    """離院：組成「於1030由家屬陪同步行離院」"""
    t = st.text_input("離院時間", placeholder="例如：1030", key=f"{prefix}_ltime")
    who = st.selectbox("陪同者", ["家屬", "案妻", "案母", "機構人員"], key=f"{prefix}_lwho")
    how = st.selectbox("離院方式", ["步行", "輪椅"], key=f"{prefix}_lhow")
    return [f"{'於' + t if t else ''}由{who}陪同{how}離院"] if t else []


def restraint_action(prefix):
    """約束開始／解除：組成「於1645依醫囑予腹部固定帶、雙手泡棉式約束使用」"""
    act = st.selectbox("約束動作", ["（不寫）", "開始約束", "部分解除", "全部解除"], key=f"{prefix}_act")
    if act == "（不寫）":
        return []
    t = st.text_input("時間", placeholder="例如：1645", key=f"{prefix}_rtime")
    types = st.multiselect("約束種類（可複選）", RESTRAINT_TYPES, key=f"{prefix}_rtype")
    when = f"於{t}" if t else ""
    what = "、".join(types)
    if act == "開始約束":
        return [f"{when}依醫囑予{what}約束使用"]
    if act == "部分解除":
        keep = st.multiselect("持續使用的約束", RESTRAINT_TYPES, key=f"{prefix}_rkeep")
        s = f"{when}依醫囑解除{what}約束"
        return [s + (f"，{'、'.join(keep)}約束持續使用" if keep else "")]
    return [f"{when}依醫囑解除{what}約束"]


# ==================================================================
# 各紀錄類型的版面設定：每區 = 幾欄，每欄 = 幾組（標題, 選項清單 或 小工具函式）

# ==================================================================
# 各紀錄類型的內容：每區（O/I/E）由上到下一列一個項目，順序 = 書寫順序
# 列可以是（名稱, 選項清單），或（名稱, 小工具函式）例如跌倒分數、防範危急
# ==================================================================
O_BASIC = [R_LOOK, R_SPIRIT, R_FACE, R_MOOD, R_TALK, R_THINK]

FORMS = {
    "常規": {
        "O": O_BASIC + [R_RISK, R_ACT, R_SOCIAL, R_GAIT, ("跌倒評估", fall_score)],
        "I": [("接觸態度", ["採尊重、友善及信任態度主動接觸", "採誠懇、尊重、信任之態度與其接觸"]),
              ("關心探視", ["自我介紹", "主動關心及定時探視"]),
              ("治療性關係", ["建立治療性人際關係", "維持治療性人際關係"]),
              ("會談", ["集中會談主題", "引導會談"]),
              ("評估", ["評估精神症狀對日常生活之影響", "評估情緒變化及行為表現"]),
              ("情緒處理", ["引導表達內心想法及感受", "予以傾聽及同理", "提供情緒宣洩管道", "適時安撫情緒"]),
              ("症狀處理", ["與其討論轉移聽幻覺之方法並對目前方式給予肯定", "引導現實導向，不爭辯妄想內容",
                        "對正向行為給予肯定", "鼓勵參與病房活動", "視情況提供協助"]),
              ("給藥", ["確實給藥、監督服藥", "服藥時予藥物衛教", "觀察藥物效果"]),
              ("觀察與安全", ["觀察行為表現", "加強查房與環境安全檢查", "依醫囑執行保護性約束護理"]),
              ("防範危急", risk_sentence),
              R_FALL_EDU],
        "E": [("表達", ["可說出其感受", "可說出內心想法及感受", "可說出聽幻覺/精神症狀干擾情形", "可說出目前症狀改善"]),
              ("症狀", ["聽幻覺尚可轉移", "班內未額外尋求協助"]),
              ("衛教", ["對衛教內容可點頭表了解及接受", "被動接受衛教內容"]),
              ("服藥", ["可配合服藥及張口檢查", "可主動排隊服藥、張口檢查"]),
              ("行為", ["引導下可參與活動", "情緒可自控", "班內行為可配合", "暫無不適切行為"]),
              R_NO_FALL],
    },
    "入院": {
        "O": [("入病房方式", admit_way)] + O_BASIC + [R_RISK, R_GAIT, ("跌倒評估", fall_score)],
        "I": [("接觸態度", ["採誠懇、尊重、信任之態度與其接觸"]),
              ("自我介紹", ["予以自我介紹", "介紹醫療團隊"]),
              ("治療性關係", ["建立治療性人際關係"]),
              ("環境介紹", ["病房環境介紹及病室、訪客規定", "衛教其了解環境安全維護之重要"]),
              ("會談", ["引導表達住院原因及感受", "評估外院治療及居家服藥情形", "予傾聽、同理感受"]),
              ("安檢", ["協助共同檢視隨身物品", "請家屬帶回或護理站保管危險物品"]),
              ("同意書", ["協助填寫住院同意書及精神科病人保護性隔離約束說明暨同意書"]),
              ("其他", ["通知專科護理師診視", "鼓勵住院期間配合治療", "觀察行為表現"]),
              ("防範危急", risk_sentence),
              R_FALL_EDU],
        "E": [("安檢", ["可配合安檢"]),
              ("同意書", ["可填妥住院同意書及精神科病人保護性隔離約束說明暨同意書"]),
              ("表達", ["能說出住院原因", "可接受衛教說明"]),
              ("行為", ["可配合入院護理", "暫無不適切行為表現"]),
              R_NO_FALL],
    },
    # 出院：單位檔案中沒有出院當日的紀錄，以下為一般常見寫法，請依單位習慣修改
    "出院": {
        "O": O_BASIC + [R_ACT, R_SOCIAL, R_GAIT],
        "I": [("接觸態度", ["採尊重、友善及信任態度主動接觸"]),
              ("治療性關係", ["維持治療性人際關係"]),
              ("出院規劃", ["評估出院規劃", "引導表達出院後安排"]),
              ("出院衛教", ["予出院衛教：規則服藥、按時回診", "說明出院帶藥之用法及注意事項",
                        "衛教症狀復發徵兆及處理方式", "告知回診時間"]),
              ("出院手續", ["協助辦理出院手續", "歸還保管之隨身物品"]),
              R_FALL_EDU],
        "E": [("表達", ["可說出出院後生活安排", "可說出回診時間及服藥方式", "可說出症狀復發時之處理方式"]),
              ("衛教", ["對衛教內容可點頭表了解及接受"]),
              ("物品", ["已領回隨身物品"]),
              R_NO_FALL,
              ("離院", leave_way)],
    },
    "約束": {
        "O": O_BASIC + [("行為表現", ["情緒起伏明顯", "具言語/身體攻擊傾向", "企圖衝出病房", "不聽勸阻"]),
                        ("約束中", ["約束下情緒漸緩和", "反覆要求鬆開約束", "約束部位皮膚完整", "肢體末梢溫暖"])],
        "I": [("約束前準備", ["備齊人力", "告知值班醫師"]),
              ("約束執行", restraint_action),
              ("約束評估", ["評估末梢血循及約束必要性", "預防約束損傷"]),
              ("探視照護", ["每15分鐘探視1次", "每兩小時鬆開約束部位", "視情況滿足生理需求"]),
              ("情緒處理", ["適時安撫情緒", "提醒維持合宜情緒及行為表現"]),
              ("觀察", ["觀察行為表現"]),
              ("防範危急", risk_sentence)],
        "E": [("配合度", ["可配合約束使用", "情緒行為暫可配合"]),
              ("約束損傷", ["無約束損傷產生", "約束部位周圍皮膚無紅腫", "肢體末梢溫暖"]),
              ("行為", ["無暴力及逃跑行為", "未再出現不適切行為"])],
    },
}


def render_section(rows, prefix):
    """由上到下畫出每一列，回傳勾選結果（依書寫順序）"""
    picked = []
    for label, items in rows:
        if callable(items):
            c1, c2 = st.columns([1.3, 8])
            c1.markdown(f"**{label}**")
            with c2:
                picked += items(f"{prefix}_{label}")
        else:
            picked += pick_row(label, items, key=f"{prefix}_{label}")
    return picked


def quick_soie(s_text, o, o_extra, i, i_extra, e, e_extra):
    """不用 AI：把各區勾選依順序用「，」接起來，手寫補充接在該區最後"""
    def line(tag, items, extra):
        parts = list(items) + ([extra.strip("，。 ")] if extra else [])
        return f"{tag}：{'，'.join(parts)}。" if parts else ""
    lines = [f"S：{s_text.strip()}" if s_text else "",
             line("O", o, o_extra), line("I", i, i_extra), line("E", e, e_extra)]
    return "\n".join(x for x in lines if x)


def soie_form(kind):
    form = FORMS[kind]
    p = kind  # 每種紀錄的勾選分開記，互不干擾
    # 生成方式：AI 融合 或 快速組句（不用 AI、不限次數）；今日額度用完時預設切到快速組句
    u = get_usage()
    no_quota = u["exhausted"] or u["count"] >= DAILY_LIMIT
    mode = st.radio("生成方式：", ["🤖 AI 生成（每日限額）", "⚡ 快速組句（不用 AI，不限次數）"],
                    index=1 if no_quota else 0, horizontal=True, key=f"{p}_mode")
    quick = mode.startswith("⚡")
    if quick:
        st.caption("快速組句：依書寫順序把勾選的詞用「，」接起來，手寫補充接在該區最後面，畫面會即時更新。")
    col1, col2 = st.columns([6, 4])

    with col1:
        st.markdown("### 📝 【S】個案主訴 (Subjective)")
        s_text = st.text_input("主訴內容（手寫輸入）：", key=f"{p}_s",
                               placeholder="例如：個案表示「今天心情比較好」或「聽幻覺一直叫我走動」...")
        st.write("---")

        st.markdown("### 🔍 【O】客觀精神症狀與評估 (Objective)")
        o_summary = render_section(form["O"], f"{p}_o")
        o_extra = st.text_input("✍️ O 區症狀/情境手寫補充：", key=f"{p}_ox", placeholder="例如：可見手摀住耳朵、在大廳繞圈情形...")
        st.write("---")

        st.markdown("### 🛠️ 【I】護理措施 (Intervention)")
        i_summary = render_section(form["I"], f"{p}_i")
        i_extra = st.text_input("✍️ I 區措施/情境手寫補充：", key=f"{p}_ix", placeholder="例如：引導會談時了解目前聽幻覺干擾細節...")
        st.write("---")

        st.markdown("### 📊 【E】護理評值 (Evaluation)")
        e_summary = render_section(form["E"], f"{p}_e")
        e_extra = st.text_input("✍️ E 區反應/情境手寫補充：", key=f"{p}_ex", placeholder="例如：聽幻覺仍存在但尚可配合轉移...")
        st.write("---")

        if quick:
            auto_mode, submit = False, False
        else:
            auto_mode = st.toggle("✨ I、E 沒勾也沒寫時，由 AI 依 S、O 區自動建議", value=False, key=f"{p}_auto")
            submit = st.button("🚀 啟動 Gemini AI 生成專屬護理紀錄", type="primary", key=f"{p}_go")

    if quick:
        with col2:
            st.markdown("### 📋 複製區（直接貼上 HIS）")
            st.text_area("直接全選複製：", height=500, key=f"{p}_quick_out",
                         value=quick_soie(s_text, o_summary, o_extra, i_summary, i_extra, e_summary, e_extra))
            st.caption("💡 快速組句不經過 AI，不消耗額度。")
        return

    with col2:
        st.markdown("### 📋 AI 靈魂優化複製區（直接貼上 HIS）")
        if submit:
            with st.spinner("🧠 Gemini 大腦正在無縫揉合您的手寫細節中..."):
                auto_i = auto_mode and not i_summary and not i_extra
                auto_e = auto_mode and not e_summary and not e_extra
                i_block = ("【I 區】: 使用者未填寫，請 AI 依 S、O 區建議" if auto_i else
                           f"【I 區常規勾選】: {'；'.join(i_summary) if i_summary else '無'}\n"
                           f"【I 區核心手寫補充（請自然嵌入上述勾選脈絡中）】: {i_extra if i_extra else '無'}")
                e_block = ("【E 區】: 使用者未填寫，請 AI 依 S、O 區建議" if auto_e else
                           f"【E 區常規勾選】: {'；'.join(e_summary) if e_summary else '無'}\n"
                           f"【E 區核心手寫補充（請自然嵌入上述勾選脈絡中）】: {e_extra if e_extra else '無'}")

                raw_input_payload = (
                    f"【紀錄類型】: {kind}紀錄\n"
                    f"【S 區主訴】: {s_text if s_text else '個案未主動表達特殊主訴'}\n\n"
                    f"【O 區常規勾選】: {'；'.join(o_summary) if o_summary else '無'}\n"
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
WAKE_REASONS = ["如廁", "翻身"]
MORNING = ["晨起無不適切情緒及行為表現", "晨起步態平穩", "晨起下床坐輪椅代步", "晨間可自行完成盥洗",
           "晨起可配合抽血檢驗，檢體已送出"]


def night_shift():
    col1, col2 = st.columns([6, 4])

    with col1:
        st.markdown("### 🌙 夜眠情形")
        c1, c2 = st.columns(2)
        with c1:
            start = st.selectbox("接班時", ["已入睡", "尚未入睡", "於大廳活動", "靜躺未入睡"])
            breath = st.checkbox("呼吸平順", value=True)
            bell = st.checkbox("叫人鈴備用")
            times = st.number_input("夜眠中斷次數", min_value=0, max_value=20, step=1)
            reasons = st.multiselect("中斷原因（可複選）", WAKE_REASONS) if times else []
            after = (st.selectbox("中斷後", ["（不寫）", "可再入睡", "可再短暫入睡", "未再入睡",
                                            "主動至護理站要求助眠藥物，服藥後可入睡"])
                     if times else None)
        with c2:
            hours = st.number_input("夜眠共計（小時）", min_value=0.0, max_value=12.0, step=0.5, value=6.0)
            early = st.text_input("早醒時間（沒有就留空）", placeholder="例如：0430")
            sugar = st.text_input("晨起飯前血糖 mg/dL（沒有就留空）", placeholder="例如：126")

        st.markdown("### 🌅 晨間情形")
        morning = checkbox_group(MORNING, "n")
        extra = st.text_input("✍️ 中斷時的狀況或其他補充：",
                              placeholder="例如：0300 至護理站表示睡不著，予傾聽後返室躺床")

    # --- 組句子（順序依單位習慣：接班→呼吸→叫人鈴→中斷→補充→早醒→共計→晨起→血糖）---
    parts = [f"接班時{start}"]
    if breath:
        parts.append("呼吸平順")
    if bell:
        parts.append("叫人鈴備用")
    if times == 0:
        parts.append("夜眠無中斷")
    else:
        parts.append(f"夜眠中斷{times}次{'、'.join(reasons)}")
        if after and after != "（不寫）":
            parts.append(after)
    if extra:
        parts.append(extra.strip("，。 "))
    if early:
        parts.append(f"{early}早醒")
    parts.append(f"共計{hours:g}小時")
    parts += morning
    if sugar:
        parts.append(f"晨間飯前血糖值：{sugar}mg╱dL")
    note = "，".join(parts) + "。"

    with col2:
        st.markdown("### 📋 複製區（直接貼上 HIS）")
        st.text_area("直接全選複製：", value=note, height=200)
        st.caption("💡 大夜紀錄由程式直接組成，不經過 AI，不消耗額度，數字也不會寫錯。")



# ==================================================================
# 小夜：一段敘述（不經過 AI，程式依單位書寫順序直接組句子）
# ==================================================================
EVENING_ROWS = [
    ("精神", ["晚間精神可", "精神可", "精神顯倦怠"]),
    R_LOOK, R_FACE, R_MOOD, R_TALK, R_THINK,
    ("活動", ["多於大廳活動", "多於大廳看電視", "多於房內活動", "多於病室內躺床活動"]),
    ("人際互動", ["人際互動合宜", "與病友互動合宜", "可與部分病友互動", "人際互動少", "人際互動疏離", "未見與他人互動"]),
    ("步態", ["活動步態平穩", "行走步態平穩", "活動步態緩慢尚穩", "下床輪椅代步"]),
    ("服藥治療", ["可配合服藥及張口檢查", "可主動排隊服藥及張口檢查", "班內治療可配合"]),
    ("防範危急", risk_sentence),
    ("行為", ["暫無不適切行為"]),
    ("熄燈後", ["熄燈後叫人鈴備用", "熄燈後可自行躺床入睡", "熄燈後可自行躺床休息", "熄燈後尚未入睡"]),
    ("跌倒", ["無跌倒發生"]),
]


def evening_shift():
    col1, col2 = st.columns([6, 4])
    with col1:
        st.markdown("### 🌆 小夜紀錄")
        start = st.selectbox("接班時", ["（不寫）", "於大廳活動", "於房內躺床", "於房內活動"], key="小夜_start")
        parts = [] if start == "（不寫）" else [f"接班時{start}"]
        parts += render_section(EVENING_ROWS, "小夜")
        extra = st.text_input("✍️ 其他補充（例如班內特殊狀況）：", key="小夜_extra",
                              placeholder="例如：2235 按鈴下床如廁，步態緩慢尚穩，如廁後可再入睡")
        if extra:
            parts.append(extra.strip("，。 "))
    # 熄燈後勾了好幾個時，只保留第一個「熄燈後」，例如「熄燈後叫人鈴備用，可自行躺床入睡」
    seen = False
    for i, x in enumerate(parts):
        if x.startswith("熄燈後"):
            if seen:
                parts[i] = x[len("熄燈後"):]
            seen = True
    note = "，".join(parts) + "。" if parts else ""

    with col2:
        st.markdown("### 📋 複製區（直接貼上 HIS）")
        st.text_area("直接全選複製：", value=note, height=250, key="小夜_out")
        st.caption("💡 小夜紀錄由程式直接組成，不經過 AI，不消耗額度。")

# ==================================================================
# 紀錄類型與班別選擇
# ==================================================================
kind = st.radio("請選擇紀錄類型：", ["📋 常規紀錄", "🏥 入院紀錄", "🏠 出院紀錄", "🔒 約束紀錄"], horizontal=True)
if kind.startswith("📋"):
    shift = st.radio("請選擇班別：", ["🌞 白班（SOIE）", "🌆 小夜（一段敘述）", "🌙 大夜（夜眠紀錄）"], horizontal=True)
    st.write("---")
    if shift.startswith("🌞"):
        soie_form("常規")
    elif shift.startswith("🌆"):
        evening_shift()
    else:
        night_shift()
else:
    st.write("---")
    if kind.startswith("🏠"):
        st.info("ℹ️ 出院選項為一般常見寫法（單位檔案中沒有出院當日紀錄），歡迎提供範本再調整。")
    soie_form({"🏥": "入院", "🏠": "出院", "🔒": "約束"}[kind[0]])

# 整頁跑完後，更新最上方的今日剩餘次數
show_quota()
